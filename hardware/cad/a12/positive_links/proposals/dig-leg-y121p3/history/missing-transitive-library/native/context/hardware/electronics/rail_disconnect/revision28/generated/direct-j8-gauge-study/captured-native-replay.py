"""Replay captured native geometry without re-extracting changing repo boards."""

import argparse
import hashlib
import json
import math
import struct
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def volume(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert count > 0 and len(data) == 84 + 50 * count
    terms = []
    for i in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * i)
        a, b, c = row[3:6], row[6:9], row[9:12]
        terms.append(a[0] * (b[1] * c[2] - b[2] * c[1])
                     + a[1] * (b[2] * c[0] - b[0] * c[2])
                     + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return abs(math.fsum(terms)) / 6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    assert output != root and root not in output.parents, "Replay into a separate scratch directory"
    output.mkdir(parents=True, exist_ok=False)
    index_path = root / "captured-replay-inputs.json"
    index = json.loads(index_path.read_text())
    assert all(sha(root / p) == h for p, h in index["relative_input_sha256"].items())
    results = {}
    for identity, case in index["cases"].items():
        target = output / (identity + ".stl")
        command = [args.openscad, "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl",
                   "-D", 'part="' + case["part"] + '"', "-D", "angle=" + str(case["angle_deg"]),
                   "-o", str(target), str(root / case["scad"])]
        run = subprocess.run(command, capture_output=True, text=True, timeout=120)
        log = run.stdout + run.stderr
        (output / (identity + ".log")).write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, (identity, log)
        if run.returncode == 1 and "Current top level object is empty." in log:
            target.unlink(missing_ok=True)
            actual = 0.0
        else:
            assert run.returncode == 0 and "NoError" in log and target.exists(), (identity, log)
            actual = volume(target)
        assert math.isclose(actual, case["expected_volume_mm3"], rel_tol=1e-6, abs_tol=1e-5), (identity, actual, case)
        results[identity] = dict(command=command, actual_volume_mm3=actual,
                                 expected_volume_mm3=case["expected_volume_mm3"], agrees=True)
        print(identity, actual, flush=True)
    assert all(sha(root / p) == h for p, h in index["relative_input_sha256"].items())
    report = dict(
        captured_input_index_sha256=sha(index_path), results=results,
        all_recorded_failures_and_controls_reproduced=True,
        physical_electrical_fabrication_qualified=False,
    )
    report["output_sha256"] = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
