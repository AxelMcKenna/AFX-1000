"""A07 housing reserves from the checked E23 inlet/protection PCB.

Supplier body bounds, connector/harness classes and fixing dimensions remain
conditional assembly allocations. They do not establish physical fit.
"""

import hashlib
import json
from pathlib import Path

from ..electronics.common.sexpr import children, first, read_sexpr
from ..electronics.output_stage.check_placement import transform

ROOT = Path(__file__).resolve().parents[1] / "electronics/input_protection"
DATUM = (248, 1.4, 7.9)


def packet():
    pcb = ROOT / "input_protection.kicad_pcb"
    placement = json.loads((ROOT / "generated/placement.json").read_text())
    assert placement["revision"] == "E23" and placement["pcb_routed"]
    assert placement["pcb_sha256"] == hashlib.sha256(pcb.read_bytes()).hexdigest()
    tree = read_sexpr(pcb.read_text())
    x0, y0, z0 = DATUM
    top = z0 + 1.6
    bodies, holes = [], []
    poses = {}
    for footprint in children(tree, "footprint"):
        ref = next(p[2] for p in children(footprint, "property") if p[1] == "Reference")
        poses[ref] = [float(v) for v in first(footprint, "at")[1:]]
        for pad in children(footprint, "pad"):
            if pad[2] not in ("thru_hole", "np_thru_hole") or ref.startswith("H"):
                continue
            x, y = transform(footprint, first(pad, "at")[1:3])
            x, y = x0 + x - 100, y0 + y - 100
            height = 4.15 if ref == "J1" else 1.15 if ref == "S1" else 3.15
            width = 1.1 if ref == "S1" else 2.6 if ref == "J1" else 2
            number = str(pad[1]) or str(len(holes))
            holes.append([ref, number, round(x, 6), round(y, 6)])
            bodies.append(
                [
                    f"e23_{ref}_lead_{number}",
                    x - width / 2,
                    y - width / 2,
                    z0 - height,
                    width,
                    width,
                    height,
                    "Conditional locating-pin or trimmed lead/solder bound; actual assembly unqualified",
                ]
            )
    assert poses["J1"][2] == poses["S1"][2] == 180
    jack_x, jack_y = x0 + poses["J1"][0] - 100, y0 + poses["J1"][1] - 100
    switch_x, switch_y = x0 + poses["S1"][0] - 100, y0 + poses["S1"][1] - 100
    face_y = jack_y - 13.7
    assert abs(face_y - (-1.6)) < 1e-6, "Jack mating face must reach the rear plate outer plane"
    assert abs(jack_x - 288) < 1e-6 and abs(switch_x - 302) < 1e-6
    switch_tip_y = switch_y - 3.8
    assert -1.9 <= switch_tip_y <= -0.8, "Switch actuator is too recessed for the rear access allocation"
    for component in placement["bodies"]:
        ref = component["reference"]
        if ref in ("J1", "S1"):
            continue
        x, y, w, d = component["courtyard_relative_mm"]
        side = component["side"]
        expand = 0.5 if ref.startswith("J") else 0
        height = component["height_allocation_mm"] + (0.15 if side == "B" else 0.31)
        bodies.append(
            [
                f"e23_{ref}",
                x0 + x - expand,
                y0 + y - expand,
                z0 - height if side == "B" else top,
                w + 2 * expand,
                d + 2 * expand,
                height,
                "Actual footprint courtyard; allocated height/PCB seat and header/harness expansion; part qualification open",
            ]
        )
    # PJ-102AH drawing: nominal 9 x 14.4 x 11 mm, axis 6.5 mm above seat,
    # front-to-terminal-3 10.7 mm and terminal-1 another 3 mm behind it.
    # The larger box includes dimensional/seat allocations. A rectangle is
    # needed in the rear plate because the housing face is rectangular.
    bodies.extend(
        [
            [
                "e23_J1",
                jack_x - 4.9,
                face_y - 0.3,
                top,
                9.8,
                15.1,
                12.31,
                "PJ-102AH body/seat allocation; nominal mating face at rear plate outer plane -1.6; exact plug/fit unqualified",
            ],
            [
                "e23_S1",
                switch_x - 4.8,
                switch_y - 2.05,
                top,
                9.6,
                4.1,
                4.31,
                "JS102011SAQN body allocation; supplier dimensions/assembly require physical qualification",
            ],
            [
                "e23_S1_actuator",
                switch_x - 3.25,
                switch_y - 4.3,
                top,
                6.5,
                2.25,
                4.31,
                "Conservative full travel/height reserve through rear slot; tactile access and exact actuator tolerances unqualified",
            ],
        ]
    )
    mounts = []
    for ref, (x, y) in sorted(placement["mounts_relative_mm"].items()):
        x, y = x0 + x, y0 + y
        mounts.append([x, y])
        bodies.append(
            [
                f"e23_{ref}_head",
                x - 2.8,
                y - 2.8,
                top,
                5.6,
                5.6,
                2.31,
                "M2 head/washer OD<=5.6 and height<=2 plus .31 seat allowance; fixing/insert engagement unqualified",
            ]
        )
    outline = placement["outline_relative_mm"]
    return dict(
        revision="A07/E23",
        pcb_sha256=placement["pcb_sha256"],
        board=["input_power", *DATUM, 64, 44, 1.6, "E23 routed input/protection PCB with rear-right relief"],
        outline_relative_mm=outline,
        bodies=[[row[0], *[round(v, 6) for v in row[1:7]], row[7]] for row in bodies],
        board_pieces=[
            ["input_power_rear", x0, y0, z0, 59, 2, 1.6],
            ["input_power_main", x0, y0 + 2, z0, 64, 37, 1.6],
            ["input_power_front_right", x0 + 33, y0 + 39, z0, 31, 5, 1.6],
        ],
        mount_centers_layout_mm=mounts,
        mount_hole_mm=2.2,
        mount_boss_diameter_mm=7.2,
        insert_through_bore_mm=3.2,
        pcb_routed=True,
        copper_layers=4,
        jack_axis_layout_mm=[288, -1.6, 16],
        rear_openings=[
            ["dc_input", "rect", 288, 15.5, 10.4, 13.4, 20],
            ["power_switch", "rect", 302, 11.65, 7.2, 5.5, 18],
        ],
        nominal_jack_front_to_terminal1_mm=13.7,
        nominal_jack_mating_face_y_mm=round(face_y, 6),
        nominal_switch_tip_y_mm=round(switch_tip_y, 6),
        rear_plate_outer_y_mm=-1.6,
        supplier_drawing_urls=[
            "https://www.sameskydevices.com/product/resource/pj-102ah.pdf",
            "https://www.littelfuse.com/assetdocs/littelfuse-c-k-slide-js-series-datasheet?assetguid=aba42b08-0d2c-423b-813d-a2faa5a3bb14",
        ],
        drawing_review_scope="PJ mechanical page visually reviewed; JS primary drawing text and native footprint geometry reviewed; height/travel tolerances remain allocated",
        physical_fit_verified=False,
        full_unit_power_budget_closed=False,
    )
