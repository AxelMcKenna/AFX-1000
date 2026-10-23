"""Independent E20 PCB and conditional mechanical placement packet."""

import json
import math
from pathlib import Path

from ..common.reports import sha
from ..common.sexpr import children, first, read_sexpr
from ..output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def mechanical(pcb, expected, routed):
    tree = read_sexpr(pcb.read_text())
    copper = {
        str(layer[1])
        for layer in first(tree, "layers")[1:]
        if isinstance(layer, list) and str(layer[1]).endswith(".Cu")
    }
    assert copper == {"F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"}
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    corners = {
        tuple(map(float, first(line, tag)[1:3]))
        for line in children(tree, "gr_line")
        for tag in ("start", "end")
    }
    assert corners == {(100, 100), (191, 100), (191, 127), (100, 127)}
    actual, mounts, bodies = {}, {}, []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pads = [p for p in children(fp, "pad") if str(p[1])]
        if ref.startswith("H"):
            pads = children(fp, "pad")
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole"
            assert float(first(pads[0], "drill")[1]) == 2.4
            x, y = transform(fp, first(pads[0], "at")[1:3])
            mounts[ref] = [x - 100, y - 100]
            bodies.append(
                [
                    f"e20_{ref}_head",
                    197 + x - 102.8,
                    77 + y - 102.8,
                    8.1,
                    5.6,
                    5.6,
                    2.0,
                    "M2 head/washer OD<=5.6,height<=2; exact insert/screw/engagement unqualified",
                ]
            )
            continue
        actual[ref] = {str(p[1]): str(first(p, "net")[-1]).lstrip("/") for p in pads}
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        bounds = courtyard(fp, side + ".CrtYd")
        assert 100 <= bounds[0] < bounds[2] <= 191 and 100 <= bounds[1] < bounds[3] <= 127, (ref, bounds)
        extra = 0.5 if ref.startswith("J") else 0
        x0, y0, x1, y1 = bounds[0] - extra, bounds[1] - extra, bounds[2] + extra, bounds[3] + extra
        if side == "B":
            height = 3.0 if ref == "C13" else 1.5
            z, top = 6.5 - 0.15 - height, 6.5
            note = "Bottom class height limit including solder plus .15mm low-seat allowance; exact MPN/assembly qualification open"
        else:
            height = 11 if ref.startswith("J") else 1.2 if ref.startswith("U") else 0.9
            z, top = 8.1, 8.1 + 0.31 + height
            note = "TLC package max1.2; header/harness<=11 and courtyard+.5; PCB/seat .31mm. Exact harness/physical fit unqualified"
        bodies.append(
            [
                f"e20_{ref}",
                round(197 + x0 - 100, 6),
                round(77 + y0 - 100, 6),
                round(z, 6),
                round(x1 - x0, 6),
                round(y1 - y0, 6),
                round(top - z, 6),
                note,
            ]
        )
        for pad in pads:
            net = actual[ref][str(pad[1])]
            if net.startswith("unconnected-"):
                assert not any(
                    str(first(item, "net")[1]).lstrip("/") == net
                    for tag in ("segment", "via")
                    for item in children(tree, tag)
                )
            if pad[2] != "thru_hole":
                continue
            x, y = transform(fp, first(pad, "at")[1:3])
            width = 1.15 if ref == "J1" else 2.0
            bodies.append(
                [
                    f"e20_{ref}_lead_{pad[1]}",
                    round(197 + x - 100 - width / 2, 6),
                    round(77 + y - 100 - width / 2, 6),
                    3.35,
                    width,
                    width,
                    3.15,
                    "Trim tail/solder protrusion<=3mm; J1 solder envelope<=1.15mm wide, others<=2mm; physical assembly unqualified",
                ]
            )
    assert actual == expected, (actual, expected)
    assert mounts == {"H1": [3, 7], "H2": [87, 7], "H3": [3, 22], "H4": [87, 22]}
    zones = children(tree, "zone")
    if routed:
        keep = [z for z in zones if children(z, "keepout")]
        planes = [z for z in zones if not children(z, "keepout")]
        assert len(keep) == 4 and len(planes) == 2
        assert {str(first(p, "layer")[1]) for p in planes} == {"In1.Cu", "In4.Cu"}
        assert all(first(p, "net")[1] == "/AGND" and children(p, "filled_polygon") for p in planes)
        for k in keep:
            assert set(first(k, "layers")[1:]) == copper
            assert all(
                first(first(k, "keepout"), tag)[1] == "not_allowed"
                for tag in ("tracks", "vias", "copperpour")
            )
        keepout_mounts = set()
        for k in keep:
            points = children(first(first(k, "polygon"), "pts"), "xy")
            assert len(points) == 32
            cx = sum(float(p[1]) for p in points) / 32
            cy = sum(float(p[2]) for p in points) / 32
            ref = next(r for r, at in mounts.items() if math.dist((cx - 100, cy - 100), at) < 1e-5)
            keepout_mounts.add(ref)
            for p, q in zip(points, points[1:] + points[:1]):
                px, py, qx, qy = float(p[1]), float(p[2]), float(q[1]), float(q[2])
                distance = abs((qx - px) * (py - cy) - (px - cx) * (qy - py)) / math.hypot(qx - px, qy - py)
                assert distance >= 3.75 - 1e-6
        assert keepout_mounts == set(mounts)
    return dict(
        revision="E20",
        pcb_sha256=sha(pcb),
        board=[
            "led_driver",
            197,
            77,
            6.5,
            91,
            27,
            1.6,
            "E20 LED/display driver; panel emitter boards/harness incomplete",
        ],
        mount_centers_layout_mm=[[197 + mounts[r][0], 77 + mounts[r][1]] for r in sorted(mounts)],
        mount_hole_mm=2.4,
        mount_boss_diameter_mm=7.2,
        insert_through_bore_mm=3.2,
        bodies=bodies,
        pcb_routed=routed,
        copper_layers=6,
        physical_fit_verified=False,
        full_led_display_system_complete=False,
        full_unit_power_budget_closed=False,
    )


def verify(run, expected, placed_only=False):
    pcb = ROOT / "led_driver.kicad_pcb"
    flags = [] if placed_only else ["--refill-zones", "--save-board", "--exit-code-violations"]
    run(
        "pcb",
        "drc",
        *flags,
        "--all-track-errors",
        "--schematic-parity",
        "--severity-all",
        "--format",
        "json",
        "-o",
        OUT / "drc.json",
        pcb,
    )
    report = json.loads((OUT / "drc.json").read_text())
    assert not report["violations"] and not report["schematic_parity"]
    assert placed_only or not report["unconnected_items"]
    packet = mechanical(pcb, expected, not placed_only)
    (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
    for name, layers in [
        ("top", "F.Cu,F.Fab,F.SilkS,Edge.Cuts"),
        ("bottom", "B.Cu,B.Fab,B.SilkS,Edge.Cuts"),
        ("ground", "In1.Cu,Edge.Cuts"),
        ("logic", "In2.Cu,Edge.Cuts"),
        ("logic-2", "In3.Cu,Edge.Cuts"),
        ("ground-2", "In4.Cu,Edge.Cuts"),
    ]:
        run(
            "pcb",
            "export",
            "svg",
            "--mode-single",
            "--page-size-mode",
            "2",
            "--exclude-drawing-sheet",
            "--layers",
            layers,
            "-o",
            OUT / (name + ".svg"),
            pcb,
        )
    tree = read_sexpr(pcb.read_text())
    iref_lengths = {}
    if not placed_only:
        for i in range(4):
            net = f"/IREF_{i}"
            segments = [s for s in children(tree, "segment") if first(s, "net")[1] == net]
            length = sum(
                math.dist(list(map(float, first(s, "start")[1:3])), list(map(float, first(s, "end")[1:3])))
                for s in segments
            )
            assert 0 < length < 15, (net, "IREF copper must stay local", length)
            iref_lengths[net.lstrip("/")] = round(length, 6)
    return dict(
        pcb_placed=True,
        pcb_routed=not placed_only,
        native_drc_violations=0,
        schematic_parity_issues=0,
        unconnected_items=len(report["unconnected_items"]),
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        saved_ground_plane_filled=not placed_only,
        saved_ground_plane_layers=["In1.Cu", "In4.Cu"] if not placed_only else [],
        copper_layers=6,
        mounting_holes=4,
        mounting_copper_keepouts=4 if not placed_only else 0,
        iref_copper_length_mm=iref_lengths,
        board_size_mm=[91, 27, 1.6],
    )
