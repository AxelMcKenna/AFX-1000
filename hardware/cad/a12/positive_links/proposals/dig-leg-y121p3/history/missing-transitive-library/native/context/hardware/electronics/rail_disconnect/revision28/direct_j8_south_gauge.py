"""Separate south-clock trial, including the complete replacement screw head.

The earlier failed trial is immutable. Both the declared inflated assembly
screen and uninflated geometry are reported; a nominal fit never waives the
inflated screen or qualifies dimensions, thread engagement or electrical use.
"""

import argparse
import json
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

from .direct_j8_gauge import OUT, REPO, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--openscad", required=True)
    args = p.parse_args()
    first = json.loads((OUT / "verification.json").read_text())
    inputs = {
        str(path.relative_to(REPO)): sha(path)
        for path in (Path(__file__), OUT / "verification.json", OUT / "gauge.scad", OUT / "capture.json")
    }
    cases = {}
    for label, obstacle in (("electronics", "electronics"), ("positive", "positive_hardware"),
                            ("returns", "other_returns")):
        cases["south_lug_inflated_" + label] = "intersection(){expanded()lug();" + obstacle + "();}"
        cases["south_complete_inflated_" + label] = "intersection(){expanded()attachment();" + obstacle + "();}"
        cases["south_complete_nominal_" + label] = "intersection(){attachment();" + obstacle + "();}"
    cases["south_attachment"] = "attachment();"
    cases["south_positive_control"] = "intersection(){lug();located()translate([7,-.1,.1])cube([.2,.2,.2]);}"
    cases["known_bad_clock_negative_control"] = (
        "intersection(){minkowski(){translate([132,129.5,15.1])rotate([0,0,-20])"
        "{local_flat();local_barrel();}cube([1.8,1.8,1.8],center=true);}positive_hardware();}"
    )
    source = 'include <gauge.scad>\nmodule attachment(){lug();washer_head();}\n'
    source += "\n".join('if(part=="' + name + '"){' + expression + "}" for name, expression in cases.items())
    scad = OUT / "south-complete.scad"
    scad.write_text(source)
    inputs[str(scad.relative_to(REPO))] = sha(scad)
    rows = {}
    for name in cases:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        command = [args.openscad, "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl",
                   "-D", 'part="' + name + '"', "-D", "angle=90", "-o", str(target), str(scad)]
        run = subprocess.run(command, capture_output=True, text=True, timeout=120)
        log = run.stdout + run.stderr
        (OUT / (name + ".log")).write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, (name, log)
        if run.returncode == 1 and "Current top level object is empty." in log:
            target.unlink(missing_ok=True)
            rows[name] = dict(volume_mm3=0, result="empty", command=command)
        else:
            assert run.returncode == 0 and "NoError" in log and target.exists(), (name, log)
            rows[name] = dict(result="valid native manifold", command=command, **binary_stl(target))
        print(name, rows[name]["volume_mm3"], flush=True)
    changed = [path for path, value in inputs.items() if sha(REPO / path) != value]
    stale = [path for path, value in first["capture"]["source_sha256"].items() if sha(REPO / path) != value]
    failures = [name for name, row in rows.items()
                if ("inflated" in name or "nominal" in name) and row["volume_mm3"] > 1e-6]
    assert rows["south_positive_control"]["volume_mm3"] > 0.0079
    assert rows["known_bad_clock_negative_control"]["volume_mm3"] > 1
    report = dict(
        scope="Private +90-degree clock trial; whole attachment includes maximum-stock washer and screw head",
        source_native_PCB_SHA256=first["capture"]["native_pcb_sha256"],
        input_sha256=inputs, native_results=rows,
        unchanged_receiving_bounds=True,
        declared_neighbor_inflation_mm=0.9,
        nominal_geometry_is_not_a_manufacturing_or_position_bound=True,
        changed_inputs=changed, stale_sources=stale,
        collision_failures=failures,
        full_declared_gauge_screen_passed=not changed and not stale and not failures,
        all_physical_and_electrical_qualification=False,
    )
    report["native_evidence_sha256"] = {
        str(path.relative_to(REPO)): sha(path) for path in OUT.iterdir()
        if path.suffix in (".stl", ".log") and path.stem.startswith(("south_", "known_bad_clock_"))
    }
    (OUT / "south-complete-review.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not changed and not stale


if __name__ == "__main__":
    main()
