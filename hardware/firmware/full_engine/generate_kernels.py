"""Losslessly pack the maintained sinc kernels; no coefficient quantization."""

import argparse
import hashlib
import json
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def pack(raw):
    floats = struct.unpack("<" + "I" * (len(raw) // 4), raw)
    out = bytearray()
    per = 1 + 33 * 64
    for level in range(33):
        words = floats[level * per : (level + 1) * per]
        out.extend(struct.pack("<I", words[0]))
        for phase in range(17):
            out.extend(struct.pack("<64I", *words[1 + phase * 64 : 1 + (phase + 1) * 64]))
        for phase in range(17, 33):
            for tap in range(64):
                value = words[1 + phase * 64 + tap] ^ words[1 + (32 - phase) * 64 + (63 - tap)]
                while value >= 128:
                    out.append((value & 127) | 128)
                    value >>= 7
                out.append(value)
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="c++")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rmx-kernel-reference-") as folder:
        tmp = Path(folder)
        source = tmp / "dump.cpp"
        binary = tmp / "dump"
        source.write_text(
            '#include "rmx/SampleReader.h"\n#include <iostream>\n#include <bit>\nint main(){static_assert(std::endian::native==std::endian::little);static_assert(sizeof(rmx::sample_reader::Level)==8452);static_assert(rmx::sample_reader::levels==33&&rmx::sample_reader::phases==32&&rmx::sample_reader::taps==64);for(auto* level:rmx::sample_reader::table)std::cout.write(reinterpret_cast<const char*>(level),sizeof(*level));}\n'
        )
        subprocess.run(
            [args.cxx, "-std=c++20", "-O2", "-I" + str(REPO / "include"), str(source), "-o", str(binary)],
            check=True,
            capture_output=True,
        )
        raw = subprocess.check_output([str(binary)])
    assert len(raw) == 33 * 8452
    packed = pack(raw)
    crc = [zlib.crc32(raw[i * 8452 : (i + 1) * 8452]) for i in range(33)]
    header = "// Generated lossless mirror/XOR transport. Regenerate with generate_kernels.py.\n"
    header += "constexpr uint32_t expectedKernelCrc = " + hex(zlib.crc32(raw)) + ";\n"
    header += (
        "constexpr std::array<uint32_t, 33> expectedLevelCrc = {" + ",".join(hex(n) for n in crc) + "};\n"
    )
    header += "constexpr uint8_t packedKernels[] = {\n"
    header += (
        "\n".join(",".join(hex(x) for x in packed[i : i + 24]) + "," for i in range(0, len(packed), 24))
        + "\n};\n"
    )
    report = dict(
        raw_bytes=len(raw),
        packed_bytes=len(packed),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        packed_sha256=hashlib.sha256(packed).hexdigest(),
        crc32=hex(zlib.crc32(raw)),
        coefficient_quantization=False,
        source_sha256={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [REPO / "include/rmx/SampleReader.h", Path(__file__)]
        },
    )
    files = {"kernel_data.inc": header, "kernel_origin.json": json.dumps(report, indent=2) + "\n"}
    for name, text in files.items():
        p = ROOT / "generated" / name
        if args.check:
            assert p.read_text() == text, ("Stale kernel transport", name)
        else:
            p.write_text(text)
    print("Lossless kernels:", len(raw), "raw bytes ->", len(packed), "packed bytes; CRC", report["crc32"])


if __name__ == "__main__":
    main()
