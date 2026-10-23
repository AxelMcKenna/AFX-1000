#!/usr/bin/env python3
"""A04/E07/E18 internal envelopes, ports, and panel board mounting data.

Envelope reserves are deliberately larger than part bodies. Board outlines are
placement designs except the E07 output and E18 input-hub boards. See components.md for remaining gates.
"""

import hashlib
import json
from pathlib import Path

from . import generate as panel

OUT = Path(__file__).resolve().parent / "generated"
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "electronics/output_stage"
OUTPUT_PLACEMENT = json.loads((OUTPUT_ROOT / "generated/placement.json").read_text())
assert (
    OUTPUT_PLACEMENT["pcb_sha256"]
    == hashlib.sha256((OUTPUT_ROOT / "output_stage.kicad_pcb").read_bytes()).hexdigest()
), "Regenerate/check output PCB placement before CAD"
CONTROL_ROOT = Path(__file__).resolve().parents[1] / "electronics/control_inputs"
CONTROL_PLACEMENT = json.loads((CONTROL_ROOT / "generated/placement.json").read_text())
assert (
    CONTROL_PLACEMENT["pcb_sha256"]
    == hashlib.sha256((CONTROL_ROOT / "control_inputs.kicad_pcb").read_bytes()).hexdigest()
), "Regenerate/check control input PCB before CAD"

# [id, x, y, z, width, depth, height, role]. Positions are minimum corners.
BOARDS = [
    ["dsp_carrier", 30, 42, 6.5, 150, 65, 1.6, "placement"],
    OUTPUT_PLACEMENT["board"],
    ["power_carrier", 207, 105, 6.5, 78, 38, 1.6, "placement"],
    ["meter_board", 40, 17, 27, 65, 21, 1.6, "placement"],
    ["bpm_board", 146, 21, 25.4, 28, 20, 1.6, "placement"],
    ["trill_craft", 82, 123.5, 23, 52, 21, 1.6, "manufacturer outline"],
    ["settings_board", 297, 18.5, 28.7, 20, 17, 1.6, "placement"],
    ["release_select_board", 306, 45.5, 28.7, 20, 17, 1.6, "placement"],
    CONTROL_PLACEMENT["board"],
]

# Component keep-outs, not detailed STEP models.
ENVELOPES = [
    ["seed3", 53, 43, 18.2, 51, 18, 4.85, "manufacturer outline plus top components"],
    ["seed_socket_rear", 53, 43, 8.1, 51, 2.6, 10.1, "socket reserve"],
    ["seed_socket_front", 53, 58.4, 8.1, 51, 2.6, 10.1, "socket reserve"],
    ["power_components", 209, 107, 8.1, 74, 34, 12, "unrouted component reserve"],
    ["trill_components", 82, 123.5, 24.6, 52, 21, 6.4, "connector/component reserve"],
    ["bpm_digits", 148.75, 24, 27, 22.5, 14, 8.5, "three SA36-11YWA bodies"],
    ["settings_switch", 302.5, 23.75, 30.3, 9, 6.5, 3.6, "JS202011CQN reserve"],
    ["release_select_switch", 309.5, 50, 30.3, 13, 8, 3.6, "JS203011SCQN terminal reserve"],
    ["angle_sensor_board", 299.7, 72, 14, 1.6, 20, 20, "custom AS5600 board reserve"],
    ["angle_sensor", 301.3, 79.5, 21.5, 1.7, 5, 5, "SOIC sensor placement reserve"],
]

for c in panel.CONTROLS:
    if c["kind"] == "knob":
        ENVELOPES.append(
            [
                c["id"] + "_pot",
                c["x"] - 8,
                c["y"] - 8,
                21.5,
                16,
                16,
                12.5,
                "PTV09A-6 body and terminal reserve",
            ]
        )
    elif c["kind"] in ("button", "sector"):
        x, y = panel.point(c, 43.5, (c["a"] + c["b"]) / 2) if c["kind"] == "sector" else (c["x"], c["y"])
        ENVELOPES.append(
            [c["id"] + "_switch", x - 4, y - 5, 27.2, 8, 10, 4.3, "B3F-1000 body and terminal reserve"]
        )
        ENVELOPES.append(
            [
                c["id"] + "_switch_leads",
                x - 4,
                y - 5,
                23.2,
                8,
                10,
                4.0,
                "conservative B3F lead reserve: 3.5mm nominal plus 0.5mm allowance below switch base",
            ]
        )

CONTROL_OBSTACLES = list(ENVELOPES)
CONTROL_ENVELOPES = CONTROL_PLACEMENT["bodies"]
STATIONARY_ENVELOPES = list(ENVELOPES) + CONTROL_ENVELOPES
OUTPUT_ENVELOPES = OUTPUT_PLACEMENT["bodies"]
ENVELOPES.extend(OUTPUT_ENVELOPES + CONTROL_ENVELOPES)
FLOOR_POCKETS = [OUTPUT_PLACEMENT["floor_pocket"]]
DAUGHTER_MOUNTS = [
    ["control_input_hub", x, y, 8.1, 12.1, 2.4] for x, y in CONTROL_PLACEMENT["mount_centers_layout_mm"]
]


def mount_diameter(m):
    return 7.2 if m[0] == "audio_carrier" else 6


# Mounts for lower carrier boards. [id,x,y,seat_z,pilot_diameter]
MOUNTS = []
for b in BOARDS[:3]:
    id, x, y, z, w, d, _, _ = b
    for px in (x + 4, x + w - 4):
        for py in (y + 4, y + d - 4):
            MOUNTS.append([id, px, py, z, 3.2 if id == "audio_carrier" else 2.0])
for x in (306, 326):
    for y in (69, 102):
        MOUNTS.append(["lever", x, y, 7, 2.5])
for x, y in ((193, 78), (295, 78), (234, 28)):
    MOUNTS.append(["scene_board", x, y, 25.6, 2.0])

# Rear panel axes are X and Z. [id,kind,x,z,width,height,inside_depth]
# RCA / service entries remain interface reserves pending exact supplier parts.
PORTS = [
    ["input_rca_l", "round", 40, 13.2, 8.2, 8.2, 17],
    ["input_rca_r", "round", 56, 13.2, 8.2, 8.2, 17],
    ["input_ts_l", "round", 74, 13.2, 9.8, 9.8, 28],
    ["input_ts_r", "round", 94, 13.2, 9.8, 9.8, 28],
    ["output_rca_l", "round", 136, 13.2, 8.2, 8.2, 17],
    ["output_rca_r", "round", 152, 13.2, 8.2, 8.2, 17],
    ["output_ts_l", "round", 182, 13.2, 9.8, 9.8, 28],
    ["output_ts_r", "round", 202, 13.2, 9.8, 9.8, 28],
    ["hardware_bypass", "rect", 223, 16, 9, 14, 18],
    ["line_mode", "rect", 241, 16, 9, 7, 18],
    ["micro_sd", "rect", 118, 16, 14, 3, 18],
    ["service_usb", "rect", 263, 16, 12, 8, 25],
    ["dc_input", "round", 288, 16, 8.2, 8.2, 20],
    ["power_switch", "rect", 302, 16, 9, 14, 18],
]


def overlap(a, b, margin=0):
    # [x,y,z,w,d,h]; zero means touching, negative means separation.
    return all(min(a[i] + a[i + 3], b[i] + b[i + 3]) - max(a[i], b[i]) > -margin for i in range(3))


def port_box(p):
    id, kind, x, z, w, h, depth = p
    diameter = 19 if "_ts_" in id else 12 if "_rca_" in id else w
    height = 19 if "_ts_" in id else 12 if "_rca_" in id else h
    return [x - diameter / 2, 0, z - height / 2, diameter, depth, height]


def validate():
    all_parts = [(b[0], b[1:7]) for b in BOARDS + ENVELOPES]
    all_parts += [(p[0], port_box(p)) for p in PORTS]
    collisions = []
    for i, (name, box) in enumerate(all_parts):
        x, y, z, w, d, h = box
        assert x >= 2.8 and x + w <= panel.W - 2.8 and y >= 0 and y + d <= panel.D - 2.8 and z >= 1.6, name
        if z < 2.8:
            pocket = FLOOR_POCKETS[0]
            _, px, py, pw, pd, pz = pocket
            assert px + 1 <= x and x + w <= px + pw - 1 and py + 1 <= y and y + d <= py + pd - 1 and z > pz, (
                name
            )
        for other, other_box in all_parts[i + 1 :]:
            if overlap(box, other_box, margin=0.01):
                # Parts exactly touching at their mounting plane are intended.
                if overlap(box, other_box):
                    collisions.append((name, other))
    if collisions:
        raise ValueError(f"Internal component reserve collisions: {collisions}")
    for name, box in all_parts:
        for p in panel.FASTENERS:
            boss = [p[0] - 4.2, p[1] - 4.2, 2.8, 8.4, 8.4, 31.2]
            assert not overlap(box, boss), f"{name} hits shell boss {p}"
        for m in MOUNTS:
            _, x, y, seat, _ = m
            diameter = mount_diameter(m)
            assert not overlap(
                box, [x - diameter / 2, y - diameter / 2, 2.8, diameter, diameter, seat - 2.8]
            ), f"{name} hits carrier/lever mount {(x, y)}"
    for p in PORTS:
        assert 6 < p[3] - p[5] / 2 and p[3] + p[5] / 2 < 30, p[0]
    print(
        f"{len(all_parts)} internal/port reserves: no bounding-box intersections or shell-boss intersections."
    )
    return dict(
        revision="A04/E07/E18",
        scope="conservative component/lead/port reserves and actual E07/E18 footprint placement",
        parts_checked=len(all_parts),
        intersections=[],
        output_placement_sha256=hashlib.sha256(
            (OUTPUT_ROOT / "generated/placement.json").read_bytes()
        ).hexdigest(),
        output_pcb_routed=OUTPUT_PLACEMENT["pcb_routed"],
        output_physical_fit_verified=False,
        control_placement_sha256=hashlib.sha256(
            (CONTROL_ROOT / "generated/placement.json").read_bytes()
        ).hexdigest(),
        control_pcb_routed=CONTROL_PLACEMENT["pcb_routed"],
        control_physical_fit_verified=False,
        control_carrier_mounting="4mm spacers; matching holes/keepouts still required on unrouted processor carrier",
        excluded=[
            "mechanism sweep and base pocket (checked separately in CAD)",
            "wiring beyond header reserves",
            "components outside named reserves and unfinished system boards",
            "thermal performance",
        ],
    )


def rear_svg():
    items = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="354mm" height="75mm" viewBox="0 0 354 75">',
        "<title>A03 standalone rear panel — provisional connector apertures</title>",
        '<rect width="354" height="75" fill="#101214"/>',
        '<g font-family="Arial,Helvetica,sans-serif" fill="#d5dadd">',
        '<text x="10" y="10" font-size="4">RMX / STANDALONE REAR I/O — A03</text>',
        '<g transform="translate(10 52) scale(1 -1)">',
        '<rect width="334" height="36" rx="5" fill="#25292c" stroke="#69737b" stroke-width="0.4"/>',
        '<rect x="12" y="3" width="310" height="30" fill="#191c1f" stroke="#59646a" stroke-width="0.25"/>',
    ]
    for id, kind, x, z, w, h, _ in PORTS:
        if kind == "round":
            items.append(
                f'<circle cx="{x}" cy="{z}" r="{w / 2}" fill="#090b0c" stroke="#70d4c9" stroke-width="0.3"/>'
            )
        else:
            items.append(
                f'<rect x="{x - w / 2}" y="{z - h / 2}" width="{w}" height="{h}" fill="#090b0c" stroke="#70d4c9" stroke-width="0.3"/>'
            )
    for x in (20, 314):
        for z in (8, 28):
            items.append(f'<circle cx="{x}" cy="{z}" r="1.7" fill="#101214"/>')
    items.append("</g>")
    for x, label in [
        (58, "INPUT L / R"),
        (166, "OUTPUT L / R"),
        (118, "SD"),
        (223, "BYPASS"),
        (241, "LEVEL"),
        (263, "SERVICE"),
        (288, "DC"),
        (302, "POWER"),
    ]:
        items.append(f'<text x="{10 + x}" y="24" text-anchor="middle" font-size="2.2">{label}</text>')
    items.append(
        '<text x="10" y="64" font-size="2.8" fill="#e7b46b">Standalone stereo line I/O · normally closed dry bypass · external DC power</text>'
    )
    items.append(
        '<text x="10" y="70" font-size="2.4">RCA/service/power holes are interface reserves. Supplier drawings and analog gain design remain open.</text>'
    )
    return "\n".join(items + ["</g></svg>"])


def main():
    result = validate()
    OUT.mkdir(exist_ok=True)
    (OUT / "components.scad").write_text(
        "// Generated by ../standalone.py; do not edit.\n"
        + "\n".join(
            f"{name} = {json.dumps(value)};"
            for name, value in [
                ("boards", BOARDS),
                ("envelopes", ENVELOPES),
                ("board_mounts", MOUNTS),
                ("rear_ports", PORTS),
                ("stationary_envelopes", STATIONARY_ENVELOPES),
                ("output_envelopes", OUTPUT_ENVELOPES),
                ("control_envelopes", CONTROL_ENVELOPES),
                ("control_obstacles", CONTROL_OBSTACLES),
                ("daughterboard_mounts", DAUGHTER_MOUNTS),
                ("floor_pockets", FLOOR_POCKETS),
                ("port_envelopes", [[p[0], *port_box(p)] for p in PORTS]),
            ]
        )
        + "\n"
    )
    (OUT / "internal-clearance.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / "rear-layout.svg").write_text(rear_svg())


if __name__ == "__main__":
    main()
