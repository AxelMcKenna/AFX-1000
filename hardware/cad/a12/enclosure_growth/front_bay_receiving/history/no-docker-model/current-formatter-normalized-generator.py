"""Native planar data calibrated into a declared proper Rx+90 receiving frame.

No KiCad STEP origin is assumed. Unknown selected heights remain receiving
requirements, never manufacturer guarantees or assembled acceptance.
"""

import json
from pathlib import Path

from hardware.cad.a12.positive_links.selected_parts import requirement
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

from .capture import ROOT, sha


def normalized_footprint(value):
    suffix = value.split(":", 1)[1]
    return suffix.replace("__", ":", 1) if "__" in suffix else value


def height(part):
    fp = normalized_footprint(part["footprint"])
    name = part["part"]
    exact = requirement(fp, name)
    if exact:
        return exact["assembled_projection_requirement_mm"], "exact-primary-body-plus-PROJECT-seat", exact
    if "TMR 1-" in name:
        return (
            12.0,
            "primary11.0+0.5-general-tolerance-plus-PROJECT0.5seat",
            dict(
                primary="https://www.tracopower.com/products/tmr1.pdf",
                page=4,
                body_normal_max_mm=11.5,
                seating_requirement_max_mm=0.5,
                original_pin_nominal_mm=3.2,
                original_pin_tolerance_mm=0.5,
            ),
        )
    if "MKS2C042201" in name:
        return (
            14.0,
            "primary13nom-plus-PROJECT0.5case-and0.5seat",
            dict(
                primary="https://www.wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf",
                page=2,
                nominal_body_mm=[7.2, 7.2, 13],
                body_size_tolerance_max_not_established=True,
                case_increment_receiving_mm=0.5,
                seating_requirement_max_mm=0.5,
            ),
        )
    if "MKS2C041001" in name:
        return (
            11.0,
            "primary10nom-plus-PROJECT0.5case-and0.5seat",
            dict(
                primary="https://www.wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf",
                page=2,
                nominal_body_mm=[7.2, 5, 10],
                body_size_tolerance_max_not_established=True,
                case_increment_receiving_mm=0.5,
                seating_requirement_max_mm=0.5,
            ),
        )
    if "TLP4590AF" in name:
        return (
            4.3,
            "primary3.8body-plus-PROJECT0.5seat",
            dict(
                primary=part["source"],
                page=13,
                body_normal_max_mm=3.8,
                standoff_manufacturer_is_MINIMUM_mm=0.25,
                seating_requirement_max_mm=0.5,
            ),
        )
    if "TLP175A" in name:
        return (
            2.8,
            "primary2.2body-plus-PROJECT0.6seat",
            dict(
                primary=part["source"],
                page=7,
                body_normal_max_mm=2.2,
                standoff_manufacturer_is_MINIMUM_mm=0.5,
                seating_requirement_max_mm=0.6,
            ),
        )
    if "ABLS-" in name:
        return (
            4.3,
            "primary4.2max-plus-PROJECT0.1seat",
            dict(
                primary="https://abracon.com/Resonators/abls.pdf",
                page=3,
                body_normal_max_mm=4.2,
                seating_requirement_max_mm=0.1,
            ),
        )
    if "CSD19536KTT" in name:
        return (
            4.8,
            "primaryKTT4.7max-plus-PROJECT0.1seat",
            dict(
                primary="https://www.ti.com/lit/ds/symlink/csd19536ktt.pdf",
                page=13,
                body_normal_max_mm=4.7,
                seating_requirement_max_mm=0.1,
            ),
        )
    if "C1210C104J5GACTU" in name:
        return (
            1.5,
            "KEMETTable1B-FG1.25+0.15-plus-PROJECT0.1seat",
            dict(
                primary="https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
                tables=["1B", "2A"],
                body_normal_max_mm=1.4,
                seating_requirement_max_mm=0.1,
            ),
        )
    if "C1206C" in name:
        return (
            1.9,
            "KEMET1206family-maximum-used1.8-plus-PROJECT0.1seat",
            dict(
                primary="https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
                table="2A",
                largest_relevant_case_EH_max_mm=1.8,
                exact_thickness_code_may_be_smaller=True,
                seating_requirement_max_mm=0.1,
            ),
        )
    if fp.startswith("Connector_") or name.startswith("JST "):
        if name.startswith("JST "):
            return (
                10.5,
                "JST9.8reference-assembly-plus-PROJECT0.7receiving",
                dict(
                    primary="https://www.jst-mfg.com/product/pdf/eng/eXH.pdf",
                    page=2,
                    reference_assembled_height_mm=9.8,
                    manufacturer_maximum_not_established=True,
                ),
            )
        return (
            12.0,
            "UNSELECTED-connector-project-receiving-depth",
            dict(selected_production_connector=None, manufacturer_bound=None),
        )
    if fp.startswith("Resistor_"):
        return (
            1.0,
            "PROJECT-receiving-projection-unaccepted",
            dict(manufacturer_bound=None, missing="exact MPN/package height/seat approval"),
        )
    if fp.startswith("Capacitor_"):
        return (
            3.0,
            "PROJECT-receiving-projection-unaccepted",
            dict(manufacturer_bound=None, missing="unselected exact MPN/package height/seat approval"),
        )
    return (
        2.0,
        "PROJECT-receiving-projection-unaccepted",
        dict(
            manufacturer_bound=None,
            missing="per-MPN dimensional/tolerance/seat approval; broad2mm allocation",
        ),
    )


def frame(origin, u, v, w):
    return [origin[0] + u, origin[1] - w, origin[2] + v]


def world_box(origin, bounds, loww, hiw):
    u0, v0, u1, v1 = bounds
    return [origin[0] + u0, origin[1] - hiw, origin[2] + v0, u1 - u0, hiw - loww, v1 - v0]


def build():
    target = ROOT / "generated/model233.json"
    if target.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("Fresh receiving model required")
    cap = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in cap["copied_input_sha256"].items())
    boxes = []
    tails = []
    mates = []
    cables = []
    boards = []
    records = []
    calibration = []
    for ident, folder, pcbname, compname, origin, dims in [
        (
            "NF233",
            "NF233",
            "negative_startup_ready.kicad_pcb",
            "components.json",
            [172, 180.5, 3.5],
            [149, 39],
        ),
        ("FPC84", "FPC84", "fan_power_health.kicad_pcb", "components.json", [14, 180.5, 3.5], [66, 38]),
    ]:
        base = ROOT / "inputs" / folder
        pcb = base / pcbname
        tree = read_sexpr(pcb.read_text())
        parts = json.loads((base / compname).read_text())
        byref = {p["ref"]: p for p in parts}
        fps = children(tree, "footprint")
        assert len(fps) == len(parts)
        edges = children(tree, "gr_line")
        corners = {
            tuple(map(float, first(e, k)[1:3]))
            for e in edges
            if first(e, "layer")[1] == "Edge.Cuts"
            for k in ["start", "end"]
        }
        assert corners == {(0.0, 0.0), (dims[0], 0.0), tuple(dims), (0.0, dims[1])}
        boards.append(
            dict(
                id=ident,
                origin=origin,
                size=dims,
                nominal_thickness=1.6,
                maximum_thickness=1.76,
                maximum_rear_assembly_projection=1.0,
                local_to_world_matrix=[
                    [1, 0, 0, origin[0]],
                    [0, 0, -1, origin[1]],
                    [0, 1, 0, origin[2]],
                    [0, 0, 0, 1],
                ],
                rotation_determinant=1,
                KiCad_STEP_origin_used=False,
                source_sha256=sha(pcb),
            )
        )
        holes = []
        boards[-1]["actual_drilled_holes_local"] = holes
        for fp in fps:
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            part = byref[ref]
            value = next(p[2] for p in children(fp, "property") if p[1] == "Value")
            assert value == part["part"], ref
            side = first(fp, "layer")[1][0]
            bounds = courtyard(fp, side + ".CrtYd")
            projection, basis, details = height(part)
            if side == "B":
                projection = 1.0
                basis = "ROOT explicit rear-assembly1mm receiving requirement, NOT supplier guarantee"
                details = dict(selected_part=part["part"], body_seat_tail_complete_acceptance=False)
            loww, hiw = (0, projection) if side == "F" else (-1.76 - projection, -1.76)
            box = world_box(origin, bounds, loww, hiw)
            boxes.append([ident + "_" + ref, *box])
            records.append(
                dict(
                    id=ident + "_" + ref,
                    ref=ref,
                    part=part["part"],
                    native_footprint=fp[1],
                    native_pose=first(fp, "at")[1:],
                    native_side=side,
                    native_courtyard=bounds,
                    world_box_mm=box,
                    projection_mm=projection,
                    basis=basis,
                    details=details,
                    physical_accepted=False,
                )
            )
            pads = children(fp, "pad")
            drilled = []
            for pad in pads:
                number = pad[1]
                xy = transform(fp, first(pad, "at")[1:3])
                calibration.append(
                    dict(
                        id=ident + "_" + ref + "." + str(number),
                        native_xy=list(xy),
                        front_reference_world_mm=frame(origin, *xy, 0),
                        world_F_normal=[0, -1, 0],
                    )
                )
                drill = children(pad, "drill")
                if drill:
                    raw = drill[0]
                    dx, dy = (
                        (float(raw[2]), float(raw[3])) if raw[1] == "oval" else (float(raw[1]), float(raw[1]))
                    )
                    at = first(pad, "at")
                    holes.append([*xy, dx, dy, float(at[3]) if len(at) > 3 else 0.0, ref, number])
                    size = first(pad, "size")
                    w = max(float(size[1]), float(size[2])) + 0.4
                    bounds2 = [xy[0] - w / 2, xy[1] - w / 2, xy[0] + w / 2, xy[1] + w / 2]
                    tails.append(
                        [ident + "_" + ref + "." + str(number), *world_box(origin, bounds2, -2.76, -1.76)]
                    )
                    drilled.append(dict(pin=number, native_xy=list(xy), drill=drill[0][1:]))
            if ref.startswith("J"):
                grow = 0.5
                mb = [bounds[0] - grow, bounds[1] - grow, bounds[2] + grow, bounds[3] + grow]
                mates.append(
                    [
                        ident + "_" + ref,
                        *world_box(origin, mb, 2.0 if part["part"].startswith("JST ") else 3.0, projection),
                    ]
                )
                # Explicit short straight bundle receiving allocation only. No
                # bend radius/complete route/current/strain qualification.
                cables.append([ident + "_" + ref, *world_box(origin, mb, projection, projection + 10)])
            records[-1]["actual_drilled_pads"] = drilled
    generated = ROOT / "generated"
    generated.mkdir(exist_ok=True)
    data = dict(
        boards=boards,
        component_records=records,
        boxes=boxes,
        tails=tails,
        mates=mates,
        prospective_straight_bundle_receivers=cables,
        native_pad_calibration=calibration,
        source_sha256={
            str(Path(__file__)): sha(Path(__file__)),
            str(ROOT / "capture.json"): sha(ROOT / "capture.json"),
        },
        body_dimensions_and_seating_accepted=False,
        mated_and_bundle_requirements_accepted=False,
        trimmed_rear_tail_requirement_mm=1.0,
        NF233_successor_incorporated=True,
        later_FPC_routing_incorporated=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    target.write_text(json.dumps(data, indent=2) + "\n")
    scad = "// Actual native planar coordinates; declared properRx+90 receivingframe.\n"
    for n, rows in [
        ("fr_boards", boards),
        ("fr_boxes", boxes),
        ("fr_tails", tails),
        ("fr_mates", mates),
        ("fr_bundles", cables),
    ]:
        if n == "fr_boards":
            rows = [[b["id"], b["origin"], b["size"], b["actual_drilled_holes_local"]] for b in boards]
        scad += n + "=" + json.dumps(rows) + ";\n"
    scad += """
module fr_boxes(rows,id="all",m=0){for(b=rows)if(id=="all"||substr_id(b[0],id))translate([b[1]-m,b[2]-m,b[3]-m])cube([b[4]+2*m,b[5]+2*m,b[6]+2*m]);}
module fr_drill(h,m=0){translate([h[0],h[1],-1.77-m])rotate([0,0,-h[4]])hull()for(t=[-1,1])translate([h[2]>h[3]?t*(h[2]-h[3])/2:0,h[3]>h[2]?t*(h[3]-h[2])/2:0,0])cylinder(d=min(h[2],h[3]),h=1.78+2*m,$fn=64);}
// Filled holes in expanded external-clearance PCB are conservative. Actual
// unexpanded PCB retains EVERY native drilled pad, not a generic slab.
module fr_PCB(id="all",m=0){for(b=fr_boards)if(id=="all"||b[0]==id)translate(b[1])rotate([90,0,0])difference(){translate([-m,-m,-1.76-m])cube([b[2][0]+2*m,b[2][1]+2*m,1.76+2*m]);if(m==0)for(h=b[3])fr_drill(h);}}
module fr_receiving(id="all",m=0){fr_PCB(id,m);fr_boxes(fr_boxes,id,m);fr_boxes(fr_tails,id,m);fr_boxes(fr_mates,id,m);}
"""
    (generated / "components233.scad").write_text(scad)
    print(
        json.dumps(
            dict(
                boards=2,
                parts=len(records),
                actual_drilled_pad_receivers=len(tails),
                prospective_connector_mates=len(mates),
                prospective_short_bundles=len(cables),
            )
        )
    )


if __name__ == "__main__":
    build()
