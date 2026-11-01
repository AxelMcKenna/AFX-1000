"""Run source-bound native packaging checks and a deliberately colliding control."""

import argparse
import json
import math
import struct
import subprocess
from pathlib import Path

from .generate import OUT, REPO, ROOT, sha
from .generate import main as generate


def stl_volume(path):
    """Signed tetrahedral volume for OpenSCAD's explicitly selected binary STL."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count and count > 0
    terms = []
    for index in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * index)
        a, b, c = row[3:6], row[6:9], row[9:12]
        terms.append(
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    return abs(math.fsum(terms)) / 6


def verify(executable):
    generate()
    outputs = REPO / "build/artifacts/cad/a12"
    outputs.mkdir(parents=True, exist_ok=True)
    allocation = json.loads((OUT / "allocation.json").read_text())
    sources = dict(allocation["source_sha256"])
    for p in [ROOT / "verify.py", *OUT.glob("*.scad")]:
        sources[str(p.relative_to(REPO))] = sha(p)
    version = subprocess.run([str(executable), "--version"], capture_output=True, text=True, check=True)
    checks = {}
    for part in [
        "collision",
        "board_collision",
        "inlet_collision",
        "inlet_board_collision",
        "unrelieved_positive_control",
    ]:
        target = outputs / (part + ".stl")
        target.unlink(missing_ok=True)
        command = [
            str(executable),
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            f'part="{part}"',
            "-o",
            str(target),
            str(ROOT / "integration.scad"),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        log = result.stdout + result.stderr
        logfile = OUT / (part + ".log")
        logfile.write_text(log)
        if part == "unrelieved_positive_control":
            assert result.returncode == 0 and target.exists(), log
            volume = stl_volume(target)
            assert volume > 1, ("Positive control did not detect boss interference", volume)
            checks[part] = dict(
                result="expected collision detected", volume_mm3=volume, stl_sha256=sha(target)
            )
        else:
            assert result.returncode == 1 and "Current top level object is empty." in log, log
            assert "WARNING" not in log and "ERROR" not in log, log
            target.unlink(missing_ok=True)
            checks[part] = dict(result="empty intersection")
        checks[part]["log_sha256"] = sha(logfile)
    assert all(sha(REPO / name) == expected for name, expected in sources.items()), (
        "Source changed during native verification"
    )
    report = dict(
        revision="A12-development",
        native_engine=(version.stdout + version.stderr).strip(),
        checks=checks,
        allocation_sha256=sha(OUT / "allocation.json"),
        source_sha256=sources,
        native_repaired_pcb_bound=False,
        physical_fit_verified=False,
        fabrication_released=False,
        limitation="Conservative supply allocation only; actual repaired PCB/component integration, inlet/harness, terminal stack/supports and thermal verification are still required",
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "A12: conservative reserve clears native housing/control/electronics geometry; unrelieved positive control collides"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True, type=Path)
    verify(parser.parse_args().openscad.resolve())
