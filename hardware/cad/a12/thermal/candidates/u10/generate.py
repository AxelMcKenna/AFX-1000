"""Actual routed-source capture plus explicitly relocated U10 thermal feasibility geometry."""

import copy
import json
from pathlib import Path

from hardware.cad.a12.repaired import outline
from hardware.cad.a12.thermal.candidates.u102.stronger.generate import actual_candidate_packet
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
METAL = [190.1, 127.7, 193.75, 131.4]
TIM = [189.1, 126.7, 194.75, 132.4]


def main():
    import cadquery as cq

    OUT.mkdir(exist_ok=True)
    pcb = ROOT / "variant/power_p03.kicad_pcb"
    bom = ROOT / "sources/components.json"
    receipt = json.loads((ROOT / "variant/receipt.json").read_text())
    assert receipt["candidate_pcb_sha256"] == sha(pcb)
    captured = json.loads((ROOT / "sources/obstacles.json").read_text())
    native, data = captured["native"], captured["other"]
    hashes = {
        str((ROOT / "sources/context" / rel).relative_to(REPO)): expected
        for rel, expected in captured["canonical_source_sha256_at_capture"].items()
    }
    pb_artifact = ROOT / "sources/context/hardware/cad/a12/positive_links/generated/positive-links.stl"
    hashes[str(pb_artifact.relative_to(REPO))] = sha(pb_artifact)
    assert all(sha(REPO / p) == h for p, h in hashes.items()), "Captured shared source changed"
    board = next(b for b in native["boards"] if b["id"] == "P03")
    board["outline_relative_mm"] = [tuple(p) for p in board["outline_relative_mm"]]
    assert outline(read_sexpr(pcb.read_text())) == board["outline_relative_mm"]
    native = actual_candidate_packet(native, pcb, bom)
    native["source_sha256"] = {
        str(p.relative_to(REPO)): sha(p)
        for p in [pcb, bom, ROOT / "variant/construction.json", ROOT / "variant/receipt.json"]
    }
    (OUT / "obstacles.json").write_text(
        json.dumps(dict(native=native, other=data, shared_source_sha256=hashes), indent=2) + "\n"
    )
    volumes = {}
    for name, box, z, h in [("LAND", METAL, 0, 5.28), ("TIM", TIM, 5.28, 1.02)]:
        x, y, xx, yy = box
        solid = (
            cq.Workplane("XY")
            .box(xx - x, yy - y, h, centered=(False, False, False))
            .translate((x + 68, y + 8, z))
        )
        assert solid.val().isValid()
        cq.exporters.export(solid, str(OUT / (name + ".step")))
        cq.exporters.export(solid, str(OUT / (name + ".stl")), tolerance=0.01, angularTolerance=0.05)
        volumes[name] = solid.val().Volume()
    boxes = copy.deepcopy(native["boxes"])
    cylinders = copy.deepcopy(native["cylinders"])
    for r in boxes:
        r[3] -= 0.2
        r[6] += 0.4
    for r in cylinders:
        r[3] -= 0.2
        r[5] += 0.4
    # All actual candidate component faces, through-hole tails and mount heads,
    # plus inherited actual electronics and rear-port reserves, are included.
    others = [r for r in data["envelopes"] if not r[0].startswith("disconnect_")] + data["port_envelopes"]
    source = """include <../sources/context/hardware/cad/a12/thermal-integration.scad>
trial="geometry";
module candidate(){import("LAND.stl");import("TIM.stl");}
module window(){translate([256.9,134.5,-.01])cube([6.05,6.1,2.82]);}
module components(){
"""
    source += "for(b=" + json.dumps(boxes + others) + ")translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);\n"
    other_boards = [b for b in data["boards"] if b[0] != "disconnect_carrier"]
    source += "for(b=" + json.dumps(other_boards) + ")board_reserve(b);\n"
    # E28 native board substrate is an additional actual obstacle; P03 contact
    # with its matched TIM is intentional, so that substrate is excluded.
    for board in native["boards"]:
        if board["id"] == "P03":
            continue
        source += (
            "translate("
            + json.dumps([board["datum"][0], board["datum"][1], board["datum"][2] - 0.2])
            + ")linear_extrude("
            + str(board["thickness_range_allocation_mm"][1] + 0.4)
            + ")polygon("
            + json.dumps(board["outline_relative_mm"])
            + ");\n"
        )
    source += (
        "for(c=" + json.dumps(cylinders) + ")translate([c[1],c[2],c[3]])cylinder(d=c[4],h=c[5],$fn=128);}\n"
    )
    source += """module links(){import("../sources/context/hardware/cad/a12/positive_links/generated/positive-links.stl");return_assembly();}
module modified_case(){difference(){retained_thermal_shell();window();}thermal_controls();lower_shell_fasteners();thermal_metal_base();}
if(trial=="geometry")candidate();
if(trial=="component_collision")intersection(){candidate();components();}
if(trial=="link_collision")intersection(){candidate();links();}
if(trial=="case_collision")intersection(){intersection(){candidate();translate([0,0,.00001])cube([334,157,40]);}modified_case();}
if(trial=="positive_control")intersection(){candidate();translate([259,137,4])cube([.2,.2,.2]);}
if(trial=="source_front_witness")intersection(){components();translate([262.2,137.3,8.3])cube([.2,.2,.2]);}
if(trial=="C32_tail_witness")intersection(){components();translate([258.5,142,5.2])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(source)
    sources = [
        ROOT / "generate.py",
        pcb,
        bom,
        ROOT / "variant/construction.json",
        ROOT / "variant/receipt.json",
        REPO / "hardware/cad/a12/repaired.py",
        REPO / "hardware/cad/a12/positive_links/selected_parts.py",
        REPO / "hardware/cad/a12/thermal/candidates/u102/stronger/generate.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
        REPO / "hardware/electronics/common/sexpr.py",
    ]
    (OUT / "geometry.json").write_text(
        json.dumps(
            dict(
                revision="U10-F-pose-local-draft",
                metal_native_mm=METAL,
                tim_native_mm=TIM,
                volumes_mm3=volumes,
                proposed_floor_window_housing_mm=[256.9, 134.5, 262.95, 140.6],
                metal_top_z=5.28,
                tim_collision_top_z=6.3,
                pcb_datum=board_datum(native),
                source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                reference_shared_source_sha256=hashes,
                actual_component_count=len(native["component_records"]),
                candidate_pcb_sha256=sha(pcb),
                nominal_C32_tail_to_tim_y_gap_mm=0.2,
                pressure_support_and_xy_tolerance_approved=False,
                physical_fit_verified=False,
                thermal_path_qualified=False,
                canonical_base_modified=False,
                canonical_pcb_modified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )


def board_datum(packet):
    return next(b["datum"] for b in packet["boards"] if b["id"] == "P03")


if __name__ == "__main__":
    main()
