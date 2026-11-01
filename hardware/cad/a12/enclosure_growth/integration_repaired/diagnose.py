"""Named-piece failure isolation and a prospective unchanged-part J29 pose."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

from .stage import A12, OUT, REPO, ROOT, sha

D = ROOT / "diagnostics"


def run(executable):
    source = OUT / "checks.scad"
    meta = json.loads((OUT / "analysis.json").read_text())
    scene = json.loads((OUT / "scene.json").read_text())
    parts = A12 / "positive_links/generated"
    proposed = []
    for b in scene["inherited_envelopes"]:
        if b[0].startswith("e19_J29"):
            row = list(b)
            row[1] -= 66.4
            row[2] -= 21.3
            proposed.append(row)
    assert len(proposed) == 4
    s = "include <" + str(source) + ">\n" + "diag_rows=" + json.dumps(proposed) + ";\n"
    s += """
diag_case="pedestal";
module diag_J29(){ui_boxes([for(b=ui_inherited_envelopes)if(b[0]=="e19_J29")b]);}
module diag_pedestal(){import("PEDESTAL");}
module diag_proposal(){ui_boxes(diag_rows,.25);}
module diag_existing(){for(b=ui_native_boards)ui_native_PCB(b);for(b=ui_other_boards)board_reserve(b);ui_components();ui_receiver_joint();ui_source_joint();tc2_board();tc2_posts();tc2_heads();}
if(diag_case=="pedestal")intersection(){diag_pedestal();diag_J29();}
if(diag_case=="copper_collision")intersection(){import("DIGCU");diag_J29();}
if(diag_case=="returns_collision")intersection(){return_assembly();diag_J29();}
if(diag_case=="without_pedestal_collision")intersection(){difference(){ui_power_only();diag_pedestal();}diag_J29();}
if(diag_case=="proposed_geometry")diag_proposal();
if(diag_case=="proposed_electronics_collision")intersection(){diag_proposal();diag_existing();}
if(diag_case=="proposed_power_collision")intersection(){diag_proposal();ui_power_only();}
if(diag_case=="proposed_controls_case_collision")intersection(){diag_proposal();ui_environment();}
if(diag_case=="proposed_positive_control")intersection(){diag_proposal();translate([100,78,10])cube([.2,.2,.2]);}
"""
    s = s.replace("PEDESTAL", str(parts / "BONDED-PEDESTAL.stl")).replace("DIGCU", str(parts / "DIG-CU.stl"))
    (D / "checks.scad").write_text(s)
    inputs = {
        str(p.relative_to(REPO)): sha(p)
        for p in [
            Path(__file__),
            source,
            OUT / "analysis.json",
            OUT / "scene.json",
            D / "checks.scad",
            parts / "BONDED-PEDESTAL.stl",
            parts / "DIG-CU.stl",
        ]
    }
    cases = {}
    names = [
        "pedestal",
        "copper_collision",
        "returns_collision",
        "without_pedestal_collision",
        "proposed_geometry",
        "proposed_electronics_collision",
        "proposed_power_collision",
        "proposed_controls_case_collision",
        "proposed_positive_control",
    ]
    for name in names:
        target = D / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key, value in dict(
            part="diag_only",
            thermal_part="diag_only",
            positive_part="diag_only",
            candidate_case="diag_only",
            trial="diag_only",
            ui_case="diag_only",
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=meta["nine_lid_boss_positions_mm"],
            board_mounts=scene["mounts"],
            rear_ports=meta["rear_ports"],
            diag_case=name,
        ).items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(D / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (D / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        stats = binary_stl(target) if p.returncode == 0 and target.exists() else None
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        expected_empty = name.endswith("collision")
        ok = clean and (
            empty if expected_empty else stats and "NoError" in log and stats["volume_mm3"] > 0.001
        )
        if name == "pedestal":
            ok &= stats is not None and math.isclose(stats["volume_mm3"], 25.53750514984131, abs_tol=1e-6)
        if name.endswith("positive_control"):
            ok &= stats is not None and math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
        cases[name] = dict(
            evidence_valid=bool(ok),
            expected_empty=expected_empty,
            empty=empty,
            returncode=p.returncode,
            statistics=stats,
            command=cmd,
        )
        print(name, bool(ok), stats["volume_mm3"] if stats else None, flush=True)
    changed = [n for n, h in inputs.items() if sha(REPO / n) != h]
    report = dict(
        source_sha256=inputs,
        artifact_sha256={
            str(p.relative_to(REPO)): sha(p) for p in D.iterdir() if p.suffix in [".log", ".stl"]
        },
        cases=cases,
        changed_inputs=changed,
        all_evidence_valid=all(r["evidence_valid"] for r in cases.values()) and not changed,
        proposed_pin1_world_mm=[104, 78.5],
        proposed_native_at_mm=[174, 136.5, -90],
        proposed_service_body=next(r for r in proposed if r[0] == "e19_J29"),
        actual_PCB_adopted=False,
        actual_drill_and_routing_legal=False,
        physical_qualified=False,
    )
    (D / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--openscad", type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(not run(a.openscad)["all_evidence_valid"])
