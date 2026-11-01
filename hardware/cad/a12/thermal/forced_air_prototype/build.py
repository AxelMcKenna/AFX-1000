"""Under-base dual-fan tray prototype; no installed-flow or cooling proof.

This is an independent receiving/space study of the H20 declared pin field.
It does not replace or inherit a full enlarged-base assembly qualification.
"""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def build():
    plan = read(ROOT / "space-plan.json")
    pin_file = ROOT.parent.parent / "housing20percent/generated/thermal.json"
    pin_data = read(pin_file)
    pins = pin_data["pin_centres_extended_proposal_mm"]
    assert len(pins) == 1037
    feet = plan["foot_centres_xy_mm"]
    fans = plan["fan_centres_xy_mm"]

    def remove(x, y):
        half = plan["fan_pin_removal_region_width_mm"] / 2
        fan = any(abs(x - a) <= half + 1.5 and abs(y - b) <= half + 1.5 for a, b in fans)
        foot = any(
            math.hypot(max(abs(x - a) - 1.5, 0), max(abs(y - b) - 1.5, 0))
            <= plan["foot_pin_removal_radius_mm"]
            for a, b in feet
        )
        return fan or foot

    removed = [p for p in pins if remove(*p)]
    kept = [p for p in pins if not remove(*p)]
    OUT.mkdir(exist_ok=True)
    data = dict(fa_fans=fans, fa_feet=feet, fa_pins=pins, fa_kept=kept)
    scene = "\n".join(k + "=" + json.dumps(v) + ";" for k, v in data.items()) + "\n"
    scene += r"""
$fn=96;
fa_case="assembly";
module fa_round(w,d,r){hull()for(x=[r,w-r],y=[r,d-r])translate([x,y])circle(r=r);}
module fa_tray(){difference(){union(){
 translate([0,0,-26.2])linear_extrude(1.5)fa_round(334,188.4,7);
 translate([0,0,-24.7])linear_extrude(18.5)difference(){fa_round(334,188.4,7);translate([2,2])fa_round(330,184.4,5);}
 for(p=fa_feet)translate([p[0],p[1],-24.7])difference(){cylinder(d=24,h=16.5);translate([0,0,-.01])cylinder(d=20.5,h=16.52);}
 for(p=fa_feet)translate([p[0],p[1],-8.2])cylinder(d=26,h=2);
 }
 for(p=fa_feet){translate([p[0],p[1],-26.21])cylinder(d=20.5,h=18.01);translate([p[0],p[1],-8.21])cylinder(d=3.4,h=2.02);}
 for(p=fa_fans){translate([p[0],p[1],-26.21])cylinder(d=37.5,h=1.52);for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-26.21])cylinder(d=4.4,h=1.52);}
 translate([34,-.01,-22.2])cube([266,2.02,14]);
}}
module fa_guard(){difference(){translate([-22,-22,-27.7])linear_extrude(1)fa_round(44,44,3);
 for(x=[-16,16],y=[-16,16])translate([x,y,-27.71])cylinder(d=4.4,h=1.02);
 for(j=[-4:4],i=[-4:4])let(x=5.2*(i+(j%2)/2),y=j*5.2*sqrt(3)/2)if(x*x+y*y<16.65*16.65)translate([x,y,-27.71])cylinder(d=4.2,h=1.02,$fn=48);
}}
module fa_guards(){for(p=fa_fans)translate([p[0],p[1],0])fa_guard();}
module fa_spacers(){for(p=fa_feet)translate([p[0],p[1],-14.2])difference(){cylinder(d=18,h=6);translate([0,0,-.01])cylinder(d=3.4,h=6.02);}}
module fa_fan(){difference(){translate([-20.25,-20.25,-24.7])cube([40.5,40.5,12.5]);for(x=[-16,16],y=[-16,16])translate([x,y,-24.71])cylinder(d=4.2,h=12.52);}}
module fa_fan_receiving(m=.25){translate([-20.25-m,-20.25-m,-24.7])cube([40.5+2*m,40.5+2*m,12.5]);}
module fa_fans(){for(p=fa_fans)translate([p[0],p[1],0])fa_fan();}
module fa_pinfield(rows){for(p=rows)translate([p[0]-1.5,p[1]-1.5,-18.2])cube([3,3,12]);}
module fa_foot_receiving(){for(p=fa_feet)hull()for(x=[-.2,.2],y=[-.2,.2])translate([p[0]+x,p[1]+y,-37.3])cylinder(d=18.6/cos(180/128),h=23.1,$fn=128);}
// Proposed M3x20 under-head gauge; actual bolt/nut/material approvals open.
module fa_bolt(){translate([0,0,-27.7])cylinder(d=3.1,h=20);translate([0,0,-30.7])cylinder(d=6,h=3);}
module fa_fasteners(){for(p=fa_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,0]){
 fa_bolt();translate([0,0,-26.7])difference(){cylinder(d=7.4,h=.5);cylinder(d=3.4,h=.51);}
 translate([0,0,-12.2])difference(){cylinder(d=7.4,h=.5);cylinder(d=3.4,h=.51);}
 translate([0,0,-11.7])difference(){cylinder(d=6.8,h=2.6,$fn=6);cylinder(d=3.12,h=2.61);}
}}
module fa_shank_sweep(m=.3){for(x=[-16,16],y=[-16,16])hull()for(dx=[-m,m],dy=[-m,m])translate([x+dx,y+dy,-24.69])cylinder(d=3.1/cos(180/128),h=12.48,$fn=128);}
if(fa_case=="tray_geometry")fa_tray();
if(fa_case=="guard_geometry")fa_guards();
if(fa_case=="spacer_geometry")fa_spacers();
if(fa_case=="fan_gauge_geometry")fa_fans();
if(fa_case=="fastener_gauge_geometry")fa_fasteners();
if(fa_case=="assembly"){fa_tray();fa_guards();fa_spacers();fa_fans();fa_fasteners();fa_pinfield(fa_kept);}
if(fa_case=="fan_tray_collision")for(p=fa_fans)intersection(){translate([p[0],p[1],.00002])fa_fan_receiving(.3);fa_tray();}
if(fa_case=="fan_guard_collision")intersection(){fa_fans();fa_guards();}
if(fa_case=="fan_spacer_collision")intersection(){fa_fans();fa_spacers();}
if(fa_case=="remaining_pin_fan_collision")for(p=fa_fans)intersection(){translate([p[0],p[1],0])fa_fan_receiving(.3);fa_pinfield(fa_kept);}
if(fa_case=="remaining_pin_tray_collision")intersection(){fa_pinfield(fa_kept);translate([0,0,-.00002])fa_tray();}
if(fa_case=="remaining_pin_hardware_collision")intersection(){fa_pinfield(fa_kept);for(p=fa_fans)for(x=[-16,16],y=[-16,16])translate([p[0]+x,p[1]+y,-30.70002])cylinder(r=(3.7+sqrt(2)*.275+.005)/cos(180/128),h=23.10004,$fn=128);}
if(fa_case=="foot_tray_collision")intersection(){fa_foot_receiving();fa_tray();}
if(fa_case=="spacer_tray_collision")intersection(){translate([0,0,-.00002])fa_spacers();fa_tray();}
if(fa_case=="guard_tray_collision")intersection(){fa_guards();fa_tray();}
// e=fan_global(.30)+pitch_half(.15)+tray_local(.10)=.55 peraxis.
// A single bolt is placed at midpoint(A,B): in either actual hole frame,
// its displacement is bounded by e/2=.275. This is the SAME straight axis.
if(fa_case=="floating_fan_hole_collision")intersection(){fa_shank_sweep(.275);fa_fan();}
if(fa_case=="floating_tray_hole_collision")intersection(){fa_shank_sweep(.275);translate([-21,-21,-24.7])difference(){cube([42,42,12.5]);for(x=[5,37],y=[5,37])translate([x,y,-.01])cylinder(d=4.4,h=12.52);}}
if(fa_case=="fixed_axis_rejected_witness")intersection(){fa_shank_sweep(.5);fa_fan();}
if(fa_case=="rear_exit_collision")intersection(){translate([35,-.02,-21.9])cube([264,2.04,13.4]);fa_tray();}
if(fa_case=="old_pins_blocked_witness")for(p=fa_fans)intersection(){translate([p[0],p[1],0])fa_fan_receiving();fa_pinfield(fa_pins);}
if(fa_case=="tray_positive_control")intersection(){fa_tray();translate([166.9,99.9,-26])cube([.2,.2,.2]);}
if(fa_case=="fan_positive_control")intersection(){fa_fans();translate([79.9,165.4,-20])cube([.2,.2,.2]);}
if(fa_case=="spacer_positive_control")intersection(){fa_spacers();translate([24,19.9,-10])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scene)
    sources = [
        Path(__file__),
        ROOT / "space-plan.json",
        ROOT / "fan-source.json",
        pin_file,
        ROOT.parent.parent / "pot_stack/handoff.json",
        ROOT.parent / "coupled_housing20/sources/base-design.json",
    ]
    relative = (
        plan["stress_fan_registration_each_XY_mm"]
        + plan["fan_hole_pitch_half_tolerance_each_XY_mm"]
        + plan["tray_hole_centre_allocation_each_XY_mm"]
    )
    assert math.isclose(relative, 0.55)
    radial = (
        plan["max_bolt_shank_receiving_diameter_mm"] / (2 * math.cos(math.pi / 128))
        + math.sqrt(2) * relative / 2
    )
    fan_clearance = 2.1 * math.cos(math.pi / 96) - radial
    tray_clearance = 2.2 * math.cos(math.pi / 96) - radial
    assert fan_clearance > 0.15 and tray_clearance > 0.25
    record = dict(
        scope=__doc__,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        original_pins=1037,
        removed_whole_pins=len(removed),
        remaining_whole_pins=len(kept),
        removed_pin_centres_mm=removed,
        plan=plan,
        shared_axis_construction=dict(
            maximum_relative_hole_offset_each_XY_mm=relative,
            common_axis_relative_to_each_actual_hole_each_XY_mm=relative / 2,
            common_axis_is_midpoint_of_the_same_two_holes=True,
            native_fan_radial_clearance_lower_mm=fan_clearance,
            native_tray_radial_clearance_lower_mm=tray_clearance,
            assembly_preload_friction_thread_or_material_qualified=False,
        ),
        exact_fan_or_foot_stack_qualified=False,
        current_enlarged_base_solid_integrated=False,
        rotor_or_airflow_performance_simulated=False,
        installed_flow_or_h_established=False,
        thermal_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def verify(executable):
    a = read(OUT / "analysis.json")
    source = dict(a["source_sha256"])
    for p in [OUT / "analysis.json", OUT / "checks.scad"]:
        source[str(p.relative_to(REPO))] = sha(p)
    names = [
        "tray_geometry",
        "guard_geometry",
        "spacer_geometry",
        "fan_gauge_geometry",
        "fastener_gauge_geometry",
        "assembly",
        "fan_tray_collision",
        "fan_guard_collision",
        "fan_spacer_collision",
        "remaining_pin_fan_collision",
        "remaining_pin_tray_collision",
        "remaining_pin_hardware_collision",
        "foot_tray_collision",
        "spacer_tray_collision",
        "guard_tray_collision",
        "floating_fan_hole_collision",
        "floating_tray_hole_collision",
        "fixed_axis_rejected_witness",
        "rear_exit_collision",
        "old_pins_blocked_witness",
        "tray_positive_control",
        "fan_positive_control",
        "spacer_positive_control",
    ]
    cases = {}
    for name in names:
        path = OUT / (name + ".stl")
        path.unlink(missing_ok=True)
        command = [
            str(executable),
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            "fa_case=" + json.dumps(name),
            "-o",
            str(path),
            str(OUT / "checks.scad"),
        ]
        p = subprocess.run(command, capture_output=True, text=True, timeout=300)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not path.exists()
        stats = binary_stl(path) if p.returncode == 0 and path.exists() else None
        clean = not any(x in log for x in ["WARNING", "ERROR"])
        ok = clean and (
            empty
            if name.endswith("collision")
            else stats and "NoError" in log and stats["volume_mm3"] > 0.001
        )
        if name.endswith("positive_control"):
            ok = bool(ok and math.isclose(stats["volume_mm3"], 0.008, abs_tol=2e-6))
        cases[name] = dict(
            clear=bool(ok), empty=empty, returncode=p.returncode, statistics=stats, command=command
        )
        print(name, bool(ok), stats and stats["volume_mm3"], flush=True)
    changed = [n for n, h in source.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        source_sha256=source,
        cases=cases,
        changed_inputs=changed,
        prototype_space_checks_clear=not changed and all(x["clear"] for x in cases.values()),
        actual_enlarged_base_integrated=False,
        physical_qualified=False,
        thermal_qualified=False,
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
    raise SystemExit(0 if verify(args.openscad)["prototype_space_checks_clear"] else 1)
