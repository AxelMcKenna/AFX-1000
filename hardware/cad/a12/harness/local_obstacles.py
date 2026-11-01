"""Actual native local obstacle solids for ranking source-wire proposals.

Clipped surfaces are a routing diagnostic. Every selected route still requires
the full native component/case/hardware/PCB and wire-pair intersection checks.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.thermal.verify import binary_stl

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/source-obstacles"


def main(executable):
    _, _, hashes = snapshot()
    hashes[str(Path(__file__).relative_to(REPO))] = sha(Path(__file__))
    OUT.mkdir(parents=True, exist_ok=True)
    source = "include <" + str(ROOT.parent / "thermal-integration.scad") + '>\ntrial="case";\n'
    source += (
        """module window(){translate([154,104,3])cube([31,35,34]);}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
if(trial=="case")intersection(){window();case_parts();}
if(trial=="return")intersection(){window();return_assembly();}
if(trial=="positive")intersection(){window();import("""
        + json.dumps(str(ROOT.parent / "positive_links/generated/positive-links.stl"))
        + """);}
if(trial=="switch_lead_witness")intersection(){case_parts();translate([163.9,109.9,23])cube([.2,.2,.2]);}
"""
    )
    scad = OUT / "obstacles.scad"
    scad.write_text(source)
    hashes[str(scad.relative_to(REPO))] = sha(scad)
    cases = {}
    for name in ["case", "return", "positive", "switch_lead_witness"]:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="local_obstacles_only"']
        cmd += ["-D", 'trial="' + name + '"', "-o", str(target), str(scad)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = (
            p.returncode == 0
            and target.exists()
            and "NoError" in log
            and not any(s in log for s in ["WARNING", "ERROR"])
        )
        row = dict(accepted=False, returncode=p.returncode, command=cmd)
        if clean:
            stats = binary_stl(target)
            valid = (
                math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
                if name.endswith("witness")
                else stats["volume_mm3"] > 1
            )
            row.update(accepted=valid, **stats)
        cases[name] = row
        print(name, row.get("accepted"), row.get("volume_mm3"), flush=True)
    changed = [n for n, h in hashes.items() if sha(REPO / n) != h]
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        cases=cases,
        changed_inputs=changed,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in (".log", ".stl")
        },
        window_min_mm=[154, 104, 3],
        window_max_mm=[185, 139, 37],
        actual_local_obstacle_solids_accepted=not changed and all(c["accepted"] for c in cases.values()),
        artificial_clipping_faces_present=True,
        full_route_native_validation_required=True,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    result = main(parser.parse_args().openscad)
    raise SystemExit(0 if result["actual_local_obstacle_solids_accepted"] else 1)
