"""Actual filled U102 PCB candidate plus separate wider local contact; no frozen edits."""

import copy
import json
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import height, outline
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
METAL = [121.75, 117.5, 128.75, 122.5]
TIM = [120.75, 116.5, 129.75, 123.5]


def actual_candidate_packet(native, pcb, bom):
    result = copy.deepcopy(native)
    tree = read_sexpr(pcb.read_text())
    parts = {c["ref"]: c for c in json.loads(bom.read_text())}
    result["boxes"] = [r for r in result["boxes"] if not r[0].startswith("P03_")]
    result["cylinders"] = [r for r in result["cylinders"] if not r[0].startswith("P03_")]
    result["component_records"] = [r for r in result["component_records"] if r["board"] != "P03"]
    board = next(b for b in result["boards"] if b["id"] == "P03")
    datum = board["datum"]
    tmin, tmax = board["thickness_range_allocation_mm"]
    assert datum == [168, 108, 6.5] and outline(tree) == board["outline_relative_mm"]
    actual_refs = set()
    for fp in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        name = "P03_" + ref
        if ref.startswith("H"):
            for pad in children(fp, "pad"):
                if pad[2] != "np_thru_hole":
                    continue
                xy = transform(fp, first(pad, "at")[1:3])
                projection, basis = height(str(fp[1]), ref, "unselected M2 head/washer")
                result["cylinders"].append(
                    [
                        name + "_mount_head",
                        xy[0] + 68,
                        xy[1] + 8,
                        datum[2] + tmin,
                        5.6,
                        projection + tmax - tmin,
                    ]
                )
            continue
        actual_refs.add(ref)
        part = parts[ref]
        assert str(fp[1]) == part["footprint"]
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        box = courtyard(fp, side + ".CrtYd")
        projection, basis = height(str(fp[1]), ref, part["part"])
        z = datum[2] - projection if side == "B" else datum[2] + tmin
        h = projection if side == "B" else projection + tmax - tmin
        row = [name, box[0] + 68, box[1] + 8, z, box[2] - box[0], box[3] - box[1], h]
        if "CP_Radial" in str(fp[1]) and side == "F":
            result["cylinders"].append([name, row[1] + row[4] / 2, row[2] + row[5] / 2, z, max(row[4:6]), h])
        else:
            result["boxes"].append(row)
        result["component_records"].append(
            dict(
                board="P03",
                ref=ref,
                face=side,
                actual_footprint=str(fp[1]),
                part=part["part"],
                maximum_projection_allocation_mm=projection,
                height_basis=basis,
                component_and_mate_height_approved=False,
            )
        )
        for pad in children(fp, "pad"):
            if pad[2] != "thru_hole":
                continue
            xy = transform(fp, first(pad, "at")[1:3])
            result["boxes"].append(
                [name + "_tail_" + str(pad[1]), xy[0] + 66.6, xy[1] + 6.6, datum[2] - 1.5, 2.8, 2.8, 1.5]
            )
    assert actual_refs == set(parts) and len(parts) == 255
    return result


def main():
    import cadquery as cq

    OUT.mkdir(exist_ok=True)
    pcb = ROOT / "sources/power_p03.kicad_pcb"
    bom = ROOT / "sources/components.json"
    receipt = json.loads((ROOT / "sources/u102-candidate.json").read_text())
    construction = json.loads((ROOT / "sources/construction.json").read_text())
    assert receipt["candidate_pcb_sha256"] == construction["pcb_sha256"] == sha(pcb)
    native, data, hashes = snapshot()
    native = actual_candidate_packet(native, pcb, bom)
    # Canonical P03 is only a source for shared datum/other-board geometry. Every
    # candidate P03 body, tail and mount is independently rebuilt from its own PCB.
    native["source_sha256"] = {
        str(p.relative_to(REPO)): sha(p)
        for p in [pcb, bom, ROOT / "sources/construction.json", ROOT / "sources/u102-candidate.json"]
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
    source = """include <../../../../../thermal-integration.scad>
trial="geometry";
module candidate(){import("LAND.stl");import("TIM.stl");}
module window(){translate([188.55,124.3,-.01])cube([9.4,7.4,2.82]);}
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
    source += """module links(){import("../../../../../positive_links/generated/positive-links.stl");return_assembly();}
module modified_case(){difference(){retained_thermal_shell();window();}thermal_controls();lower_shell_fasteners();thermal_metal_base();}
if(trial=="geometry")candidate();
if(trial=="component_collision")intersection(){candidate();components();}
if(trial=="link_collision")intersection(){candidate();links();}
if(trial=="case_collision")intersection(){intersection(){candidate();translate([0,0,.00001])cube([334,157,40]);}modified_case();}
if(trial=="positive_control")intersection(){candidate();translate([193,127,4])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(source)
    sources = [
        ROOT / "generate.py",
        pcb,
        bom,
        ROOT / "sources/construction.json",
        ROOT / "sources/u102-candidate.json",
        REPO / "hardware/cad/a12/repaired.py",
        REPO / "hardware/cad/a12/positive_links/selected_parts.py",
    ]
    (OUT / "geometry.json").write_text(
        json.dumps(
            dict(
                revision="U102-wider-actual-nine-via-candidate",
                metal_native_mm=METAL,
                tim_native_mm=TIM,
                volumes_mm3=volumes,
                proposed_floor_window_housing_mm=[188.55, 124.3, 197.95, 131.7],
                metal_top_z=5.28,
                tim_collision_top_z=6.3,
                pcb_datum=board_datum(native),
                source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                reference_shared_source_sha256=hashes,
                actual_component_count=len(native["component_records"]),
                candidate_pcb_sha256=sha(pcb),
                nominal_tail_to_tim_left_gap_mm=0.35,
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
