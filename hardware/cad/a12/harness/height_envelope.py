"""Native shell-plus-controls height audit for retained and raised-shell studies.

The thermal interface's 66.8mm value ends at the plastic shell. This separate
audit includes knobs, selector caps, key travel, release-lever travel and feet.
No mass, compression, dimensional-production or whole-assembly approval follows.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a11.integration import assignments
from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.thermal.verify import binary_stl

from ..generate import REPO, sha

OUT = Path(__file__).resolve().parent / "generated/height-envelope"


def run(executable):
    _, _, hashes = snapshot()
    hashes[str(Path(__file__).relative_to(REPO))] = sha(Path(__file__))
    OUT.mkdir(parents=True, exist_ok=True)
    controls = assignments(REPO / "hardware/cad/a11/generated/controls.scad")
    max_knob = max(k[4] for k in controls["knobs"])
    source = """include <../../../thermal-integration.scad>
module outer_controls(){
 for(k=knobs)translate([k[1],k[2],shell_height+2.8])knob(k[3],k[4]);
 for(b=buttons)button_pose(b)key_sweep(b);
 for(c=caps)if(c[1]=="switch")translate([c[2],c[3],panel_z])selector_cap();
 translate([0,0,shell_height-38])lever_sweep();
}
// Include the actual shell and rear panel to avoid confusing a controls-only
// bounding box with an assembled mechanical envelope. Internal material and
// lower base fins stay between these extrema; they are not a collision audit.
retained_thermal_shell();rear_panel();outer_controls();thermal_feet();
"""
    scad = OUT / "height.scad"
    scad.write_text(source)
    inputs = {str(scad.relative_to(REPO)): sha(scad)}
    rows = []
    for height in (38, 54):
        target = OUT / ("shell-" + str(height) + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for name in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", name + '="height_audit_only"']
        cmd += ["-D", "shell_height=" + str(height), "-o", str(target), str(scad)]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = process.stdout + process.stderr
        log_path = OUT / ("shell-" + str(height) + ".log")
        log_path.write_text(log)
        assert (
            process.returncode == 0 and "NoError" in log and not any(s in log for s in ("WARNING", "ERROR"))
        ), "Native height geometry rejected"
        observed = binary_stl(target)
        expected_top = height + 2.8 + max_knob
        assert math.isclose(observed["max_mm"][2], expected_top, abs_tol=1e-4)
        assert math.isclose(observed["min_mm"][2], -28.8, abs_tol=1e-4)
        row = dict(
            shell_height_mm=height,
            native_geometry=observed,
            shell_plus_thermal_feet_height_mm=height + 28.8,
            nominal_overall_height_including_controls_mm=observed["max_mm"][2] - observed["min_mm"][2],
            expected_knob_top_z_mm=expected_top,
            command=cmd,
        )
        rows.append(row)
        print(height, row["nominal_overall_height_including_controls_mm"], flush=True)
    changed = [n for n, h in {**hashes, **inputs}.items() if sha(REPO / n) != h]
    report = dict(
        scope="Native mechanical outer Z envelope; no full integration, structural or physical qualification",
        cases=rows,
        source_sha256=hashes,
        evidence_inputs_sha256=inputs,
        changed_inputs=changed,
        native_height_audit_accepted=not changed,
        thermal_interface_height_excludes_controls=True,
        enclosure_height_adopted=False,
        physical_fit_verified=False,
        fabrication_released=False,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in (".stl", ".log")
        },
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not changed, "Height audit source changed"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    run(parser.parse_args().openscad)
