#!/usr/bin/env python3
"""Build F05 boot-storage host tests and both real ARM profiles; never flash."""

import argparse
import datetime
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "hardware/validation/standalone-storage"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, log=None):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True, text=True)
    text = result.stdout + result.stderr
    if log:
        (OUT / log).write_text(text)
    if result.returncode:
        raise RuntimeError(" ".join(map(str, args)) + "\n" + "\n".join(text.splitlines()[-30:]))
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, default=ROOT / "build-hardware/libDaisy")
    parser.add_argument("--host-build", type=Path, default=ROOT / "build/standalone-storage-host")
    args = parser.parse_args()
    sdk, toolchain, host = args.sdk.resolve(), args.toolchain.resolve(), args.host_build.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "verification.json"
    report_path.unlink(missing_ok=True)
    pinned = json.loads((ROOT / "hardware/firmware/dependencies.json").read_text())["libDaisy"]["commit"]
    assert run(["git", "-C", sdk, "rev-parse", "HEAD"]).strip() == pinned
    assert not run(["git", "-C", sdk, "status", "--porcelain", "--untracked-files=no"]).strip()
    run(
        ["cmake", "-S", ROOT / "hardware/runtime", "-B", host, "-DCMAKE_BUILD_TYPE=Release"],
        "host-configure.txt",
    )
    run(["cmake", "--build", host, "--parallel", "4"], "host-build.txt")
    run(
        ["ctest", "--test-dir", host, "--output-on-failure", "--output-junit", OUT / "host-tests.xml"],
        "host-tests.txt",
    )
    cases = ET.parse(OUT / "host-tests.xml").getroot().findall(".//testcase")
    assert len(cases) == 27 and any(c.attrib["name"] == "boot_storage" for c in cases)
    assert all(c.find("failure") is None and c.find("skipped") is None for c in cases)
    summary = run([host / "rmx_boot_storage_tests"]).strip()
    profiles = {}
    for profile in ["onboard", "external"]:
        directory = ROOT / "hardware/firmware" / ("build-storage-" + profile)
        target = "rmx_standalone" + ("_external" if profile == "external" else "")
        run(
            [
                "make",
                "-C",
                ROOT / "hardware/firmware",
                "PROFILE=" + profile,
                "BUILD_DIR=" + directory.name,
                "-j4",
                "GCC_PATH=" + str(toolchain),
                "LIBDAISY_DIR=" + str(sdk),
            ],
            "arm-" + profile + "-build.txt",
        )
        elf, binary = directory / (target + ".elf"), directory / (target + ".bin")
        sections = {}
        for line in run([toolchain / "arm-none-eabi-size", "-A", elf]).splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[0].startswith(".") and fields[1].isdigit():
                sections[fields[0]] = dict(bytes=int(fields[1]), address=hex(int(fields[2])))
        symbols = run([toolchain / "arm-none-eabi-nm", "-S", "-C", elf])
        dma = [line.split() for line in symbols.splitlines() if "bootSdDmaStorage" in line]
        assert len(dma) == 1
        address, length = int(dma[0][0], 16), int(dma[0][1], 16)
        assert address % 32 == 0 and 0x24000000 <= address < address + length <= 0x24078000
        assert length == sections[".sdmmc_bss"]["bytes"]
        assert sections[".sdram_bss"]["bytes"] == 48 * 1024 * 1024
        assert sections[".sram1_bss"]["bytes"] <= 32768
        assert sections[".bss"]["bytes"] + sections[".data"]["bytes"] < 120 * 1024
        assert "rmx::embedded::loadBootCard(" in symbols and "rmx::storage::load(" in symbols
        assert ("rmx::embedded::ExternalAudio::dispatch(" in symbols) == (profile == "external")
        profiles[profile] = dict(
            binary=str(binary.relative_to(ROOT)),
            binary_bytes=binary.stat().st_size,
            binary_sha256=sha(binary),
            elf_sha256=sha(elf),
            sections=sections,
            sdmmc_dma_address=hex(address),
            sdmmc_dma_bytes=length,
            cross_compiled=True,
            flashed=False,
            hardware_verified=False,
        )
    files = []
    for folder in [ROOT / "hardware/runtime", ROOT / "hardware/firmware"]:
        files += [
            p
            for p in folder.rglob("*")
            if p.is_file()
            and not any(
                part.startswith("build") or part == "__pycache__" for part in p.relative_to(folder).parts
            )
            and (
                p.suffix in (".h", ".cpp", ".py", ".json", ".md", ".ld")
                or p.name in ("Makefile", "CMakeLists.txt")
            )
        ]
    sdk_files = [
        "src/sys/fatfs.h",
        "src/sys/fatfs.cpp",
        "src/util/sd_diskio.c",
        "src/per/sdmmc.h",
        "src/sys/ffconf.h",
        "core/STM32H750IB_sram.lds",
        "Middlewares/Third_Party/FatFs/src/option/ccsbcs.c",
    ]
    report = dict(
        revision="F05",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope="Read-only boot SD sample/preset/user-profile loading before audio; host data/fault tests and both ARM builds, no physical test",
        profiles=profiles,
        host_tests_passed=len(cases),
        boot_storage_test_summary=summary,
        libdaisy_commit=pinned,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(files))},
        sdk_source_sha256={p: sha(sdk / p) for p in sdk_files},
        maximum_decoded_bank_bytes=16 * 96000 * 8,
        maximum_staged_sample_bytes=96000 * 8,
        inter_operation_budget_ms=8000,
        hard_wall_clock_deadline_verified=False,
        calibration_qspi_sectors_unchanged=["0x007f0000", "0x007f1000"],
        physical_storage_verified=False,
        build_ready=False,
        limitations=[
            "SD socket/detect wiring, card current/inrush and supply margins unqualified",
            "SDK calls can overrun the 8 s inter-operation budget; vendor SD reads use 30 s polling limits, so this is not a hard 8 s boot deadline",
            "Actual SDMMC DMA/cache behavior, card removal, startup time and audio timing need hardware measurement",
            "Only cold-boot reading is implemented; no hot reload, card writing, original RSD compatibility or complete desktop preset compatibility",
            "Per sample limits are 96000 decoded frames and 2 s duration, 8-96 kHz mono/stereo PCM16/24/32 or float32; full extended WAV format is rejected",
            "The original F04 calibration, converter, latch and input-settling protections remain; their physical qualification is still open",
        ],
    )
    report["evidence_sha256"] = {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p != report_path}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(summary)
    print(
        "F05:27 host tests pass; both ARM profiles cross-compile; SD buffers in AXI SRAM; no physical qualification"
    )


if __name__ == "__main__":
    main()
