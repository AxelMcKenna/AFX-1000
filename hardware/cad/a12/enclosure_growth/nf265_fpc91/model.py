"""Actual NF267/FPC91 native planar geometry in explicit receiving frames."""

import json

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

from .capture import ROOT, sha, write


def world_box(origin, bb, low, high):
    return [origin[0] + bb[0], origin[1] - high, origin[2] + bb[1], bb[2] - bb[0], high - low, bb[3] - bb[1]]


def selected_height(part, selections):
    """Known dimensional bounds; remaining packages are explicit requirements.

    Historical NP selections are used only for matching exact MPNs, or named
    same-family land/body envelopes. They do not select a production MPN for
    generic values in the new BOM and do not close complete electrical bounds.
    """
    name, fp = part["part"], part["footprint"]
    for row in selections:
        mpn = row.get("MPN")
        if mpn and mpn in name and isinstance(row.get("body_plus_seat_max_mm"), (int, float)):
            return row["body_plus_seat_max_mm"], "exact-NP01-primary-body-plus-PROJECT-seat", row
    if "TMR 1-" in name:
        return (
            12.0,
            "primary11.5-body-plus-PROJECT0.5-seat",
            {"source": "https://www.tracopower.com/products/tmr1.pdf", "page": 4},
        )
    if "MKS2C042201" in name:
        return (
            14.0,
            "primary13-nominal-plus-PROJECT0.5-body-0.5-seat",
            {
                "source": "https://www.wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf",
                "supplier_body_max_unestablished": True,
            },
        )
    if "MKS2C041001" in name:
        return (
            11.0,
            "primary10-nominal-plus-PROJECT0.5-body-0.5-seat",
            {
                "source": "https://www.wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf",
                "supplier_body_max_unestablished": True,
            },
        )
    for key, h, body in [
        ("CSD19536KTT", 4.8, 4.7),
        ("TLP4590AF", 4.3, 3.8),
        ("TLP175A", 2.8, 2.2),
        ("ABLS-", 4.3, 4.2),
        ("C3225X7R1E106K250AC", 2.9, 2.8),
        ("C0603C104K5RACTU", 1.05, 0.95),
        ("C0603C272J5GACTU", 0.97, 0.87),
        ("C0603C150J5GACTU", 0.97, 0.87),
        ("C1206C104J3GACTU", 1.9, 1.8),
        ("C1210C104J5GACTU", 1.5, 1.4),
    ]:
        if key in name:
            return (
                h,
                "captured-primary-body-plus-PROJECT-seat",
                {
                    "MPN_key": key,
                    "body_max_mm": body,
                    "assembled_receiving_mm": h,
                    "source": part.get("source"),
                    "physical_accepted": False,
                },
            )
    if "TPS2553DBVR" in name:
        return (
            1.55,
            "primary-max-including-flash1.45-plus-PROJECT0.1seat",
            {"source": "https://www.ti.com/lit/ds/symlink/tps2553.pdf", "body_max_mm": [2.25, 3.55, 1.45]},
        )
    families = [
        ("TNPW1206", 0.75),
        ("TNPW0805", 0.65),
        ("TNPU0805", 0.65),
        ("TNPU0603", 0.65),
        ("CRCW2010", 0.8),
        ("WSL2512", 0.989),
        ("PROPOSED_KEMET0603", 1.05),
        ("PROPOSED_KEMET1206", 1.9),
        ("PROPOSED_KEMET1210", 1.5),
        ("C_1206_", 1.9),
        ("R_0805_", 0.65),
        ("C_0603_", 1.05),
    ]
    for family, h in families:
        if family in fp:
            return (
                h,
                "named-family-PROJECT-receiving-unaccepted",
                {"family": family, "exact_MPN_and_process_accepted": False},
            )
    return (
        2.0,
        "PROJECT-package-projection-unaccepted",
        {"supplier_bound": None, "source": part.get("source")},
    )


def build():
    if (ROOT / "generated/model.json").exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New model output required")
    cap = json.loads((ROOT / "capture.json").read_text())
    assert all(sha(ROOT / n) == h for n, h in cap["copied_input_sha256"].items())
    base = ROOT / "inputs/hardware/qualification/boards"
    nc = base / "nf_connector_receiving265"
    ports = {p["ref"]: p for p in json.loads((nc / "ports-v2.json").read_text())["ports"]}
    selections = json.loads((nc / "inputs/references/NP01-selections.json").read_text())["rows"]
    placement = json.loads((base / "startup_negative_circuit/physical_layout/placement.json").read_text())
    rear_tall = set(placement["local_rear_1p9_mm_receiving_caps"])
    assert len(rear_tall) == 14
    boards, records, boxes, tails, mates, calibration = [], [], [], [], [], []
    policy_conflicts = []
    for ident, folder, pcbname, origin, dims, expected in [
        (
            "NF265",
            "startup_negative_circuit/physical_layout",
            "negative_startup_physical.kicad_pcb",
            [172, 180.5, 3.5],
            [149, 39],
            265,
        ),
        (
            "FPC91",
            "fan_health/composite_nf_branch",
            "fan_power_health.kicad_pcb",
            [14, 180.5, 3.5],
            [66, 38],
            91,
        ),
    ]:
        folder = base / folder
        pcb = folder / pcbname
        tree = read_sexpr(pcb.read_text())
        parts = json.loads((folder / "components.json").read_text())
        byref = {p["ref"]: p for p in parts}
        assert len(byref) == len(parts) == expected
        fps = children(tree, "footprint")
        assert len(fps) == expected + (2 if ident == "NF265" else 0)
        corners = {
            tuple(map(float, first(e, k)[1:3]))
            for e in children(tree, "gr_line")
            if first(e, "layer")[1] == "Edge.Cuts"
            for k in ["start", "end"]
        }
        assert corners == {(0.0, 0.0), (dims[0], 0.0), tuple(dims), (0.0, dims[1])}
        holes, actual_refs, mechanical = [], [], []
        for fp in fps:
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            side = first(fp, "layer")[1][0]
            if ref in byref:
                actual_refs.append(ref)
                part = byref[ref]
                value = next(p[2] for p in children(fp, "property") if p[1] == "Value")
                assert value == part["part"], ref
                bb = courtyard(fp, side + ".CrtYd")
                h, basis, details = selected_height(part, selections)
                if side == "B":
                    required = 1.9 if ident == "NF265" and ref in rear_tall else 1.2
                    if h > required + 1e-9 and not basis.startswith("PROJECT"):
                        policy_conflicts.append(
                            dict(
                                id=ident + "_" + ref,
                                primary_or_family_projection_mm=h,
                                declared_policy_mm=required,
                            )
                        )
                    h = max(h, required) if not basis.startswith("PROJECT") else required
                    basis += "; explicit rear receiving policy=" + str(required) + "mm"
                lo, hi = (0, h) if side == "F" else (-1.76 - h, -1.76)
                row = [ident + "_" + ref, *world_box(origin, bb, lo, hi)]
                if ident == "NF265" and ref in ports:
                    port = ports[ref]
                    assert side == "F" and all(
                        abs(float(a) - b) < 1e-8 for a, b in zip(first(fp, "at")[1:3], port["anchor_mm"])
                    )
                    angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
                    assert angle == port["rotation_deg"]
                    pb = port["receiving_body_uv_bounds_mm"]
                    u, v = port["anchor_mm"]
                    bbp = [pb[0] + u, pb[1] + v, pb[2] + u, pb[3] + v]
                    row = [
                        ident + "_" + ref,
                        *world_box(origin, bbp, 0, port["receiving_body_front_normal_mm"]),
                    ]
                    mates.append(row)
                    basis = "exact-NC265-port-v2-receiving-NOT-supplier-max"
                    details = port
                else:
                    boxes.append(row)
                    if ref.startswith("J"):
                        if part["part"].startswith("JST "):
                            nominal = courtyard(fp, "F.Fab")
                            mb = [nominal[0] - 0.3, nominal[1] - 0.3, nominal[2] + 0.3, nominal[3] + 0.3]
                            normal = 9.0 if "PH-" in part["part"] else 10.5
                            mates.append([ident + "_" + ref, *world_box(origin, mb, 0, normal)])
                        else:
                            mates.append(
                                [
                                    ident + "_" + ref,
                                    *world_box(
                                        origin, [bb[0] - 0.5, bb[1] - 0.5, bb[2] + 0.5, bb[3] + 0.5], 0, 12
                                    ),
                                ]
                            )
                records.append(
                    dict(
                        id=ident + "_" + ref,
                        ref=ref,
                        part=part["part"],
                        native_footprint=fp[1],
                        native_side=side,
                        native_pose=first(fp, "at")[1:],
                        native_courtyard=bb,
                        world_box_mm=row[1:],
                        projection_mm=row[5],
                        basis=basis,
                        details=details,
                        physical_accepted=False,
                    )
                )
            else:
                assert ident == "NF265" and ref in {"H101", "H102"}
                mechanical.append(ref)
            for pad in children(fp, "pad"):
                xy = transform(fp, first(pad, "at")[1:3])
                calibration.append(
                    dict(
                        id=ident + "_" + ref + "." + str(pad[1]),
                        native_uv=list(xy),
                        front_reference_world_mm=[origin[0] + xy[0], origin[1], origin[2] + xy[1]],
                    )
                )
                ds = children(pad, "drill")
                if not ds:
                    continue
                d = [
                    float(x)
                    for x in ds[0][1:]
                    if isinstance(x, (float, int)) or (isinstance(x, str) and x.replace(".", "", 1).isdigit())
                ]
                assert len(d) in {1, 2}, (ref, ds)
                dx, dy = d if len(d) == 2 else (d[0], d[0])
                angle = float(first(pad, "at")[3]) if len(first(pad, "at")) > 3 else 0
                holes.append([*xy, dx, dy, angle, ref, str(pad[1])])
                if ref in byref and str(pad[2]) == "thru_hole":
                    size = first(pad, "size")
                    span = max(float(size[1]), float(size[2])) + 0.4
                    tb = [xy[0] - span / 2, xy[1] - span / 2, xy[0] + span / 2, xy[1] + span / 2]
                    tails.append(
                        [ident + "_" + ref + "." + str(pad[1]), *world_box(origin, tb, -3.26, -1.76)]
                    )
        assert set(actual_refs) == set(byref)
        boards.append(
            dict(
                id=ident,
                origin=origin,
                size=dims,
                holes=holes,
                parts=len(parts),
                native_FPs=len(fps),
                mechanical_refs=mechanical,
                source_PCB_sha256=sha(pcb),
                frame_matrix=[
                    [1, 0, 0, origin[0]],
                    [0, 0, -1, origin[1]],
                    [0, 1, 0, origin[2]],
                    [0, 0, 0, 1],
                ],
                rotation_determinant=1,
            )
        )
    assert len(records) == 356 and sum(b["native_FPs"] for b in boards) == 358
    assert len({r["id"] for r in records}) == 356
    data = dict(
        boards=boards,
        component_records=records,
        boxes=boxes,
        tails=tails,
        mates=mates,
        native_pad_calibration=calibration,
        electrical_parts=356,
        total_native_FPs=358,
        rear_named1p9=sorted(rear_tall),
        rear_policy_conflicts=policy_conflicts,
        external_clearance_mm=0.25,
        independent_PCB_position_mm=0.2,
        combined_external_margin_mm=0.45,
        FR4_max_mm=1.76,
        THT_trim_plus_fillet_receiving_mm=1.5,
        strain_fastener_rear_projection_mm=2.07,
        PH1p76_supplier_status="FAILED-board-catalog0.8..1.6-vs-receiving1.76",
        unknown_PROJECT_receivers_accepted=False,
        full_harness_qualified=False,
        physical_qualified=False,
    )
    write(ROOT / "generated/model.json", data)
    scad = "// NEW actual356electricalparts/358nativeFPs; properRx+90, no STEP-Z assumption.\n"
    for name, rows in [
        ("fr_boards", [[b["id"], b["origin"], b["size"], b["holes"]] for b in boards]),
        ("fr_boxes", boxes),
        ("fr_tails", tails),
        ("fr_mates", mates),
        ("fr_bundles", []),
    ]:
        scad += name + "=" + json.dumps(rows) + ";\n"
    scad += """
function fr_matches(name,id)=name==id||(len(name)>len(id)&&name[len(id)]=="_"&&[for(i=[0:len(id)-1])name[i]]==[for(i=[0:len(id)-1])id[i]]);
module fr_boxes(rows,id="all",m=0){for(b=rows)if(id=="all"||fr_matches(b[0],id))translate([b[1]-m,b[2]-m,b[3]-m])cube([b[4]+2*m,b[5]+2*m,b[6]+2*m]);}
module fr_drill(h,m=0){translate([h[0],h[1],-1.77-m])rotate([0,0,-h[4]])hull()for(t=[-1,1])translate([h[2]>h[3]?t*(h[2]-h[3])/2:0,h[3]>h[2]?t*(h[3]-h[2])/2:0,0])cylinder(d=min(h[2],h[3]),h=1.78+2*m,$fn=64);}
module fr_PCB(id="all",m=0){for(b=fr_boards)if(id=="all"||b[0]==id)translate(b[1])rotate([90,0,0])difference(){translate([-m,-m,-1.76-m])cube([b[2][0]+2*m,b[2][1]+2*m,1.76+2*m]);if(m==0)for(h=b[3])fr_drill(h);}}
"""
    target = (
        ROOT
        / "context/hardware/cad/a12/enclosure_growth/front_bay_receiving/robust_rear_variant/components.scad"
    )
    old = target.read_bytes()
    target.write_text(scad)
    write(
        ROOT / "generated/derived-model-replacement.json",
        dict(
            target=str(target.relative_to(ROOT)),
            captured_original_sha256=__import__("hashlib").sha256(old).hexdigest(),
            replacement_sha256=sha(target),
            only_new_context_changed=True,
        ),
    )
    print(
        json.dumps(
            dict(
                electrical_parts=356,
                native_FPs=358,
                component_boxes=len(boxes),
                mated_receivers=len(mates),
                THT_tails=len(tails),
                policy_conflicts=policy_conflicts,
            )
        )
    )


if __name__ == "__main__":
    build()
