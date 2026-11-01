"""TC02 front-bay floor-post candidate; no adoption or physical proof."""

import copy
import hashlib
import json
import re
from pathlib import Path

from hardware.cad.a12.enclosure_growth.integration.stage import actual_bores
from hardware.cad.a12.repaired import outline
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
A12 = ROOT.parent
EI = A12 / "enclosure_growth/integration"
TC = A12 / "trill_mount_candidate"
J29 = A12 / "harness/proposals/processor-awg18-ear-fanout-j29"
GROWTH = REPO / "hardware/electronics/rail_disconnect/revision28/generated/p9-growth-band43-work"
OUT = ROOT / "generated"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    OUT.mkdir(exist_ok=True)
    for parent in [EI, TC]:
        seal = json.loads((parent / "handoff.json").read_text())
        assert all(sha(parent / n) == h for n, h in seal["files_sha256"].items())
    tc = json.loads((TC / "report.json").read_text())
    scene = json.loads((EI / "generated/scene.json").read_text())
    shift = [0, 34.5, -10.6]
    centres = [[round(m["world_xy_mm"][0], 7), round(m["world_xy_mm"][1] + 34.5, 7)] for m in tc["mounts"]]
    assert centres == [[130.0871, 168.922], [93.0871, 168.9352]]
    pcb = J29 / "processor_carrier.kicad_pcb"
    assert sha(pcb) == "302ec64b2c4d027476de5ac903e76f2ead32a4955f68ef425e9ad21a4147cfd2"
    native = json.loads((J29 / "generated/native.json").read_text())
    assert not any(native["counts"].values()) and native["candidate_pcb_sha256"] == sha(pcb)
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    fp = fps["J29"]
    xy = courtyard(fp, "F.CrtYd")
    newbox = [
        "e19_J29",
        round(xy[0] - 70 - 0.5, 6),
        round(xy[1] - 58 - 0.5, 6),
        8.1,
        round(xy[2] - xy[0] + 1, 6),
        round(xy[3] - xy[1] + 1, 6),
        11.31,
    ]
    assert newbox[1:3] == [163.05, 97.53]
    inherited = [r for r in scene["inherited_envelopes"] if not r[0].startswith("e19_J29")] + [newbox]
    for p in children(fp, "pad"):
        x, y = transform(fp, first(p, "at")[1:3])
        inherited.append(["e19_J29_lead_" + str(p[1]), x - 71, y - 59, 3.35, 2, 2, 3.15])
    gp = GROWTH / "rail_disconnect.kicad_pcb"
    assert sha(gp) == "67b746d0bff1169e6f1cfee89745a7e9566d60e9315836c24c1534eb98a15c6a"
    gr = json.loads((GROWTH / "generated/outline-growth.json").read_text())
    gtree = read_sexpr(gp.read_text())
    before = copy.deepcopy(gtree)
    for change in gr["changes"]:
        target = sexpr(read_sexpr(change["after"]))
        indices = [
            i
            for i, v in enumerate(before)
            if isinstance(v, list) and v and v[0] == "gr_line" and sexpr(v) == target
        ]
        assert len(indices) == 1
        before[indices[0]] = read_sexpr(change["before"])
    assert max(p[1] for p in outline(before)) == 45.25 and max(p[1] for p in outline(gtree)) == 54.5
    inputs = [
        Path(__file__),
        EI / "handoff.json",
        EI / "generated/checks.scad",
        EI / "generated/scene.json",
        EI / "generated/analysis.json",
        TC / "handoff.json",
        TC / "report.json",
        A12 / "panel_mount_audit/report.json",
        pcb,
        J29 / "components.json",
        J29 / "handoff.json",
        J29 / "generated/native.json",
        J29 / "generated/current-native.json",
        gp,
        GROWTH / "generated/outline-growth.json",
        GROWTH / "generated/current-native.json",
    ]
    # Exact CAD closure used by the sealed EI01 scene (including real imported hardware).
    inherited_sources = json.loads((EI / "generated/analysis.json").read_text())["source_sha256"]
    hashes = {}
    for name, h in inherited_sources.items():
        assert sha(REPO / name) == h
        hashes[name] = h
    for p in inputs:
        hashes[str(p.relative_to(REPO))] = sha(p)
    for name, h in hashes.items():
        p = REPO / name
        data = p.read_bytes()
        assert hashlib.sha256(data).hexdigest() == h
        dest = ROOT / "sources" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    context = (EI / "generated/checks.scad").read_text()
    overrides = {
        "ui_inherited_envelopes": inherited,
        "ui_receiver_outline": outline(tree),
        "ui_receiver_holes": actual_bores(tree),
    }
    for key, value in overrides.items():
        context, count = re.subn(
            r"^" + key + r"=.*;$", key + "=" + json.dumps(value) + ";", context, flags=re.M
        )
        assert count == 1
    (OUT / "context-derived.scad").write_text(context)
    scad = "include <" + str(OUT / "context-derived.scad") + ">\n"
    for key, value in dict(
        tc2_centres=centres, tc2_shift=shift, tc2_growth=outline(gtree), tc2_before=outline(before)
    ).items():
        scad += key + "=" + json.dumps(value) + ";\n"
    scad += """
tc2_case="geometry";
module tc2_posts(m=0){for(p=tc2_centres)difference(){translate([p[0],p[1],2.7])cylinder(d=(7.2+2*m)/cos(180/128),h=17.3,$fn=128);translate([p[0],p[1],15.3])cylinder(d=2.05,h=4.71,$fn=128);}}
module tc2_board(){translate(tc2_shift)tc_board();}
// Explicit source-derived centres keep the minimum-bore acceptance screen independent.
module tc2_min_board(){difference(){translate([82,158,20])cube([53.848,21.844,1.6]);for(p=tc2_centres)translate([p[0],p[1],19.99])cylinder(d=3.1,h=1.62,$fn=128);}}
module tc2_components(){translate(tc2_shift){tc_components();tc_tails();}}
module tc2_heads(){for(p=tc2_centres){translate([p[0],p[1],21.6])cylinder(d=6.4,h=2.2,$fn=128);translate([p[0],p[1],15.6])cylinder(d=2.5,h=6,$fn=128);}}
module tc2_tool(){for(p=tc2_centres)translate([p[0],p[1],21.6])cylinder(d=6.5,h=38.5,$fn=128);}
module tc2_relative(m){for(p=tc2_centres)translate([p[0],p[1],19.9])cylinder(r=(1.25+m+.005)/cos(180/128),h=1.8,$fn=128);}
module tc2_hardware(){tc2_posts();tc2_heads();}
module tc2_new_material(){tc2_posts();tc2_heads();tc2_board();tc2_components();}
module tc2_existing(){for(b=ui_native_boards)ui_native_PCB(b);ui_receiver();for(b=ui_other_boards)board_reserve(b);ui_components(false);ui_receiver_joint();ui_source_joint();ui_h9_head();}
module tc2_growth_slab(){translate([8,108.5,4.8])linear_extrude(2.1)difference(){polygon(tc2_growth);polygon(tc2_before);}}
module tc2_growth_external(m){tc2_posts(m);}
module tc2_above_floor(){intersection(){tc2_new_material();translate([0,0,2.80002])cube([334,188.4,100]);}}
module tc2_case_open(){ui_shell();rear_panel();thermal_metal_base();}
if(tc2_case=="geometry")tc2_new_material();
if(tc2_case=="posts_geometry")tc2_posts();
if(tc2_case=="growth_slab_geometry")tc2_growth_slab();
if(tc2_case=="existing_collision")intersection(){tc2_new_material();tc2_existing();}
if(tc2_case=="case_collision")intersection(){tc2_above_floor();tc2_case_open();}
if(tc2_case=="controls_collision")intersection(){tc2_new_material();ui_controls_and_lid();}
if(tc2_case=="power_collision")intersection(){tc2_new_material();ui_power_only();}
if(tc2_case=="wire_collision")intersection(){tc2_new_material();pf_wires(.25);}
if(tc2_case=="posts_component_tail_collision")intersection(){tc2_posts();tc2_components();}
if(tc2_case=="heads_components_collision")intersection(){tc2_heads();tc2_components();}
if(tc2_case=="posts_board_collision")intersection(){translate([0,0,-.00002])tc2_posts();tc2_board();}
if(tc2_case=="shank_board_collision")intersection(){translate([0,0,.00002])tc2_heads();tc2_board();}
if(tc2_case=="bore_relative_0p2_collision")intersection(){tc2_relative(.2);tc2_min_board();}
if(tc2_case=="bore_relative_0p3_rejected_sensitivity")intersection(){tc2_relative(.3);tc2_min_board();}
if(tc2_case=="growth_nominal_collision")intersection(){tc2_new_material();tc2_growth_slab();}
if(tc2_case=="growth_0p45_collision")intersection(){tc2_growth_external(.45);tc2_growth_slab();}
if(tc2_case=="growth_0p90_collision")intersection(){tc2_growth_external(.90);tc2_growth_slab();}
if(tc2_case=="openlid_tool_electronics_collision")intersection(){tc2_tool();union(){tc2_existing();tc2_components();}}
if(tc2_case=="openlid_tool_power_case_collision")intersection(){tc2_tool();union(){tc2_case_open();ui_power_only();}}
if(tc2_case=="guide_left_in_place_blocked_witness")intersection(){tc2_tool();translate([0,0,panel_z-guide_thick])guide_plate();}
if(tc2_case=="floor_bond")intersection(){tc2_posts();ui_shell();}
if(tc2_case=="post_positive_control")intersection(){tc2_posts();translate([132.9,168.8,10])cube([.2,.2,.2]);}
if(tc2_case=="body_positive_control")intersection(){tc2_board();translate([100,160,20.5])cube([.2,.2,.2]);}
if(tc2_case=="growth_positive_control")intersection(){tc2_growth_slab();translate([100,160,5.5])cube([.2,.2,.2]);}
if(tc2_case=="tool_positive_control")intersection(){tc2_tool();translate([129.9,168.8,30])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    meta = dict(
        scope=__doc__,
        source_sha256=hashes,
        origin_mm=[82, 158, 20],
        C3_size_mm=[53.848, 21.844, 1.6],
        C3_component_and_tail_shift_from_TC01_mm=shift,
        mount_centres_mm=centres,
        post_OD_mm=7.2,
        post_z_mm=[2.7, 20],
        blind_pilot_mm=dict(diameter=2.05, z=[15.3, 20]),
        head_washer_requirement_mm=[6.4, 2.2],
        shank_maximum_requirement_mm=2.5,
        screw_underhead_nominal_requirement_mm=6,
        nominal_engagement_without_washer_mm=4.4,
        washer_thickness_and_actual_engagement_approved=False,
        source_bore_nominal_mm=3.2,
        proposed_minimum_bore_acceptance_requirement_mm=3.1,
        minimum_bore_manufacturer_guaranteed=False,
        relative_fit_allocation_mm=0.2,
        relative_fit_sensitivity_mm=0.3,
        geometry_allowance_mm=0.005,
        nominal_requirement_radial_margin_mm=(3.1 - 2.5) / 2 - 0.2 - 0.005,
        rejected_sensitivity_radial_margin_mm=(3.1 - 2.5) / 2 - 0.3 - 0.005,
        growth_slab_native_source_sha256=sha(gp),
        growth_only_no_ports_or_PDNevidence_inherited=True,
        growth_max_y_mm=163,
        nominal_post_to_slab_gap_mm=168.922 - 3.6 - 163,
        global_XY_sensitivity_envelopes_mm=[0.45, 0.90],
        global_XY_envelopes_not_fabrication_guarantees=True,
        actual_J29_source_sha256=sha(pcb),
        openlid_access_requires_panel_and_guide_removal=True,
        actual_guide_left_in_place_witness_required=True,
        exact_post_material_and_thread_process_selected=False,
        actual_electrode_I2C_harness_unimplemented=True,
        complete_case_fit=False,
        physical_qualified=False,
        thermal_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(dict(sources=len(hashes), mount_centres=centres)))
    return meta


if __name__ == "__main__":
    build()
