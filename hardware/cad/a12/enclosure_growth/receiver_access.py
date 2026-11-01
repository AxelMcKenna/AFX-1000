"""Actual wide-ear PCB, relocated post and open-lid tool-access candidate.

The native test uses the unchanged power-link assembly, retains the old blocked
axis as a witness, and checks both retained and raised component reserves.
No exact driver/insert/fastener, structural load or physical process is approved.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.harness.receiver_review import footprints
from hardware.cad.a12.harness.receiver_support_fit import surface_components
from hardware.cad.a12.repaired import outline
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from .generate import FASTENERS

ROOT = Path(__file__).resolve().parent
HARNESS = ROOT.parent / "harness"
BOARD = HARNESS / "proposals/processor-awg18-ear-wide-access"
OUT = ROOT / "receiver-access"


def generate():
    hashes = {}
    prior_path = HARNESS / "generated/receiver-ear/verification.json"
    prior = json.loads(prior_path.read_text())
    assert prior["all_local_ear_checks_clear"] and not prior["changed_inputs"]
    for key in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
        hashes.update(prior[key])
    pcb = BOARD / "processor_carrier.kicad_pcb"
    native_path = BOARD / "generated/native.json"
    native = json.loads(native_path.read_text())
    assert native["candidate_pcb_sha256"] == sha(pcb) and not any(native["counts"].values())
    for key in ["source_sha256", "artifact_sha256"]:
        hashes.update(native[key])
    drc = json.loads((BOARD / "generated/drc.json").read_text())
    erc = json.loads((BOARD / "generated/erc.json").read_text())
    assert all(not drc[k] for k in ["violations", "unconnected_items", "schematic_parity"])
    assert erc["sheets"] and all(not s["violations"] for s in erc["sheets"])
    tree = read_sexpr(pcb.read_text())
    fps = footprints(tree)
    original = HARNESS / "proposals/processor-awg18-ear-supported/processor_carrier.kicad_pcb"
    old = footprints(read_sexpr(original.read_text()))
    assert set(old) == set(fps) and len(fps) == 86
    assert all(old[k] == f for k, f in fps.items() if k != "H9")
    h9 = fps["H9"]
    assert list(map(float, first(h9, "at")[1:])) == [252, 150.2]
    hp = children(h9, "pad")
    assert len(hp) == 1 and hp[0][2] == "np_thru_hole" and float(first(hp[0], "drill")[1]) == 2.4
    j13 = []
    for p in children(fps["J13"], "pad"):
        x, y = transform(fps["J13"], first(p, "at")[1:3])
        point = [x - 70, y - 58, 8.1]
        assert point == ([188, 100, 8.1] if str(p[1]) == "1" else [188, 104, 8.1])
        j13.append(point)
    shape = outline(tree)
    assert set(map(tuple, shape)) == {(0, 0), (150, 0), (150, 48), (164, 48), (164, 65), (0, 65)}
    for p in [
        Path(__file__),
        Path(__file__).with_name("generate.py"),
        prior_path,
        native_path,
        pcb,
        original,
        HARNESS / "generated/receiver-ear/checks.scad",
        HARNESS / "receiver_support_fit.py",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Stale access-fit source"
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(HARNESS / "generated/receiver-ear/checks.scad") + ">\n"
    scad += "access_outline=" + json.dumps(shape) + ";\n"
    scad += "access_J13=" + json.dumps(j13) + ";\n"
    scad += """
module ax_post(m=0){difference(){translate([182,92.2,2.7-m])cylinder(d=7.2+2*m,h=3.8+2*m,$fn=128);translate([182,92.2,3.2])cylinder(d=3.2,h=3.31+m,$fn=128);}}
module ax_head(m=0){translate([182,92.2,8.1-m])cylinder(d=5.6+2*m,h=2.31+2*m,$fn=128);}
module ax_shaft(){translate([182,92.2,4.1])cylinder(d=2.05,h=4,$fn=128);}
module ax_tool(old=false){translate([182,old?97.2:92.2,8.1])cylinder(d=6.5,h=52,$fn=128);}
module ax_ear(){difference(){translate([30,42,6.5])linear_extrude(1.6)polygon(access_outline);translate([29,41,6.49])cube([151,67,1.62]);for(p=access_J13)translate([p[0],p[1],6.49])cylinder(d=2.2,h=1.62,$fn=128);translate([182,92.2,6.49])cylinder(d=2.4,h=1.62,$fn=128);}}
module ax_ear_reserve(){translate([179.55,89.55,6.05])cube([14.9,17.9,2.5]);}
module ax_seats(){guarded_inherited_support();translate([182,92.2,2.79998])cylinder(d=7.20004,h=3.70004,$fn=128);}
module ax_nonseating_ear(){difference(){ax_ear_reserve();ax_seats();}}
module ax_open_case(){retained_thermal_shell();thermal_metal_base();lower_shell_fasteners();ax_post();}
module ax_dual_component_reserves(){electronics();translate([0,0,7.6])electronics();}
module ax_relative_board(){translate([30,42,6.3])difference(){linear_extrude(2.16)polygon(access_outline);translate([152,50.2,-.01])cylinder(d=2.3,h=2.18,$fn=128);}}
if(trial=="access_geometry"){ax_ear();ax_post();ax_head();ax_shaft();joint();}
if(trial=="access_tool_geometry")ax_tool();
if(trial=="access_ear_material")ax_ear();
if(trial=="access_nominal_ear_case_collision")intersection(){translate([0,0,.00002])ax_ear();ax_open_case();}
if(trial=="access_ear_case_collision")intersection(){ax_nonseating_ear();ax_open_case();}
if(trial=="access_ear_hardware_collision")intersection(){union(){ax_ear_reserve();joint(.45);}hardware();}
if(trial=="access_ear_electronics_collision")intersection(){union(){ax_ear_reserve();joint(.45);}ax_dual_component_reserves();}
if(trial=="access_post_joint_collision")intersection(){union(){ax_post(.45);ax_head(.45);}joint();}
if(trial=="access_post_electronics_collision")intersection(){union(){ax_post(.45);ax_head(.45);}ax_dual_component_reserves();}
if(trial=="access_post_hardware_collision")intersection(){union(){ax_post(.45);ax_head(.45);}hardware();}
if(trial=="access_tool_hardware_collision")intersection(){ax_tool();hardware();}
if(trial=="access_tool_electronics_collision")intersection(){ax_tool();ax_dual_component_reserves();}
if(trial=="access_tool_open_case_collision")intersection(){ax_tool();ax_open_case();}
if(trial=="access_shaft_bore_collision")intersection(){translate([182,92.2,4.1])cylinder(d=2.26,h=7,$fn=128);ax_relative_board();}
if(trial=="access_floor_bond")intersection(){ax_post();retained_thermal_shell();}
if(trial=="access_old_axis_blocked_witness")intersection(){ax_tool(true);hardware();}
if(trial=="access_post_positive_control")intersection(){ax_post();translate([184.9,92.1,4])cube([.2,.2,.2]);}
if(trial=="access_ear_positive_control")intersection(){ax_ear();translate([189.9,91.9,7])cube([.2,.2,.2]);}
if(trial=="access_tool_positive_control")intersection(){ax_tool();translate([181.9,92.1,30])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        source_PCB_sha256=sha(pcb),
        all85_other_complete_footprints_unchanged=True,
        H9_world_xy_mm=[182, 92.2],
        J13_world_centers_mm=j13,
        shell_dimensions_mm=[334, 188.4, 45.6],
        new_post_OD_mm=7.2,
        new_post_z_mm=[2.7, 6.5],
        blind_bore_OD_mm=3.2,
        tool_nominal_OD_requirement_mm=5.6,
        relative_position_clearance_reserve_mm=0.45,
        test_tool_OD_mm=6.5,
        test_tool_z_mm=[8.1, 60.1],
        old_axis_blocked_witness_required=True,
        both_fixed_and_raised_component_reserves_checked=True,
        candidate_panel_transform_not_adopted=True,
        support_seat_boolean_guard_mm=0.00002,
        exact_driver_fastener_insert_selected=False,
        strain_relief_implemented=False,
        lid_removal_path_assembly_or_physical_verified=False,
        receiver_PDN_result_inherited=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify(executable):
    report = json.loads((OUT / "analysis.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "analysis.json", OUT / "checks.scad"]}
    cases = {}
    names = [
        "geometry",
        "tool_geometry",
        "ear_material",
        "nominal_ear_case_collision",
        "ear_case_collision",
        "ear_hardware_collision",
        "ear_electronics_collision",
        "post_joint_collision",
        "post_electronics_collision",
        "post_hardware_collision",
        "tool_hardware_collision",
        "tool_electronics_collision",
        "tool_open_case_collision",
        "shaft_bore_collision",
        "floor_bond",
        "old_axis_blocked_witness",
        "post_positive_control",
        "ear_positive_control",
        "tool_positive_control",
    ]
    (OUT / "verification.json").unlink(missing_ok=True)
    for short in names:
        name = "access_" + short
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="access_only"']
        for key, value in dict(
            body_width=334, body_depth=188.4, shell_height=45.6, fasteners=FASTENERS, trial=name
        ).items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = process.stdout + process.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        empty = (
            process.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        )
        if short.endswith("collision") and empty and clean:
            row = dict(clear=True, empty=True)
        elif (
            process.returncode == 0
            and target.exists()
            and clean
            and (
                "NoError" in log
                or (
                    short == "tool_geometry"
                    and "3D object (PolySet)" in log
                    and any(line.strip().split() == ["Convex:", "yes"] for line in log.splitlines())
                )
            )
        ):
            stats = binary_stl(target)
            ok = not short.endswith("collision") and stats["volume_mm3"] > 0.001
            if short == "tool_geometry":
                stats.update(surface_components(target))
                ok &= stats["connected_surface_components"] == 1
                ok &= stats["edges_without_exactly_two_faces"] == 0
                ok &= not stats["collapsed_binary_float_triangles"]
                expected_volume = 64 * 3.25**2 * math.sin(2 * math.pi / 128) * 52
                ok &= math.isclose(stats["volume_mm3"], expected_volume, abs_tol=0.005)
                for key, expected in [("min_mm", [178.75, 88.95, 8.1]), ("max_mm", [185.25, 95.45, 60.1])]:
                    ok &= all(
                        math.isclose(a, b, abs_tol=3e-5) for a, b in zip(stats[key], expected, strict=True)
                    )
            if short.endswith("positive_control"):
                ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            if short == "old_axis_blocked_witness":
                ok &= math.isclose(stats["volume_mm3"], 11.3508465325, abs_tol=1e-5)
            if short == "floor_bond":
                ok &= math.isclose(stats["volume_mm3"], math.pi * 3.6**2 * 0.1, abs_tol=0.003)
            row = dict(clear=bool(ok), **stats)
        else:
            row = dict(clear=False, returncode=process.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        native_local_ear_post_open_lid_tool_checks_clear=not changed
        and all(r["clear"] for r in cases.values()),
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
        lid_removal_driver_retention_or_physical_qualified=False,
        complete_harness_or_receiver_PDN_qualified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["native_local_ear_post_open_lid_tool_checks_clear"] else 1)
