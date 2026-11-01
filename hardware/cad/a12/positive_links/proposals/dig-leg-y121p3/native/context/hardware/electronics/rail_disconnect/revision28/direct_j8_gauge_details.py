"""Retain exact first-gauge failures; localize and screen explicit clock angles."""

import argparse
import json
import subprocess

from hardware.cad.a12.thermal.verify import binary_stl

from .direct_j8_gauge import OUT, REPO, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True)
    args = parser.parse_args()
    original = OUT / "verification.json"
    data = json.loads(original.read_text())
    assert data["collision_failures"] == ["positive_hardware_collision", "other_returns_collision"]
    assert not data["stale_sources"] and not data["changed_inputs"]
    inputs = {str(original.relative_to(REPO)): sha(original),
              str((OUT / "gauge.scad").relative_to(REPO)): sha(OUT / "gauge.scad"),
              str(__file__.replace(str(REPO) + "/", "")): sha(__import__("pathlib").Path(__file__))}
    rows = {}
    cases = []
    for mesh in sorted((OUT / "native-inputs").glob("*.stl")):
        if mesh.name == "AFX-A12-R01-DIG-BAR.stl":
            continue
        cases.append(("detail-" + mesh.stem, -20, 'import("native-inputs/' + mesh.name + '");'))
    for angle in (-90, -120, -150):
        for label, module in (("electronics", "electronics"), ("positive", "positive_hardware"),
                              ("returns", "other_returns")):
            cases.append((f"clock{angle}-" + label, angle, module + "();"))
    for name, angle, obstacle in cases:
        scad = OUT / (name + ".scad")
        scad.write_text('include <gauge.scad>\nintersection(){expanded()lug();' + obstacle + '}\n')
        inputs[str(scad.relative_to(REPO))] = sha(scad)
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [args.openscad, "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl",
               "-D", 'part="detail"', "-D", "angle=" + str(angle), "-o", str(target), str(scad)]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        log = run.stdout + run.stderr
        (OUT / (name + ".log")).write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, (name, log)
        if run.returncode == 1 and "Current top level object is empty." in log:
            target.unlink(missing_ok=True)
            rows[name] = dict(volume_mm3=0, result="empty", angle_deg=angle, command=cmd)
        else:
            assert run.returncode == 0 and "NoError" in log and target.exists(), (name, log)
            rows[name] = dict(result="valid native manifold", angle_deg=angle, command=cmd, **binary_stl(target))
        print(name, rows[name]["volume_mm3"], flush=True)
    changed = [p for p, h in inputs.items() if sha(REPO / p) != h]
    report = dict(
        input_sha256=inputs, native_results=rows, changed_inputs=changed,
        scope="Clock screen only; no changed receiving bounds or manufacturer-max claim",
        all_physical_and_electrical_qualification=False,
    )
    report["native_evidence_sha256"] = {
        str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir()
        if p.suffix in (".stl", ".log") and p.stem.startswith(("clock", "detail-"))
    }
    (OUT / "clock-detail-review.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not changed


if __name__ == "__main__":
    main()
