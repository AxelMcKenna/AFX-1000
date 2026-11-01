"""Dimensioned native-vector drawing and manufacturing schedule."""

import json
from html import escape

from .generate import OUT, corner_disks, load, points, seat


def main():
    d = load()
    d["assembled_board_bottom_z_mm"] = json.loads((OUT / "geometry.json").read_text())[
        "effective_measured_plane_inputs"
    ]
    d["assembled_terminal_top_override_z_mm"] = json.loads((OUT / "geometry.json").read_text()).get(
        "effective_terminal_top_override_z_mm", {}
    )
    s = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1740" viewBox="0 0 1400 1740"><rect width="1400" height="1740" fill="white"/>',
        "<style>text{font-family:Arial,sans-serif;fill:#17202a;font-size:16px} .title{font-size:27px;font-weight:bold} .small{font-size:14px}</style>",
    ]

    def text(x, y, t, cls=""):
        s.append(f'<text x="{x}" y="{y}" class="{cls}">{escape(t)}</text>')

    def line(x1, y1, x2, y2, color="#17202a", width=1):
        s.append(f'<path d="M{x1},{y1}L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}"/>')

    text(38, 43, "AFX-A12-R01 — isolated quiet-return bars and retainers", "title")
    text(
        38,
        72,
        "DESIGN CANDIDATE • dimensions mm • measured terminal planes set bar rise and PEEK seat • no forced bend",
    )
    text(
        38,
        100,
        "C11000 annealed certified copper • MCAM Ketron1000 natural unfilled PEEK • no fabrication/physical approval",
    )
    ox, oy, scale = 100, 145, 15

    def xy(x, y):
        return ox + (x - 125) * scale, oy + (y - 106) * scale

    def rect(x, y, w, h, color, fill="none"):
        xx, yy = xy(x, y)
        s.append(
            f'<rect x="{xx}" y="{yy}" width="{w * scale}" height="{h * scale}" fill="{fill}" stroke="{color}"/>'
        )

    def circ(x, y, r, color, fill="none"):
        xx, yy = xy(x, y)
        s.append(f'<circle cx="{xx}" cy="{yy}" r="{r * scale}" fill="{fill}" stroke="{color}"/>')

    rect(125, 108.5, 39, 45.25, "#566573", "#f4f6f7")
    rect(168, 108, 17, 45, "#566573", "#f4f6f7")
    for x, y, r in [(153, 123.75, 5.25), (154.5, 145.5, 8.25)]:
        circ(x, y, r, "#7d6608", "#fcf3cf")
    circ(167, 149, 4.2, "#a93226")
    colors = {"ANA": "#b85c24", "DIG": "#2874a6"}
    for name in d["paths"]:
        pp = points(d, name)
        color = colors[name]
        for a, b in zip(pp, pp[1:]):
            xx, yy = xy(a[0], a[1])
            xxx, yyy = xy(b[0], b[1])
            line(xx, yy, xxx, yyy, color, 6 * scale)
        for q in corner_disks(d, name):
            circ(q[0], q[1], q[3] / 2, color, color)
        for q in (pp[0], pp[-1]):
            circ(q[0], q[1], 5, color, color)
            circ(q[0], q[1], 2, "#17202a", "white")
        for x, y, z in pp:
            xx, yy = xy(x, y)
            s.append(f'<circle cx="{xx}" cy="{yy}" r="3" fill="white"/>')
        cx, cy = d["retainers"]["locations"][name]
        rect(cx - 2, cy - 7, 4, 14, "#239b56")
        for off in (-5.35, 5.35):
            circ(cx, cy + off, 0.9, "#17202a")
    text(1030, 165, "WORLD XY DATUM TABLE")
    yy = 195
    for name in d["paths"]:
        text(1030, yy, name + " centerline / bottom Z")
        yy += 25
        for x, y, z in points(d, name):
            text(1030, yy, f"({x:g}, {y:g})  Z{z:.4f}", "small")
            yy += 23
        yy += 16
    text(1030, 530, "Bare Cu section:6.0±0.10×3.5±0.05", "small")
    text(1030, 554, "Land Ø10±0.10 / hole Ø4±0.05", "small")
    text(1030, 578, "Plating adds≤0.020 overall envelope", "small")
    text(1030, 602, "PEEK post centres X166", "small")
    text(1030, 626, "Y113 /133.125", "small")
    text(1030, 650, "Copper ramps: ANA X150..173", "small")
    text(1030, 674, "DIG X141..173", "small")
    text(1030, 698, "Landing faces are flat at real studs", "small")
    text(
        100,
        892,
        "PLAN: brown ANA / blue DIG. Yellow=actual capacitor courtyard outlines; red=lidboss reserve; green=retainers.",
    )
    text(
        100,
        918,
        "XY drawing is an interface view, not a fabricated PCB drawing. Native collision receipt binds actual board revisions.",
    )
    # Retainer section through X; horizontal screw-bearing cap top is intentional.
    x0, y0, k = 190, 1220, 24
    name = "ANA"
    r = d["retainers"]
    cx, cy = r["locations"][name]
    left, right = 164, 168
    zleft = seat(d, name, left)
    zright = seat(d, name, right)
    cap_top = zright + 3.8 + 1.6

    def poly(coords, fill):
        points_attr = " ".join(f"{x0 + (x - 162) * k},{y0 - (z - 8.7) * k}" for x, z in coords)
        s.append(f'<polygon points="{points_attr}" fill="{fill}" stroke="#17202a"/>')

    poly([(164, 8.7), (168, 8.7), (168, zright - 0.05), (164, zleft - 0.05)], "#e8daaa")
    poly([(163, zleft), (169, zright), (169, zright + 3.5), (163, zleft + 3.5)], "#b85c24")
    poly([(164, zleft + 3.8), (168, zright + 3.8), (168, cap_top), (164, cap_top)], "#e8daaa")
    line(x0 + 4 * k, y0, x0 + 4 * k, y0 + 8.7 * k, "#b7950b", 3 * k)
    text(
        40,
        972,
        "RETENTION SECTION: sloped seat/cap underside, flat upper screw-bearing face; illustrative X section",
    )
    text(500, 1005, "Head:4.00±0.05 X ×14.00±0.05 Y; lower faceZ8.70")
    text(500, 1035, "Stem:Ø3.00±0.05; M2×0.4 ≥4.5 usable; Ø1.6 drill5.8 frombase")
    text(500, 1065, "Channel:7.40±0.05 Y; seat0.05 below measured copper underside")
    text(500, 1095, "Cap:minimum1.60 thick; underside bar-top clearance0.30 nominal")
    text(500, 1125, "Required allocated cap gap≥0.15 after full tolerance/measurement stack")
    text(500, 1155, "Cap holesØ1.8 atY±5.35; post M1.6×0.35 ≥4 usable,drill5.2")
    text(500, 1185, "Retainer height and slope must match measured assembled terminal planes")
    rows = [
        "BAR: machine from certified6.35mm C11000/O60 plate; minimum normal Cu area20mm² at all necks/ramps. R3 full-depth turns;edge break≤0.10,no hole countersinks.",
        "FINISH: APT bright tin,ASTM B545ClassB ≥5.08µm,process maximum10µm/face; compatibility/whisker/life approval open. Deburr before plating.",
        "JOINT: Accu SPP-M3-8-A2 +HPW-M3-A2 washer0.55(+0/−0.10); head maxØ6/H2.52. Trial0.4Nm±10%,below0.5Nm terminal limit.",
        "M2BASE: Accu SPK-M2-10-A2,metal Ø2.4/Ø4.8 90°undersideCSK through6.2plate; floor holeØ3.5 ONLY; PEEK carries no chassis current.",
        "CAP: PTS A91201605 M1.6×5,A2. Trial cap0.02Nm/base0.05Nm are project trials,not approved PEEK torques. Verify creep/pullout.",
        "ASSEMBLY: use temporary torque-holding fixture. Never transmit arbitrary wrench torque into the3mm PEEK stem or SMT stud solder.",
        "MEASURE: each complete terminal joint≤0.35mΩ,bar≤0.1mΩ,PCB access≤1mΩ allocations; complete return≤2mΩ. No DC-to-RF/noise inference.",
    ]
    yy = 1460
    for row in rows:
        text(38, yy, row, "small")
        yy += 29
    s.append("</svg>")
    (OUT / "fabrication-drawing.svg").write_text("\n".join(s) + "\n")
    (OUT / "fabrication-schedule.json").write_text(
        json.dumps(
            dict(
                design=d,
                thread_solids="Tap drills/cylindrical screw envelopes; threads are callouts,not helical BREP",
                critical_surfaces="BareCu contact faces Ra≤1.6µm,flatness allocation0.03; PEEK seat±0.03; all actual process limits require supplier approval",
                assembly_clearance_allocations=dict(bar_xy_float_and_process_mm=0.65, bar_z_process_mm=0.1),
                physical_fit_verified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
