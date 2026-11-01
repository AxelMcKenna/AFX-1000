"""Dimensioned source-bound feasibility drawing; SVG is not a fabrication drawing."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def main():
    pcb = ROOT / "repaired/power_p03.kicad_pcb"
    a = json.loads((OUT / "geometry.json").read_text())
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    assert sha(pcb) == a["candidate_pcb_sha256"]
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="830" viewBox="0 0 1200 830">',
        '<rect width="1200" height="830" fill="#fff"/>',
        "<style>text{font-family:Arial,sans-serif;fill:#162333} .small{font-size:15px} .body{font-size:18px}</style>",
    ]

    def text(x, y, value, size=18):
        lines.append(f'<text x="{x}" y="{y}" font-size="{size}">{value}</text>')

    text(35, 38, "U102 local thermal candidate / same-face capacitor repair", 27)
    text(35, 68, "Selected PCB 37fd6109… / native coordinates in mm / feasibility dimensions only", 18)
    x0, y0, scale = 55, 112, 27

    def xy(x, y):
        return x0 + (x - 118) * scale, y0 + (y - 114) * scale

    def rect(box, fill, stroke, dash=""):
        x, y = xy(box[0], box[1])
        lines.append(
            f'<rect x="{x}" y="{y}" width="{(box[2] - box[0]) * scale}" '
            f'height="{(box[3] - box[1]) * scale}" fill="{fill}" stroke="{stroke}" stroke-width="2" '
            f'stroke-dasharray="{dash}"/>'
        )

    for x in range(118, 136, 2):
        px, py = xy(x, 114)
        lines.append(f'<path d="M{px},{py}v405" stroke="#e7edf2"/>')
        text(px - 8, py - 8, str(x), 13)
    for y in range(114, 130, 2):
        px, py = xy(118, y)
        lines.append(f'<path d="M{px},{py}h459" stroke="#e7edf2"/>')
        text(px - 30, py + 5, str(y), 13)
    rect([120.55, 116.3, 129.95, 123.7], "none", "#65758b", "6 4")
    rect(a["tim_native_mm"], "#d9f3ec", "#277c6a")
    rect(a["metal_native_mm"], "#d7e6fa", "#315b91")
    # Actual native package body; native copper/terminal outlines remain in the PCB.
    rect([124.75, 118.5, 127.75, 121.5], "#f0c996", "#9c6228")
    for ref, dx, dy in [
        ("U102", -19, -10),
        ("C106", -36, 25),
        ("C113", -33, -12),
        ("C110", 8, 8),
        ("R110", -55, -10),
        ("R130", -38, 25),
        ("C109", 8, 20),
    ]:
        p = first(fps[ref], "at")
        px, py = xy(float(p[1]), float(p[2]))
        color = "#334e7c" if first(fps[ref], "layer")[1] == "F.Cu" else "#9b4e7e"
        lines.append(f'<circle cx="{px}" cy="{py}" r="4" fill="{color}"/>')
        text(px + dx, py + dy, ref + (" F" if color == "#334e7c" else " B"), 14)
    px, py = xy(124.925, 120.325)
    lines.append(f'<circle cx="{px}" cy="{py}" r="7.425" fill="white" stroke="#a22" stroke-width="2"/>')
    text(620, 123, "Actual construction", 22)
    for i, value in enumerate(
        [
            "LAND: native [121.75,117.5] to [128.75,122.5]",
            "7 × 5 mm metal; Z0 to5.28; 184.80 mm³",
            "TIM cut:9 × 7 mm; 64.26 mm³ collision solid",
            "Housing floor window:188.55,124.3 to197.95,131.7",
            "Native→housing transform:+68,+8",
            "9 direct EP +3 adjacent AGND barrels retained",
            "POWER_RUN/PG via .55/.20 inside field is a real void",
            "C106 F1210:2.90 mm assembled projection allocation",
            "C113 F0805 soft:1.60; C110 F0603:1.00 mm",
            "B-part markers show the three retained relocations",
            "Full collision test uses all507 native part records",
        ]
    ):
        text(620, 158 + i * 25, value, 16)
    text(45, 554, "SECTION / nominal matched assembly (mm; source face F)", 21)
    lines += [
        '<rect x="70" y="650" width="470" height="58" fill="#c6d0df" stroke="#315b91"/>',
        '<rect x="220" y="610" width="170" height="40" fill="#d7e6fa" stroke="#315b91"/>',
        '<rect x="200" y="592" width="210" height="18" fill="#d9f3ec" stroke="#277c6a"/>',
        '<rect x="70" y="568" width="470" height="24" fill="#e8dbc5" stroke="#8c6c43"/>',
    ]
    text(555, 590, "PCB underside6.5 nominal; matched6.3..6.7", 16)
    text(555, 616, "Land top5.28; nominal thermal gap1.22", 16)
    text(555, 642, "TIM collision top6.3 / lowest-board clearance screen", 16)
    text(555, 668, "Base upper plane0; plastic carrier gets local window", 16)
    text(
        45,
        746,
        "No isolation credit for solder mask; received pad compression/flatness/VIP/fill/cap/process must be verified.",
        17,
    )
    text(
        45,
        773,
        "107.30°C sensitivity assumes65°C local base +2°C allowance; neither is a measured bound. Thermal/stability flags FALSE.",
        17,
    )
    text(
        45,
        802,
        "Not to scale in Z. No canonical/frozen-base change. STEP/STL and7native-case report accompany this drawing.",
        16,
    )
    lines.append("</svg>")
    (OUT / "front-cell-drawing.svg").write_text("\n".join(lines) + "\n")
    # CPU-only raster preview of this simple SVG's explicit primitives.
    import re
    import xml.etree.ElementTree as ET

    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 830), "white")
    draw = ImageDraw.Draw(image)
    for node in ET.fromstring("\n".join(lines)):
        attr = node.attrib
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            x, y = float(attr.get("x", 0)), float(attr.get("y", 0))
            draw.rectangle(
                [x, y, x + float(attr["width"]), y + float(attr["height"])],
                fill=None if attr.get("fill") == "none" else attr.get("fill"),
                outline=attr.get("stroke"),
                width=int(attr.get("stroke-width", 1)),
            )
        elif tag == "circle":
            x, y, r = (float(attr[k]) for k in ["cx", "cy", "r"])
            draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=attr.get("fill"),
                outline=attr.get("stroke"),
                width=int(attr.get("stroke-width", 1)),
            )
        elif tag == "path":
            match = re.fullmatch(r"M([0-9.]+),([0-9.]+)([hv])([0-9.]+)", attr["d"])
            assert match
            x, y, axis, length = match.groups()
            x, y, length = float(x), float(y), float(length)
            draw.line(
                [x, y, x + (length if axis == "h" else 0), y + (length if axis == "v" else 0)],
                fill=attr["stroke"],
            )
        elif tag == "text":
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", int(attr["font-size"]))
            draw.text((float(attr["x"]), float(attr["y"])), node.text, font=font, fill="#162333", anchor="ls")
    image.save(OUT / "front-cell-drawing.png")
    (OUT / "front-cell-drawing.json").write_text(
        json.dumps(
            dict(
                source_sha256={
                    str(p.relative_to(REPO)): sha(p)
                    for p in [Path(__file__).resolve(), pcb, OUT / "geometry.json"]
                },
                fabrication_drawing=False,
                physical_fit_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
