#!/usr/bin/env python3
"""Rebuild and audit F06 host tests and SRAM ARM images; never flash hardware."""

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "hardware/validation/full-engine"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, log=None):
    result = subprocess.run([str(a) for a in args], cwd=REPO, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if log:
        (OUT / log).write_text(output)
    if result.returncode:
        raise RuntimeError(" ".join(map(str, args)) + "\n" + "\n".join(output.splitlines()[-30:]))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, default=REPO / "build-hardware/libDaisy")
    parser.add_argument("--host-build", type=Path, default=REPO / "build/full-engine-host")
    parser.add_argument("--python", default="python3")
    args = parser.parse_args()
    sdk, tools, host = args.sdk.resolve(), args.toolchain.resolve(), args.host_build.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    record = OUT / "verification.json"
    record.unlink(missing_ok=True)
    pinned = json.loads((HERE.parent / "dependencies.json").read_text())["libDaisy"]["commit"]
    assert run(["git", "-C", sdk, "rev-parse", "HEAD"]).strip() == pinned
    assert not run(["git", "-C", sdk, "status", "--porcelain", "--untracked-files=no"]).strip()
    compiler_version = run([tools / "arm-none-eabi-g++", "--version"]).strip()
    sdk_command = ["make", "-C", sdk, "GCC_PATH=" + str(tools)]
    run(sdk_command + ["clean"], "sdk-clean.txt")
    run(sdk_command + ["-j4"], "sdk-build.txt")
    sdk_archive = sdk / "build/libdaisy.a"
    assert sdk_archive.is_file()
    run([args.python, HERE / "generate_kernels.py", "--check"], "kernel-origin.txt")
    run(["cmake", "-S", HERE, "-B", host, "-DCMAKE_BUILD_TYPE=Release"], "host-configure.txt")
    run(["cmake", "--build", host, "--parallel", "4"], "host-build.txt")
    run(
        ["ctest", "--test-dir", host, "--output-on-failure", "--output-junit", OUT / "host-tests.xml"],
        "host-tests.txt",
    )
    cases = ET.parse(OUT / "host-tests.xml").getroot().findall(".//testcase")
    assert {
        "full_integration",
        "full_kernels",
        "full_storage",
        "full_memory",
        "full_control_recovery",
        "full_allocator_storage",
    } <= {c.attrib["name"] for c in cases}
    assert all(c.find("failure") is None and c.find("skipped") is None for c in cases)
    summaries = {
        name: run([host / name]).strip()
        for name in [
            "full_integration",
            "full_kernels",
            "full_memory",
            "full_storage",
            "full_control_recovery",
            "full_allocator_storage",
        ]
    }
    settings = re.search(
        r"F06: (\d+) maintained parameters, (\d+) advanced User settings", summaries["full_integration"]
    )
    assert settings, "Missing maintained-engine parameter coverage summary"
    profiles = {}
    for profile in ["onboard", "external"]:
        directory = HERE / ("build-verified-" + profile)
        target = "rmx_full_engine" + ("_external" if profile == "external" else "")
        command = [
            "make",
            "-C",
            HERE,
            "PROFILE=" + profile,
            "BUILD_DIR=" + directory.name,
            "GCC_PATH=" + str(tools),
            "LIBDAISY_DIR=" + str(sdk),
        ]
        # Compiler flags are not Make dependencies. Always rebuild this dedicated
        # validation directory so a stale opt-in/off object cannot certify F06.
        run(command + ["clean"], "arm-" + profile + "-clean.txt")
        run(command + ["-j4"], "arm-" + profile + "-build.txt")
        elf, binary = directory / (target + ".elf"), directory / (target + ".bin")
        sections = {}
        for line in run([tools / "arm-none-eabi-size", "-A", elf]).splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[0].startswith(".") and fields[1].isdigit():
                sections[fields[0]] = dict(bytes=int(fields[1]), address=hex(int(fields[2])))
        symbols = run([tools / "arm-none-eabi-nm", "-S", "-C", elf])

        def symbol(fragment):
            rows = [line.split() for line in symbols.splitlines() if fragment in line]
            assert len(rows) == 1, (fragment, rows)
            return int(rows[0][0], 16), int(rows[0][1], 16)

        dma, dma_bytes = symbol("bootSdDmaStorage")
        kernels, kernel_bytes = symbol("sample_reader::(anonymous namespace)::restored")
        assert dma % 32 == 0 and 0x24000000 <= dma < dma + dma_bytes <= 0x24078000
        assert dma_bytes == sections[".sdmmc_bss"]["bytes"] == 5888
        assert kernel_bytes == 33 * 8452
        assert kernels % 32 == 0 and 0xC0000000 <= kernels < kernels + kernel_bytes <= 0xC4000000
        assert sections[".sdram_bss"]["bytes"] == 60 * 1024 * 1024 + kernel_bytes
        assert sections[".sram1_bss"]["bytes"] <= 32768
        assert sections[".bss"]["bytes"] + sections[".data"]["bytes"] < 120 * 1024
        # All instruction sections execute from AXI SRAM, preserving safe
        # calibration-sector writes while QSPI memory mapping is disabled.
        elf_sections = run([tools / "arm-none-eabi-readelf", "-W", "-S", elf])
        executable_sections = {}
        for line in elf_sections.splitlines():
            match = re.match(
                r"\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+(\S+)",
                line,
            )
            if match and "X" in match.group(4):
                name, address, size = match.group(1), int(match.group(2), 16), int(match.group(3), 16)
                if size:
                    assert "A" in match.group(4), (name, "Unallocated executable section")
                    assert 0x24000000 <= address < address + size <= 0x24078000, (name, hex(address), size)
                    executable_sections[name] = dict(address=hex(address), bytes=size)
        assert ".text" in executable_sections
        assert binary.stat().st_size <= 480 * 1024
        assert "rmx::embedded::loadBootCard(" in symbols and "rmx::storage::load(" in symbols
        assert "rmx::sample_reader::initializeTable()" in symbols
        assert ("rmx::embedded::ExternalAudio::dispatch(" in symbols) == (profile == "external")
        assert "rmx::sample_reader::kernelLevel<" not in symbols, (
            "Uncompressed reference table leaked into ARM image"
        )
        profiles[profile] = dict(
            binary=str(binary.relative_to(REPO)),
            binary_bytes=binary.stat().st_size,
            binary_sha256=sha(binary),
            elf_sha256=sha(elf),
            sections=sections,
            executable_sections=executable_sections,
            sdmmc_dma_address=hex(dma),
            sdmmc_dma_bytes=dma_bytes,
            kernel_sdram_address=hex(kernels),
            kernel_sdram_bytes=kernel_bytes,
            cross_compiled=True,
            flashed=False,
            hardware_verified=False,
        )
    files = []
    for folder in [HERE, REPO / "include/rmx", REPO / "src/core"]:
        files += [
            p
            for p in folder.rglob("*")
            if p.is_file()
            and not any(
                part.startswith("build") or part == "__pycache__" for part in p.relative_to(folder).parts
            )
            and (
                p.suffix in (".h", ".cpp", ".py", ".json", ".md", ".inc")
                or p.name in ("Makefile", "CMakeLists.txt")
            )
        ]
    files += [p for p in HERE.parent.iterdir() if p.is_file() and p.suffix in (".h", ".cpp", ".ld", ".json")]
    files += list((REPO / "tests").glob("*_tests.cpp")) + [REPO / "tools/memory_budget.cpp"]
    files += list((REPO / "hardware/runtime/tests/support").glob("*.h"))
    report = dict(
        revision="F06",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope="Maintained DSP engine in SRAM-boot firmware; host behavior, exact kernel transport and ARM linking; no physical verification",
        maintained_parameters=int(settings.group(1)),
        advanced_user_settings=int(settings.group(2)),
        libdaisy_commit=pinned,
        compiler_version=compiler_version,
        sdk_archive_sha256=sha(sdk_archive),
        sdk_makefile_sha256=sha(sdk / "Makefile"),
        sdk_clean_rebuild_performed=True,
        host_tests_passed=len(cases),
        test_summaries=summaries,
        profiles=profiles,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(set(files))},
        shared_kernel_transport_opt_in=True,
        coefficient_quantization=False,
        calibration_qspi_sectors_unchanged=["0x007f0000", "0x007f1000"],
        physical_controls_verified=False,
        real_time_audio_verified=False,
        build_ready=False,
        limitations=[
            "No MCU callback deadline, SDRAM/cache integrity, storage, sensor or audio performance measurement",
            "Read-only boot loading; no hot reload/card writing/original RSD compatibility",
            "Each sample limited to 96000 decoded frames and 2 seconds; not complete RMX or desktop media compatibility",
            "Cold boot budget is cooperative; blocking vendor SD operations can exceed 8 seconds",
            "Fault Panic intentionally clears recorded sequence, scene and isolator engagement; fresh gestures required",
            "Firmware build does not qualify electrical, mechanical, converter or full-unit behavior",
        ],
    )
    report["evidence_sha256"] = {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p != record}
    record.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"F06: {len(cases)} host groups pass; both exact-kernel SRAM profiles link; physical qualification remains open"
    )


if __name__ == "__main__":
    main()
