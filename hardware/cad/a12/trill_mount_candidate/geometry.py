"""Nominal insulating saddle local-fit screens, not selected hardware proof."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
CASES = {
    "saddle": "solid",
    "board": "solid",
    "hardware_requirements": "solid",
    "saddle_board": "empty",
    "saddle_components": "empty",
    "saddle_tails": "empty",
    "saddle_backer": "empty",
    "heads_components": "empty",
    "heads_backer": "empty",
    "central_aperture": "empty",
    "known_board_collision": "control",
    "known_head_collision": "control",
    "backer_contact": "contact",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def generate():
    r = json.loads((ROOT / "report.json").read_text())
    OUT.mkdir(exist_ok=True)
    p = ROOT / "sources/hardware/cad/a11/controls.scad"
    s = "use <" + str(p) + '>\n$fn=64;panel_z=43.6;candidate_case="saddle";\n'
    s += "mounts=" + json.dumps([m["world_xy_mm"] for m in r["mounts"]]) + ";\n"
    s += "bodies=" + json.dumps([m["box_mm"] for m in r["component_terminal_reserves"]]) + ";\n"
    s += "tails=" + json.dumps([t["xy_mm"] for t in r["tail_reserves"]]) + ";\n"
    s += """
module corners(){for(x=[73,143],y=[123,145])translate([x,y,0])children();}
module saddle(){difference(){union(){
 // Outer lower rails and crossbeam stay beneath the declared3mm solder tails.
 for(y=[123,145])translate([70.1,y-2.9,24.6])cube([75.8,5.8,1.6]);
 for(x=[73,143])translate([x-2.9,120.1,24.6])cube([5.8,27.8,1.6]);
 translate([73,131.4,24.6])cube([70,6,1.6]);
 for(m=mounts)translate([m[0],m[1],26.2])cylinder(d=5.4,h=4.4);
 corners()translate([0,0,26.2])cylinder(d=5.8,h=16);
 }for(m=mounts)translate([m[0],m[1],24.5])cylinder(d=3.4,h=6.2);
 // UnselectedM2-class corner interface: no thread or material strength credit.
 corners()translate([0,0,26.3])cylinder(d=2.2,h=16);
}}
module board(){difference(){translate([82,123.5,30.6])cube([53.848,21.844,1.6]);
 for(m=mounts)translate([m[0],m[1],30.5])cylinder(d=3.2,h=1.8);
}}
module components(){for(b=bodies)translate([b[0],b[1],b[2]])cube([b[3],b[4],b[5]]);}
module tails(){for(p=tails)translate([p[0],p[1],27.6])cylinder(r=.8,h=3);}
module hardware(){for(m=mounts){
 translate([m[0],m[1],32.2])cylinder(d=6.4,h=3.2);
 translate([m[0],m[1],24.6])cylinder(d=3,h=7.6);
}}
module aperture(){translate([75.5,126.5,42.1])cube([65,15,4]);}
if(candidate_case=="saddle")saddle();
if(candidate_case=="board")board();
if(candidate_case=="hardware_requirements")hardware();
if(candidate_case=="saddle_board")intersection(){translate([0,0,-.00002])saddle();board();}
if(candidate_case=="saddle_components")intersection(){saddle();components();}
if(candidate_case=="saddle_tails")intersection(){saddle();tails();}
if(candidate_case=="saddle_backer")intersection(){translate([0,0,-.00002])saddle();touch_backer();}
if(candidate_case=="heads_components")intersection(){hardware();components();}
if(candidate_case=="heads_backer")intersection(){hardware();touch_backer();}
if(candidate_case=="central_aperture")intersection(){saddle();aperture();}
if(candidate_case=="known_board_collision")intersection(){board();translate([100,130,31])cube([.2,.2,.2]);}
if(candidate_case=="known_head_collision")intersection(){hardware();translate([130,134.4,34])cube([.2,.2,.2]);}
if(candidate_case=="backer_contact")intersection(){translate([0,0,.01])saddle();touch_backer();}
"""
    (OUT / "checks.scad").write_text(s)
    binding = {
        str(q.relative_to(ROOT)): sha(q)
        for q in [ROOT / "report.json", Path(__file__), p, OUT / "checks.scad"]
    }
    (OUT / "input-hashes.json").write_text(json.dumps(binding, indent=2) + "\n")
    return binding


def verify(executable):
    hashes = generate()
    rows = {}
    for name, role in CASES.items():
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [
            str(executable),
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            "panel_z=43.6",
            "-D",
            "candidate_case=" + json.dumps(name),
            "-o",
            str(target),
            str(OUT / "checks.scad"),
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        clean = not any(s in log for s in ["WARNING", "ERROR"])
        stats = binary_stl(target) if p.returncode == 0 and target.exists() else None
        clear = clean and (
            (role == "empty" and empty)
            or (role == "solid" and stats and stats["volume_mm3"] > 0.01)
            or (role == "control" and stats and abs(stats["volume_mm3"] - 0.008) < 1e-6)
            or (role == "contact" and stats and stats["volume_mm3"] > 0.1)
        )
        rows[name] = dict(
            role=role, clear=bool(clear), returncode=p.returncode, empty=empty, statistics=stats, command=cmd
        )
        print(name, rows[name]["clear"], flush=True)
    changed = [name for name, h in hashes.items() if sha(ROOT / name) != h]
    result = dict(
        cases=rows,
        changed_inputs=changed,
        source_sha256=hashes,
        all_local_checks_clear=all(r["clear"] for r in rows.values()) and not changed,
        physical_qualified=False,
        fabrication_released=False,
    )
    result["artifact_sha256"] = {
        str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.iterdir()) if p.suffix in [".stl", ".log"]
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True)
    a = parser.parse_args()
    raise SystemExit(not verify(a.openscad)["all_local_checks_clear"])
