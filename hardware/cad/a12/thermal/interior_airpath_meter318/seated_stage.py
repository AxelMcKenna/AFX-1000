"""Derive a separate scoped-contact fixture from exact raw19 branches."""

import json
import re

from .mating import CONTROLS, EMPTY
from .stage import OUT, ROOT, sha, write

CONTROL_GUARD = {
    "M3_directseal_overlap_control": "M3_hardware_nominal_mates",
    "M2_directseal_overlap_control": "M2_hardware_nominal_mates",
    "upper_seal_tray_overlap_control": "upper_gasket_tray",
    "upper_seal_base_overlap_control": "upper_gasket_base",
    "frame_seal_tray_overlap_control": "frame_gasket_tray",
    "frame_seal_fan_overlap_control": "frame_gasket_fan",
    "meter_seal_plate_overlap_control": "meter_gasket_wall_plate",
    "meter_seal_wall_overlap_control": "meter_gasket_wall_plate",
}
GUARDED = EMPTY[:8]
EXTRA = ["boss_radial_overlap_control", "FIP_radial_overlap_control", "FIP_axial_overlap_control"]


def build():
    path = OUT / "mating-seated.scad"
    if (ROOT / "handoff.json").exists() or path.exists():
        raise RuntimeError("Seated fixture capture is immutable")
    source = (ROOT / "mating.scad").read_text()
    branches = dict(re.findall(r'^if\(mate_case=="([^\"]+)"\)(.*)$', source, re.M))
    assert list(branches) == EMPTY + CONTROLS
    text = (
        "include <"
        + str(ROOT / "mating.scad")
        + ">\ninclude <"
        + str(ROOT / "mating_guards.scad")
        + '>\nmate_seated_case="none";\n'
    )
    for n, branch in branches.items():
        g = n if n in GUARDED else CONTROL_GUARD.get(n)
        expression = ("difference(){" + branch + "mate_guard_for(" + json.dumps(g) + ");}") if g else branch
        text += "if(mate_seated_case==" + json.dumps(n) + ")" + expression + "\n"
    text += r"""
module mate_boss_radial_overlap(){intersection(){ap_tray();for(p=ap_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-25.1])difference(){cylinder(r=3.1,h=.3,$fn=96);translate([0,0,-.01])cylinder(r=3.08,h=.32,$fn=96);}}}
module mate_FIP_radial_overlap(){intersection(){ap_baffles();for(x=[46,235.5])translate([x,137,-10])rotate([-90,0,0])cylinder(r=2.22,h=2,$fn=96);}}
module mate_FIP_axial_overlap(){intersection(){ap_baffles();translate([0,.02,0])ap_feedthroughs();}}
if(mate_seated_case=="boss_radial_overlap_control")difference(){mate_boss_radial_overlap();mate_guard_for("frame_gasket_tray");}
if(mate_seated_case=="FIP_radial_overlap_control")difference(){mate_FIP_radial_overlap();mate_guard_for("feedthrough_wall");}
if(mate_seated_case=="FIP_axial_overlap_control")difference(){mate_FIP_axial_overlap();mate_guard_for("feedthrough_wall");}
"""
    path.write_text(text)
    write(
        OUT / "mating-seat-contract.json",
        dict(
            test_only_guard_mm=0.00002,
            raw_source_sha256=sha(ROOT / "mating.scad"),
            exact_raw_branch_sha256={
                n: __import__("hashlib").sha256(b.encode()).hexdigest() for n, b in branches.items()
            },
            guarded_empty_cases=GUARDED,
            positive_controls_use_the_same_guard=CONTROL_GUARD,
            deliberate_penetration_mm=0.02,
            additional_radial_and_axial_controls=EXTRA,
            raw_source_or_actual_AP03_parts_modified=False,
            source_sha256={
                "seated_stage.py": sha(ROOT / "seated_stage.py"),
                "mating_guards.scad": sha(ROOT / "mating_guards.scad"),
                "generated/raw-mating-surface-audit.json": sha(OUT / "raw-mating-surface-audit.json"),
                "generated/raw-mating-bolt-domain-audit.json": sha(OUT / "raw-mating-bolt-domain-audit.json"),
            },
            fixture_sha256=sha(path),
            physical_qualified=False,
            fabrication_released=False,
        ),
    )
    print(json.dumps(dict(cases=len(branches) + len(EXTRA), actual_parts_edited=False)))


if __name__ == "__main__":
    build()
