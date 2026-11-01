"""Private PTV09A-6/20 mm shaft seating and revised knob candidate.

Nominal drawing dimensions plus explicit, unaccepted receiving requirements.
This does not select an orderable suffix or approve a manufactured assembly.
"""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"
EI = ROOT.parent / "enclosure_growth/integration_repaired"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def build():
    handoff = read(EI / "handoff.json")
    assert all(sha(EI / n) == h for n, h in handoff["files_sha256"].items())
    prior = read(EI / "generated/verification.json")
    inputs = {**prior["source_sha256"], **prior["evidence_inputs_sha256"]}
    for p in [
        EI / "handoff.json",
        Path(__file__),
        ROOT.parent / "enclosure_growth/control-temperature-source.json",
    ]:
        inputs[str(p.relative_to(REPO))] = sha(p)
    text = (EI / "generated/checks.scad").read_text()
    line = next(x for x in text.splitlines() if x.startswith("ui_inherited_envelopes="))
    rows = json.loads(line.split("=", 1)[1].rstrip(";"))
    pots = [b for b in rows if b[0].endswith("_pot")]
    assert len(pots) == 10 and all(b[4:7] == [16, 16, 12.5] for b in pots)
    # Retain the inherited XY class requirement. Only its axial reserve grows.
    text = text.replace(
        line, "ui_inherited_envelopes=" + json.dumps([b for b in rows if not b[0].endswith("_pot")]) + ";"
    )
    old = "for(k=knobs)translate([k[1],k[2],shell_height+2.8])knob(k[3],k[4]);"
    assert text.count(old) == 1
    text = text.replace(old, "for(k=knobs)translate([k[1],k[2],shell_height+3.6])ps_knob(k[3],k[4]);")
    controls = ROOT.parent.parent / "a11/controls.scad"
    source = controls.read_text()
    knob = source[source.index("module knob(") : source.index("module selector_cap()")]
    assert knob.count("[0,0,6]") == 1 and knob.count("[6,0,6]") == 1
    knob = (
        knob.replace("module knob(", "module ps_knob(")
        .replace("[0,0,6]", "[0,0,3]")
        .replace("[6,0,6]", "[6,0,3]")
    )
    inputs[str(controls.relative_to(REPO))] = sha(controls)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "context-derived.scad").write_text(text)
    scad = "include <" + str(OUT / "context-derived.scad") + ">\n" + knob
    centres = [[p[1] + 8, p[2] + 8] for p in pots]
    scad += "ps_centres=" + json.dumps(centres) + ";\n"
    scad += r"""
ps_case="stack";
module ps_body(m=0){for(p=ps_centres)translate([p[0]-8-m,p[1]-8-m,27.7-.2-m])cube([16+2*m,16+2*m,43.59998-(27.7-.2-m)]);}
// Actual mounting faces are correlated at panelbottom43.6; no top Z clearance
// is applied through their own intended shoulder seat.
module ps_bushing(d=9,lo=43.6,hi=48.6){translate([0,0,lo])cylinder(d=d/cos(180/128),h=hi-lo,$fn=128);}
module ps_hardware_max(){ps_bushing(9.1,43.5,48.9);translate([0,0,45.4])difference(){cylinder(d=16,h=.9,$fn=128);cylinder(d=8.8,h=1,$fn=128);}translate([0,0,45.8])difference(){cylinder(d=11.5/cos(30),h=2.7,$fn=6);cylinder(d=8.8,h=3,$fn=128);}}
module ps_shaft_max(){hull()for(x=[-.05,.05],y=[-.05,.05])translate([x,y,48.9])cylinder(d=6/cos(180/128),h=7.1,$fn=128);}
module ps_local_knob(i=0,low=false){translate([0,0,low?49.1:49.2])ps_knob([16,17,29,32][i],[13,15,18,18][i]);}
module ps_bearing(axis=3,base=49.3){translate([1.4,-.1,base+axis-.05-1.5])cube([.2,.2,3.1]);}
module ps_exposed_shaft_band(){translate([1.3,-.2,49.15])cube([.4,.4,54.15-49.15]);}
if(ps_case=="body_geometry")ps_body();
if(ps_case=="stack"){ps_body();for(k=knobs)translate([k[1],k[2],0]){ps_hardware_max();ps_shaft_max();translate([0,0,49.2])ps_knob(k[3],k[4]);}}
if(ps_case=="body_other_electronics_collision")intersection(){ps_body(.25);ui_electronics();}
if(ps_case=="body_controls_collision")intersection(){ps_body(.25);ui_controls();}
if(ps_case=="body_case_collision")intersection(){ps_body(.25);ui_case_and_lid();}
if(ps_case=="body_power_wire_collision")intersection(){ps_body(.25);union(){ui_power_only();pf_wires(.25);ui_all_joints(.25);ui_h9_head();tc2_posts();tc2_heads();}}
if(ps_case=="new_knobs_environment_collision")for(k=knobs)intersection(){translate([k[1],k[2],49.1])ps_knob(k[3],k[4]);union(){ui_electronics();ui_power_only();ui_case_and_lid();ps_body();}}
if(ps_case=="old_bushing_knob_blocked_witness")intersection(){ps_bushing();translate([0,0,48.4])knob(16,13);}
if(ps_case=="old_bearing_outside_shaft_witness")difference(){ps_bearing(6,48.4);ps_exposed_shaft_band();}
if(ps_case=="new_bearing_axial_collision")difference(){ps_bearing();ps_exposed_shaft_band();}
if(ps_case=="body_positive_control")intersection(){ps_body();translate([17.9,26.9,30])cube([.2,.2,.2]);}
if(ps_case=="hardware_positive_control")intersection(){ps_hardware_max();translate([3.9,-.1,47])cube([.2,.2,.2]);}
if(ps_case=="bearing_positive_control")intersection(){ps_bearing();translate([1.4,-.1,52])cube([.2,.2,.2]);}
for(i=[0:3]){
 if(ps_case==str("knob_",i))ps_local_knob(i);
 if(ps_case==str("shaft_knob_",i,"_collision"))intersection(){ps_shaft_max();ps_local_knob(i,true);}
 if(ps_case==str("hardware_knob_",i,"_collision"))intersection(){ps_hardware_max();ps_local_knob(i,true);}
}
"""
    (OUT / "checks.scad").write_text(scad)
    record = dict(
        scope=__doc__,
        source_sha256=inputs,
        manufacturer_drawing=read(ROOT.parent / "enclosure_growth/control-temperature-source.json"),
        drawing_dimensions_mm=dict(
            body_datum_to_shoulder=8.4,
            nominal_thread_length=5,
            shaft_length=20,
            shaft_length_tolerance=0.5,
            terminal_projection_max=7.3,
            nut_thickness_max=2.2,
            washer_nominal_thickness=0.4,
        ),
        unaccepted_receiving_allocations_mm=dict(
            body_datum_uncertainty=0.2,
            seat_z=0.1,
            thread_length_uncertainty=0.2,
            washer_max_thickness=0.5,
            panel_max_thickness=2.1,
            knob_base_z=0.1,
            bearing_axis_z=0.05,
            bushing_max_diameter=9.1,
            independent_shaft_xy_each=0.05,
        ),
        body_datum_metric_inch_inconsistency="Drawing labels8.4mm/.315in; declared mm used with separate unaccepted0.2mm allocation, not a supplier tolerance.",
        nominal_panel_bottom_z_mm=43.6,
        nominal_panel_top_z_mm=45.6,
        old_knob_base_mm=48.4,
        new_knob_base_mm=49.2,
        new_knob_base_requirement_mm=[49.1, 49.3],
        old_bearing_axis_local_mm=6,
        new_bearing_axis_local_mm=3,
        worst_allocated_shaft_tip_z_mm=[54.4, 56.0],
        worst_allocated_bushing_top_z_mm=48.9,
        required_axial_bearing_reserve_mm=0.25,
        minimum_allocated_reserve_beyond_that_mm=0.3,
        nominal_screw="Inherited nominalM3x4 grub; thread material/engagement/torque/retention unapproved",
        proposed_family_not_selected_suffix="PTV09A-6 /20mm Fshaft; resistance/taper/exactorderablepart not approved",
        actual_knob_supports_or_anti_rotation_designed=False,
        potentiometer_thermal_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    assert math.isclose(54.4 - (49.3 + 3 + 0.05 + 1.5 + 0.25), 0.3, abs_tol=1e-10)
    (OUT / "analysis.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def verify(executable):
    a = read(OUT / "analysis.json")
    source = dict(a["source_sha256"])
    for p in [OUT / "analysis.json", OUT / "checks.scad", OUT / "context-derived.scad"]:
        source[str(p.relative_to(REPO))] = sha(p)
    names = ["body_geometry", "stack"] + [f"knob_{i}" for i in range(4)]
    names += [
        "body_other_electronics_collision",
        "body_controls_collision",
        "body_case_collision",
        "body_power_wire_collision",
        "new_knobs_environment_collision",
        "new_bearing_axial_collision",
    ]
    names += [f"{kind}_knob_{i}_collision" for kind in ["shaft", "hardware"] for i in range(4)]
    names += [
        "old_bushing_knob_blocked_witness",
        "old_bearing_outside_shaft_witness",
        "body_positive_control",
        "hardware_positive_control",
        "bearing_positive_control",
    ]
    v = read(EI / "generated/verification.json")
    command = v["cases"]["whole_geometry"]["command"]
    # Reuse exactly the bound complete-scene CLI overrides, replacing only
    # the case/output/entrypoint; inherited top-level outputs remain disabled.
    base = command[: command.index("-o")]
    j = base.index('ui_case="whole_geometry"')
    base[j] = 'ui_case="pot_stack_only"'
    base[0] = str(executable)
    cases = {}
    for name in names:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = base + ["-D", "ps_case=" + json.dumps(name), "-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(x in log for x in ["WARNING", "ERROR"])
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        stats = binary_stl(target) if p.returncode == 0 and target.exists() else None
        expected_empty = name.endswith("collision")
        ok = clean and (
            empty if expected_empty else stats and "NoError" in log and stats["volume_mm3"] > 0.001
        )
        if name.endswith("positive_control"):
            ok = bool(ok and math.isclose(stats["volume_mm3"], 0.008, abs_tol=2e-6))
        cases[name] = dict(
            clear=bool(ok),
            expected_empty=expected_empty,
            empty=empty,
            returncode=p.returncode,
            command=cmd,
            statistics=stats,
        )
        print(name, bool(ok), stats and stats["volume_mm3"], flush=True)
    changed = [n for n, h in source.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        source_sha256=source,
        cases=cases,
        changed_inputs=changed,
        conditional_checks_clear=not changed and all(x["clear"] for x in cases.values()),
        physical_qualified=False,
        fabrication_released=False,
        artifact_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    build()
    raise SystemExit(0 if verify(args.openscad)["conditional_checks_clear"] else 1)
