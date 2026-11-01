"""Native fit of the actual separate E19 receiver PCB and conservative joint reserve.

The original 11.31 mm header/service height and 3.15 mm tail reserve are retained
as conservative local space requirements. This does not select a header or
qualify the complete receiving wire bend, termination or strain relief.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.netlists import netlist
from hardware.electronics.processor_carrier.check_board import mechanical

from ..generate import REPO, sha
from .receiver_review import check

ROOT = Path(__file__).resolve().parent
CASES = [
    "geometry",
    "case_collision",
    "electronics_collision",
    "hardware_collision",
    "source_PCB_geometry",
    "source_wirefit_collision",
    "wirefit_geometry",
    "joint_positive_control",
    "source_PCB_positive_control",
    "bare_positive_control",
    "insulated_positive_control",
]


def generate(workspace, out):
    proof = check(workspace)
    _, pins = netlist(workspace / "generated/netlist.xml")
    filled = workspace / "generated/filled.kicad_pcb"
    actual = mechanical(filled, pins)
    native, other, hashes = snapshot()
    hashes.update(proof["source_sha256"])
    for p in [
        Path(__file__),
        ROOT / "receiver_review.py",
        workspace / "generated/independent-review.json",
        REPO / "hardware/electronics/processor_carrier/check_board.py",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    bodies = actual["bodies"]
    joints = [b for b in bodies if b[0] == "e19_J1" or b[0].startswith("e19_J1_lead_")]
    assert len(joints) == 3 and next(b for b in joints if b[0] == "e19_J1")[6] == 11.31
    boxes = native["boxes"] + native["switch_diagnostic_boxes"] + [b for b in bodies if b not in joints]
    boxes += [b for b in other["envelopes"] if not b[0].startswith(("e19_", "disconnect_"))]
    boxes += other["port_envelopes"]
    expected = sum(math.prod(b[4:7]) for b in joints)
    out.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(ROOT.parent / "thermal-integration.scad") + '>\ntrial="geometry";\n'
    for key, value in dict(
        joints=joints,
        boxes=boxes,
        cylinders=native["cylinders"],
        pads=[p["world_mm"] for p in proof["actual_pads"]],
    ).items():
        scad += key + "=" + json.dumps(value) + ";\n"
    scad += """module receiver(m=0){for(b=joints)translate([b[1]-m,b[2]-m,b[3]-m])cube([b[4]+2*m,b[5]+2*m,b[6]+2*m]);}
module electronics(){for(b=boxes)translate([b[1],b[2],b[3]-.2])cube([b[4],b[5],b[6]+.4]);for(c=cylinders)translate([c[1],c[2],c[3]-.2])cylinder(d=c[4]/cos(180/128),h=c[5]+.4,$fn=128);
"""
    for b in native["boards"]:
        scad += (
            "translate("
            + json.dumps([*b["datum"][:2], b["datum"][2] - 0.2])
            + ")linear_extrude("
            + str(b["thickness_range_allocation_mm"][1] + 0.4)
            + ")polygon("
            + json.dumps(b["outline_relative_mm"])
            + ");\n"
        )
    for b in other["boards"]:
        if b[0] not in ("dsp_carrier", "disconnect_carrier"):
            scad += "board_reserve(" + json.dumps(b) + ");\n"
    scad += (
        """}
module hardware(){return_assembly();import("""
        + json.dumps(str(ROOT.parent / "positive_links/generated/positive-links.stl"))
        + """);}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
// Common-frame source board includes all its material except the two actual
// minimum finished J1 bores. Other holes are conservatively left as material.
module source_PCB(){difference(){translate([30,42,6.3])cube([150,65,2]);for(p=pads)translate([p[0],p[1],6.29])cylinder(d=2.1,h=2.02,$fn=64);}}
// 1.4 mm pretinned OD, .3 mm relative centering and .005 mm geometry reserve.
// Insulation ODmax1.7526, same centering, flat cut Z11.2 with +/-.305 reserve.
module relative_wire(){for(p=pads){translate([p[0],p[1],5])cylinder(r=1.005/cos(180/64),h=6.505,$fn=64);translate([p[0],p[1],10.895])cylinder(r=1.1813/cos(180/64),h=3.305,$fn=64);}}
if(trial=="geometry")receiver();
if(trial=="case_collision")intersection(){receiver(.45);case_parts();}
if(trial=="electronics_collision")intersection(){receiver(.45);electronics();}
if(trial=="hardware_collision")intersection(){receiver(.45);hardware();}
if(trial=="source_PCB_geometry")source_PCB();
if(trial=="source_wirefit_collision")intersection(){relative_wire();source_PCB();}
if(trial=="wirefit_geometry")relative_wire();
if(trial=="joint_positive_control")intersection(){receiver();translate([43.9,46.9,8.5])cube([.2,.2,.2]);}
if(trial=="source_PCB_positive_control")intersection(){source_PCB();translate([54.9,44.9,7])cube([.2,.2,.2]);}
if(trial=="bare_positive_control")intersection(){relative_wire();translate([43.9,46.9,9])cube([.2,.2,.2]);}
if(trial=="insulated_positive_control")intersection(){relative_wire();translate([43.9,46.9,12.5])cube([.2,.2,.2]);}
"""
    )
    (out / "checks.scad").write_text(scad)
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    result = dict(
        scope=__doc__,
        source_sha256=hashes,
        candidate_pcb_sha256=proof["candidate_pcb_sha256"],
        filled_native_pcb_sha256=sha(filled),
        receiver_joints=joints,
        expected_joint_reserve_volume_mm3=expected,
        joint_XYZ_position_allocation_mm=0.2,
        clearance_mm=0.25,
        current_E19_component_packet=actual,
        conservative_switch_body_and_lead_boxes_included=True,
        own_PCB_excluded_only_from_external_joint_comparison=True,
        source_common_frame_minimum_bore_test_required=True,
        wire_bend_complete=False,
        current_path_resistance_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify(executable, out):
    report = json.loads((out / "analysis.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [out / "analysis.json", out / "checks.scad"]}
    cases = {}
    (out / "verification.json").unlink(missing_ok=True)
    for name in CASES:
        target = out / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="receiver_only"']
        cmd += ["-D", 'trial="' + name + '"', "-o", str(target), str(out / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (out / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        clean = not any(s in log for s in ["WARNING", "ERROR"])
        if name.endswith("collision") and empty and clean:
            row = dict(clear=True, empty=True)
        elif p.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            good = not name.endswith("collision") and stats["volume_mm3"] > 0.001
            if name == "geometry":
                good = math.isclose(
                    stats["volume_mm3"], report["expected_joint_reserve_volume_mm3"], abs_tol=0.01
                )
            if name.endswith("positive_control"):
                good = math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            row = dict(clear=good, **stats)
        else:
            row = dict(clear=False, returncode=p.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in out.iterdir() if p.suffix in (".log", ".stl")
        },
        all_checked_receiver_intersections_clear=not changed and all(c["clear"] for c in cases.values()),
        wire_bend_complete=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--openscad", required=True, type=Path)
    args = parser.parse_args()
    out = ROOT / "generated/receiver-awg18"
    generate(args.workspace.resolve(), out)
    raise SystemExit(0 if verify(args.openscad, out)["all_checked_receiver_intersections_clear"] else 1)
