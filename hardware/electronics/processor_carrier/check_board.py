"""Independent E19 native-PCB and conditional component-envelope checks."""

import json
import math
from pathlib import Path

from ..common.reports import sha
from ..common.sexpr import children, first, read_sexpr
from ..output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def mechanical(pcb, expected):
    tree = read_sexpr(pcb.read_text())
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    corners = {
        tuple(map(float, first(line, tag)[1:3]))
        for line in children(tree, "gr_line")
        for tag in ("start", "end")
    }
    assert corners == {(100, 100), (250, 100), (250, 165), (100, 165)}
    assert {str(first(z, "layer")[1]) for z in children(tree, "zone")} == {"In1.Cu"}
    zone = children(tree, "zone")[0]
    assert str(first(zone, "net")[1]) == "/AGND" and children(zone, "filled_polygon")
    actual, mounts, bodies = {}, {}, []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pads = children(fp, "pad")
        if ref.startswith("H"):
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole"
            assert float(first(pads[0], "drill")[1]) == 2.4
            x, y = transform(fp, first(pads[0], "at")[1:3])
            mounts[ref] = [round(x - 100, 6), round(y - 100, 6)]
            x, y = 30 + x - 100, 42 + y - 100
            if int(ref[1:]) <= 4:
                bodies.append(
                    [
                        f"e19_{ref}_head",
                        x - 2.8,
                        y - 2.8,
                        8.1,
                        5.6,
                        5.6,
                        2.0,
                        "M2 head/washer OD<=5.6 and height<=2; insert engagement/process qualification open",
                    ]
                )
            else:
                bodies.append(
                    [
                        f"e19_{ref}_lower_fixing",
                        x - 2.25,
                        y - 2.25,
                        4.35,
                        4.5,
                        4.5,
                        2.15,
                        "Daughter spacer lower head/nut OD<=4.5, projection<=2mm plus .15 seat allowance; exact attachment unselected",
                    ]
                )
            continue
        actual[ref] = {str(p[1]): str(first(p, "net")[1]).lstrip("/") for p in pads}
        if ref == "U1":
            at = first(fp, "at")
            assert all(
                math.isclose(float(a), b, abs_tol=1e-6) for a, b in zip(at[1:4], (159.63, 145.98, 270))
            )
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        bounds = courtyard(fp, side + ".CrtYd")
        expand = 0.5 if ref.startswith("J") else 0
        x0, y0, x1, y1 = bounds[0] - expand, bounds[1] - expand, bounds[2] + expand, bounds[3] + expand
        assert 100 <= x0 < x1 <= 250 and 100 <= y0 < y1 <= 165, (ref, bounds)
        if ref == "U1":
            z, top = 8.1, 25.3
            note = "Seed3 + two SSW-120-02-G-S sockets: whole assembly reserve, including dimensional/seat allowance; manufacturer geometry only, physical stack unverified"
        elif side == "B":
            z, top = 4.85, 6.5
            note = "Bottom SMD <=1.5mm including solder plus .15mm low-seat allowance; exact MPN qualification open"
        else:
            z = 8.1
            height = 11 if ref.startswith("J") else 1.5 if ref.startswith("C") else 0.9
            top = z + height + 0.31
            note = "Header/harness<=11mm and XY courtyard+.5; SMD class height limit plus PCB/seat .31mm. Exact parts and physical fit unqualified"
        bodies.append(
            [
                f"e19_{ref}",
                round(30 + x0 - 100, 6),
                round(42 + y0 - 100, 6),
                z,
                round(x1 - x0, 6),
                round(y1 - y0, 6),
                round(top - z, 6),
                note,
            ]
        )
        for pad in pads:
            if pad[2] != "thru_hole":
                continue
            x, y = transform(fp, first(pad, "at")[1:3])
            bodies.append(
                [
                    f"e19_{ref}_lead_{pad[1]}",
                    round(30 + x - 101, 6),
                    round(42 + y - 101, 6),
                    3.35,
                    2,
                    2,
                    3.15,
                    "Trim socket/header tails including solder to<=3mm; .15 low-seat allowance",
                ]
            )
        if ref == "U1":
            for pad in pads[15:19]:
                net = str(first(pad, "net")[1]).lstrip("/")
                assert net.startswith("unconnected-")
                assert not any(
                    str(first(item, "net")[1]).lstrip("/") == net
                    for kind in ("segment", "via")
                    for item in children(tree, kind)
                )
    assert actual == expected, (actual, expected)
    assert mounts == {
        "H1": [4, 4],
        "H2": [146, 4],
        "H3": [4, 61],
        "H4": [146, 61],
        "H5": [83, 5],
        "H6": [139, 5],
        "H7": [83, 51],
        "H8": [139, 51],
    }
    # Provision for a right-facing USB plug/strain relief. This is a clearance
    # allocation, not a selected pigtail or an electrically approved service port.
    bodies.append(
        [
            "e19_usb_plug",
            92.55,
            90,
            20,
            25,
            13,
            10,
            "Right-facing USB plug+strain-relief allocation; exact cable, internal route and partial-power behavior unqualified",
        ]
    )
    return dict(
        revision="E19",
        pcb_sha256=sha(pcb),
        board=["dsp_carrier", 30, 42, 6.5, 150, 65, 1.6, "E19 routed processor/knob carrier"],
        mount_centers_layout_mm=[[30 + mounts[f"H{i}"][0], 42 + mounts[f"H{i}"][1]] for i in range(1, 5)],
        daughter_mount_centers_layout_mm=[
            [30 + mounts[f"H{i}"][0], 42 + mounts[f"H{i}"][1]] for i in range(5, 9)
        ],
        mount_hole_mm=2.4,
        mount_boss_diameter_mm=7.2,
        insert_through_bore_mm=3.2,
        insert="CNC Kitchen M2 x 3mm OD3.6; through bore; M2x4 board screw; physical engagement/process unqualified",
        bodies=bodies,
        pcb_routed=True,
        physical_fit_verified=False,
        complete_control_board=False,
        firmware_profile="external",
        limits=[
            "E19 only; complete analog/power/LED/sensor/SD placement unfinished",
            "Socket, pigtail, harness, passive, fastener and assembly bounds require physical qualification",
            "ADC acquisition/accuracy, signal integrity, 3.3V loads and USB partial power unverified",
        ],
    )


def verify(run, expected):
    pcb = ROOT / "processor_carrier.kicad_pcb"
    run(
        "pcb",
        "drc",
        "--refill-zones",
        "--save-board",
        "--all-track-errors",
        "--schematic-parity",
        "--severity-all",
        "--format",
        "json",
        "--exit-code-violations",
        "-o",
        OUT / "drc.json",
        pcb,
    )
    report = json.loads((OUT / "drc.json").read_text())
    assert not report["violations"] and not report["unconnected_items"] and not report["schematic_parity"]
    packet = mechanical(pcb, expected)
    tree = read_sexpr(pcb.read_text())
    assert children(tree, "segment") and children(tree, "via")
    (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
    for name, layers in [
        ("top", "F.Cu,F.Fab,F.SilkS,Edge.Cuts"),
        ("bottom", "B.Cu,B.Fab,Edge.Cuts"),
        ("logic", "In2.Cu,Edge.Cuts"),
        ("ground", "In1.Cu,Edge.Cuts"),
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
    return dict(
        pcb_placed=True,
        pcb_routed=True,
        pcb_drc_passed=True,
        native_drc_violations=0,
        schematic_parity_issues=0,
        unconnected_items=0,
        saved_ground_plane_filled=True,
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        mounting_holes=8,
        board_size_mm=[150, 65, 1.6],
    )
