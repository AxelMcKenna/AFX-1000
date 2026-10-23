#!/usr/bin/env python3
"""Build both real ARM profiles and run nine host suites. No flashing."""

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "hardware/firmware"
VALIDATION = ROOT / "hardware/validation"
TESTS = [
    "engine",
    "hardware_controls",
    "audio_arena",
    "hardware_wire",
    "connection_mode",
    "relay_feedback",
    "external_converter",
    "input_qualification",
    "control_expanders",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    result = subprocess.run(
        [str(a) for a in args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if result.returncode:
        raise RuntimeError(" ".join(map(str, args)) + "\n" + "\n".join(result.stdout.splitlines()[-35:]))
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--toolchain", type=pathlib.Path, required=True, help="Directory containing arm-none-eabi-g++"
    )
    parser.add_argument("--host-build", type=pathlib.Path, default=ROOT / "build-hardware")
    parser.add_argument("--sdk", type=pathlib.Path, default=ROOT / "build-hardware/libDaisy")
    args = parser.parse_args()
    sdk = args.sdk.resolve()
    host = args.host_build.resolve()
    toolchain = args.toolchain.resolve()
    dependency = json.loads((FIRMWARE / "dependencies.json").read_text())
    commit = run(["git", "-C", sdk, "rev-parse", "HEAD"]).strip()
    assert commit == dependency["libDaisy"]["commit"], "SDK commit differs from the pinned source"
    assert not run(["git", "-C", sdk, "status", "--porcelain", "--untracked-files=no"]).strip(), (
        "SDK tracked source is modified"
    )
    proposal = json.loads((ROOT / "hardware/electronics/converter/interface-plan.json").read_text())
    profile = json.loads((FIRMWARE / "external-profile.json").read_text())
    assert profile["firmware_adapter_implemented"] and not profile["hardware_verified"]
    assert profile["codec_address_seven_bit"] == proposal["codec"]["address_seven_bit"] == 24
    for key, pin, net in [
        ("permit_pin", 29, "MCU_PERMIT"),
        ("latch_feedback_pin", 30, "ARMED"),
        ("codec_run_shared_reset_pin", 0, "CODEC_RUN"),
    ]:
        assert profile[key] == pin and proposal["module_gpio"]["D" + str(pin)]["net"] == net
    assert profile["sample_rate_hz"] == proposal["sai"]["sample_rate_hz"] == 48000
    assert profile["bits_per_slot"] == proposal["sai"]["word_bits"] == 32
    sequencer_path = ROOT / "hardware/electronics/sequenced_bypass/integration.json"
    sequencer = json.loads(sequencer_path.read_text())
    # F04 retains E11/F02 and E13/F03 qualification; only front-expander wiring
    # and configuration change. Rear/status A0..A3 and all MCU GPIO stay fixed.
    assert sequencer["firmware_revision"] == "F02" and profile["revision"] == "F04"
    monitor_path = ROOT / "hardware/electronics/rail_monitor/integration.json"
    monitor = json.loads(monitor_path.read_text())
    assert monitor["firmware_revision"] == "F03"
    assert profile["required_mcp23017_both_profiles"] == 3
    assert not profile["mcp23017_output_only_pins_used_as_inputs"]
    assert profile["expander_configuration_readback"]
    control_path = ROOT / profile["control_input_hub"]
    control = json.loads(control_path.read_text())
    assert control["firmware_revision"] == "F04" and control["front_inputs"] == 32
    assert (
        control["receiving_reset_pulldown_ohm"]
        == profile["required_receiving_end_reset_pulldown_ohm"]
        == 100000
    )
    assert (
        control["receiving_analog_ok_pulldown_ohm"]
        == profile["required_receiving_end_analog_ok_pulldown_ohm"]
    )
    assert (
        control["receiving_input_ready_pulldown_ohm"]
        == profile["required_receiving_end_input_ready_pulldown_ohm"]
    )
    assert control["rear_header_external_profile_only"] and not control["full_control_board_complete"]
    run([sys.executable, FIRMWARE / "control_map.py", "--check"])
    mapping = json.loads((FIRMWARE / "control-inputs.json").read_text())
    assert len(mapping["front_inputs"]) == 32 and len(mapping["external_rear_inputs"]) == 4
    assert not any(p["gpio"].endswith("7") for p in mapping["front_inputs"] + mapping["external_rear_inputs"])
    assert (
        len(
            {(p["address"], p["soic_pin"]) for p in mapping["front_inputs"] + mapping["external_rear_inputs"]}
        )
        == 36
    )
    assert profile["power_startup_id_poll_ms"] == monitor["software_id_poll_ms"] == 5
    assert profile["power_startup_id_stable_ms"] == monitor["software_id_stable_ms"] == 20
    assert profile["power_startup_timeout_ms"] == monitor["software_startup_timeout_ms"] == 5000
    assert profile["third_mcp_inputs"]["GPA3"] == "INPUT_READY active high"
    assert (
        profile["required_receiving_end_input_ready_pulldown_ohm"]
        == sequencer["status_receiving_pulldown_ohm"]
        == 270000
    )
    assert profile["continuous_software_input_quiet_ms"] == sequencer["software_input_quiet_ms"] == 1250
    assert profile["input_qualification_timeout_ms"] == sequencer["software_input_timeout_ms"] == 10000
    sdk_hashes = {}
    for path, expected in proposal["sdk_source_sha256"].items():
        relative = path.split("libDaisy/", 1)[1]
        actual = sha(sdk / relative)
        assert actual == expected, path
        sdk_hashes[relative] = actual
    for path in [
        "src/daisy_seed.cpp",
        "src/hid/audio.cpp",
        "src/sys/system.cpp",
        "src/sys/dma.c",
        "core/STM32H750IB_sram.lds",
        "Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_sai.c",
    ]:
        sdk_hashes[path] = sha(sdk / path)
    seed = (sdk / "src/daisy_seed.h").read_text()
    for key, entry in proposal["module_gpio"].items():
        match = re.search(r"constexpr Pin " + key + r"\s*= Pin\(PORT([A-Z]), (\d+)\);", seed)
        assert match and entry["stm32_pin"] == "P" + match.group(1) + match.group(2), key
    run(["cmake", "-S", ROOT, "-B", host, "-DCMAKE_BUILD_TYPE=Release", "-DRMX_BUILD_TESTS=ON"])
    targets = ["rmx_tests"] + ["rmx_" + name + "_tests" for name in TESTS[1:]]
    run(["cmake", "--build", host, "--target", *targets, "--parallel", "4"])
    junit = VALIDATION / "external-host-tests.xml"
    run(
        [
            "ctest",
            "--test-dir",
            host,
            "--output-on-failure",
            "-R",
            "^(" + "|".join(TESTS) + ")$",
            "--output-junit",
            junit,
        ]
    )
    cases = ET.parse(junit).getroot().findall(".//testcase")
    assert sorted(case.attrib["name"] for case in cases) == sorted(TESTS)
    assert not any(case.find("failure") is not None or case.find("skipped") is not None for case in cases)
    direct = run([host / "rmx_external_converter_tests"]).strip()
    input_summary = run([host / "rmx_input_qualification_tests"]).strip()
    control_summary = run([host / "rmx_control_expanders_tests"]).strip()
    profiles = {}
    for profile, target, build in [
        ("external", "rmx_standalone_external", "build-external"),
        ("onboard", "rmx_standalone", "build"),
    ]:
        output = run(
            [
                "make",
                "-C",
                FIRMWARE,
                "PROFILE=" + profile,
                "-j4",
                "GCC_PATH=" + str(toolchain),
                "LIBDAISY_DIR=" + str(sdk),
            ]
        )
        assert not re.search(r"(?:^|\n).*warning:.*", output) or all(
            any(expected in line for expected in ["not implemented", "RWX permissions"])
            for line in output.splitlines()
            if "warning:" in line
        ), "Unexpected build warning"
        directory = FIRMWARE / build
        binary = directory / (target + ".bin")
        elf = directory / (target + ".elf")
        sections = {}
        for line in run([toolchain / "arm-none-eabi-size", "-A", elf]).splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[0].startswith(".") and fields[1].isdigit():
                sections[fields[0]] = int(fields[1])
        assert sections[".sram1_bss"] <= 32768 and sections[".sdram_bss"] == 48 * 1024 * 1024
        assert sections[".bss"] + sections[".data"] < 128 * 1024
        symbols = run([toolchain / "arm-none-eabi-nm", "-C", elf])
        assert ("rmx::embedded::ExternalAudio::dispatch(" in symbols) == (profile == "external")
        if profile == "external":
            # Confirm uncached DMA region and 32-byte alignment in actual ELF.
            dma_symbols = {}
            for line in symbols.splitlines():
                if "anonymous namespace)::receive" in line or "anonymous namespace)::transmit" in line:
                    address = int(line.split()[0], 16)
                    assert 0x30000000 <= address < 0x30008000 and address % 32 == 0
                    dma_symbols[line.split()[-1]] = hex(address)
            assert len(dma_symbols) == 2
        else:
            dma_symbols = {}
        profiles[profile] = dict(
            binary=str(binary.relative_to(ROOT)),
            binary_bytes=binary.stat().st_size,
            binary_sha256=sha(binary),
            elf_sha256=sha(elf),
            sections_bytes=sections,
            dma_symbols=dma_symbols,
            cross_compiled=True,
            flashed=False,
            hardware_verified=False,
        )
    assert profiles["external"]["binary_sha256"] != profiles["onboard"]["binary_sha256"]
    invalid = subprocess.run(["make", "-C", str(FIRMWARE), "PROFILE=invalid"], capture_output=True, text=True)
    assert invalid.returncode and "PROFILE must be onboard or external" in invalid.stderr
    sources = [
        p for p in FIRMWARE.iterdir() if p.is_file() and p.suffix in (".h", ".cpp", ".py", ".json", ".md")
    ]
    sources += [
        FIRMWARE / "Makefile",
        FIRMWARE / "control-inputs.csv",
        ROOT / "CMakeLists.txt",
        *sorted((ROOT / "src/core").glob("*.cpp")),
        ROOT / "hardware/electronics/converter/interface-plan.json",
        ROOT / "hardware/electronics/converter/dependencies.json",
        sequencer_path,
        monitor_path,
        control_path,
        ROOT / "hardware/cad/generate.py",
    ]
    sources += sorted((ROOT / "tests").glob("*tests.cpp"))
    sources += sorted((ROOT / "include/rmx").rglob("*.h"))
    sources += sorted(p for p in (ROOT / "src/core").rglob("*") if p.is_file() and p.suffix in (".h", ".cpp"))
    report = dict(
        revision="F04",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope="Both ARM profiles and nine host suites; 32 front inputs on three MCP23017s with no output-only pins used as inputs, verified register setup and bus-fault handling; E18 receiving-load interface checked, E11/E13 qualification retained; no physical test",
        libdaisy_commit=commit,
        sdk_source_sha256=sdk_hashes,
        toolchain=run([toolchain / "arm-none-eabi-g++", "--version"]).splitlines()[0],
        profiles=profiles,
        host_tests=dict(passed=len(cases), failed=0, names=TESTS, junit_sha256=sha(junit)),
        external_test_summary=direct,
        input_qualification_summary=input_summary,
        control_expanders_summary=control_summary,
        control_input_map="hardware/firmware/control-inputs.json",
        invalid_profile_rejected=True,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(sources))},
        limitations=[
            "Codec and MCU SAI32 mode not tested on hardware",
            "Master clock/BCLK/WS/data edge phase unmeasured",
            "DMA phase/16-word copy reserve and interrupt timing require physical measurement",
            "E12-E17 analog/power circuits are conditional schematics; integrated PCB and complete enclosure placement unfinished",
            "E13 analog startup delay up to420ms; software ID probing is bounded to5s; actual supply/startup timing unmeasured",
            "E18 routes digital inputs with ANALOG_OK47k/INPUT_READY270k/reset100k receiving pull-downs; complete control circuitry and physical qualification unfinished",
            "Both profiles now require three MCP23017s and revised front wiring; older two-expander wiring is incompatible",
            "Physical control scan latency, I2C rise time/capacitance and EMI behavior unmeasured",
            "E11 hardware startup, gain reset pulse, coil/contact settling and brownout behavior unmeasured",
            "Raw converter scale, gain/calibration, noise/THD, latency, bypass transients and soak unverified",
            "microSD sample/preset loader and user settings application incomplete",
            "Existing SDK/newlib unsupported POSIX syscall and RWX linker warnings remain",
        ],
    )
    path = VALIDATION / "external-firmware.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(direct)
    print(input_summary)
    print(control_summary)
    print("Both ARM profiles build; nine host suites pass; report:", path.relative_to(ROOT))
    for name, profile in profiles.items():
        print(name, profile["binary_bytes"], "bytes; DMA SRAM", profile["sections_bytes"][".sram1_bss"])


if __name__ == "__main__":
    main()
