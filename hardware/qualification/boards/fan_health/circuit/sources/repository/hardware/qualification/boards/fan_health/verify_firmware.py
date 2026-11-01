"""Build/test FH01 software; this does not qualify the hardware adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avr-bin", type=Path, required=True)
    parser.add_argument("--compiler-archive", type=Path, required=True)
    parser.add_argument("--host-cc", default="clang")
    args = parser.parse_args()
    expected = "f6ed2346953fcf88df223469088633eb86de997fa27ece117fd1ef170d69c1f8"
    if sha(args.compiler_archive) != expected:
        raise SystemExit("Compiler archive differs from official Arduino index checksum")
    installed_files = 0
    with tarfile.open(args.compiler_archive, "r:bz2") as archive:
        for member in archive:
            if not (member.isfile() or member.issym() or member.islnk()):
                continue
            pieces = Path(member.name).parts
            if pieces[0] != "avr" or ".." in pieces:
                raise SystemExit("Unexpected toolchain archive member")
            target = args.avr_bin.parent.joinpath(*pieces[1:])
            stream = archive.extractfile(member)
            if stream is None or hashlib.sha256(stream.read()).hexdigest() != sha(target):
                raise SystemExit(f"Installed toolchain differs from archive: {member.name}")
            installed_files += 1
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    commands = []

    def run(argv: list[str], log: str) -> str:
        result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
        (out / log).write_text(result.stdout + result.stderr)
        commands.append({"argv": argv, "returncode": result.returncode, "log": log})
        if result.returncode:
            raise SystemExit(f"Command failed; see {out / log}")
        return result.stdout

    host = str(out / "host_test")
    run([args.host_cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
         "-fsanitize=address,undefined", "firmware/health.c", "firmware/test_health.c",
         "-o", host], "host_compile.log")
    host_result = run([host], "host_test.log").strip()
    gcc = str(args.avr_bin / "avr-gcc")
    version = run([gcc, "--version"], "compiler_version.log").splitlines()[0]
    flags = ["-std=gnu11", "-mmcu=attiny84", "-Os", "-Wall", "-Wextra", "-Werror",
             "-ffunction-sections", "-fdata-sections"]
    for name in ("health", "attiny84a", "startup"):
        # The isolated naked startup function has no compiler stack estimate.
        stack_flags = [] if name == "startup" else ["-fstack-usage"]
        run([gcc, *flags, *stack_flags, "-c", f"firmware/{name}.c", "-o", f"generated/{name}.o"],
            f"{name}_compile.log")
    run([gcc, "-mmcu=attiny84", "-Wl,--gc-sections,-Map=generated/fan_health.map",
         "generated/health.o", "generated/attiny84a.o", "generated/startup.o",
         "-o", "generated/fan_health.elf"],
        "target_link.log")
    run([str(args.avr_bin / "avr-objcopy"), "-O", "ihex", "-R", ".eeprom",
         "generated/fan_health.elf", "generated/fan_health.hex"], "hex_export.log")
    size = run([str(args.avr_bin / "avr-size"), "generated/fan_health.elf"], "target_size.log")
    run([str(args.avr_bin / "avr-objdump"), "-d", "generated/fan_health.elf"], "target_disassembly.log")
    rows = size.splitlines()[1].split()
    text_bytes, data_bytes, bss_bytes = map(int, rows[:3])
    assert text_bytes + data_bytes <= 8192
    assert data_bytes + bss_bytes < 512
    inputs = [*sorted((ROOT / "firmware").glob("*")), Path(__file__)]
    outputs = [p for p in sorted(out.iterdir()) if p.name != "verification.json" and p.is_file()]
    report = {
        "scope": "FH01 C engine host tests and ATtiny84 target compilation only",
        "host_result": host_result,
        "compiler": version,
        "compiler_archive_sha256": expected,
        "installed_toolchain_files_matching_archive": installed_files,
        "compiler_archive_url": "https://downloads.arduino.cc/tools/avr-gcc-7.3.0-atmel3.6.1-arduino7-x86_64-apple-darwin14.tar.bz2",
        "text_bytes": text_bytes, "data_bytes": data_bytes, "bss_bytes": bss_bytes,
        "stack_worst_case_qualified": False,
        "target_execution_verified": False,
        "clock_adc_interrupts_watchdogs_verified": False,
        "native_schematic_implemented": False,
        "fabrication_release": False,
        "commands": commands,
        "inputs": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        "outputs": {str(p.relative_to(ROOT)): sha(p) for p in outputs},
    }
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(host_result)
    print(size.strip())


if __name__ == "__main__":
    main()
