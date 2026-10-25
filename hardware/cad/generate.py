#!/usr/bin/env python3
"""Generate A02 standalone panel assets and check visible spacing. Standard library only."""

import csv
import html
import io
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
W, D = 334, 157
FASTENERS = [(x, y) for x in (8, 167, 326) for y in (8, 149)]
CONTROLS = []


def add(id, label, kind, x, y, w, h, target, behavior, value="", height=3):
    CONTROLS.append(
        dict(
            id=id,
            label=label,
            kind=kind,
            x=x,
            y=y,
            w=w,
            h=h,
            target=target,
            behavior=behavior,
            value=value,
            height=height,
        )
    )


for id, label, x, y, diameter, height, target in [
    ("input", "INPUT LEVEL", 18, 27, 16, 13, "input_gain"),
    ("output", "OUTPUT LEVEL", 114, 27, 16, 13, "output_gain"),
    ("low", "LOW", 52, 78, 29, 18, "low"),
    ("mid", "MID", 108, 78, 29, 18, "mid"),
    ("high", "HI", 164, 78, 29, 18, "high"),
    ("scene_depth", "SCENE DEPTH", 244, 78, 32, 18, "scene_depth"),
    ("x_level", "X-PAD LEVEL", 18, 133, 16, 13, "x_level"),
    ("x_pitch", "PITCH", 53, 133, 17, 15, "x_pitch"),
    ("scene_time", "SUB PARAM 1", 194, 133, 17, 15, "scene_time"),
    ("scene_resonance", "SUB PARAM 2", 295, 133, 17, 15, "scene_resonance"),
]:
    add(
        id,
        label,
        "knob",
        x,
        y,
        diameter,
        diameter,
        target,
        "absolute; scene_depth also enables Scene FX",
        height=height,
    )


def button(id, label, x, y, w, h, target, behavior="toggle", value=""):
    add(id, label, "button", x, y, w, h, target, behavior, value)


button("quantize", "QUANTIZE", 134, 22, 19, 8, "quantize")
button("auto", "AUTO", 185, 22, 14, 8, "auto_tempo")
button("tap", "TAP", 185, 38, 12, 10, "EventType::Tap", "momentary event")
button("nudge_down", "-", 129, 38, 9, 8, "tempo + auto_tempo", "tempo -= 0.1; auto_tempo = 0")
button("nudge_up", "+", 140, 38, 9, 8, "tempo + auto_tempo", "tempo += 0.1; auto_tempo = 0")
add(
    "bpm",
    "120",
    "display",
    160,
    31,
    25,
    16,
    "tempo",
    "three common-anode 0.36-inch digits; manual BPM via tap/nudge",
)
button(
    "source_input",
    "INPUT",
    17,
    60,
    14,
    8,
    "scene_source + isolate_source",
    "toggle input source bit; see PanelController.h",
)
button(
    "source_xpad",
    "X-PAD",
    17,
    92,
    14,
    8,
    "scene_source + isolate_source",
    "toggle sampler source bit; see PanelController.h",
)
for value, (label, x) in enumerate(
    [("ISOLATOR", 70), ("CUT / ADD", 91), ("TRANS / ROLL", 127), ("GATE / DRIVE", 148)]
):
    button(f"isolate_{value}", label, x, 59, 18, 7, "isolate_mode", "select mode", value)
button("bank", "BANK", 36, 110, 11, 8, "bank", "cycle 0..3")
button("roll", "ROLL", 63, 110, 15, 8, "x_source")
for i, label in enumerate(["KICK", "SNARE", "CLAP", "HI HAT"]):
    button(
        f"pad_{i}",
        label,
        82 + 19 * i,
        110,
        15,
        8,
        "EventType::Trigger",
        f"USB MIDI note {36 + i}; release note-off",
        i,
    )
button(
    "overdub", "OVERDUB", 164, 110, 12, 8, "overdub", "toggle; long press proposes EventType::ClearSequence"
)
button(
    "hold", "HOLD", 164, 133, 13, 13, "x_hold", "toggle; off sends RollStop; long press proposes sampler_mute"
)
add(
    "xpad",
    "X-PAD",
    "strip",
    108,
    134,
    68,
    18,
    "x_roll + events",
    "8 zones; touch starts roll; release stops unless held",
    height=1,
)
add(
    "settings",
    "DEFAULT / USER",
    "switch",
    307,
    27,
    15,
    7,
    "user_settings",
    "two-position maintained",
    height=3,
)
add(
    "release_type",
    "RELEASE FX",
    "switch",
    316,
    54,
    15,
    7,
    "release_type",
    "three-position maintained: Back Spin / Echo / Vinyl Brake",
    height=3,
)
add(
    "release",
    "RELEASE",
    "lever",
    316,
    82,
    16,
    28,
    "release_amount",
    "spring return 0..1; 35 degree pivot; AS5600 angle sensor",
    height=12,
)

NAMES = [
    "BPF ECHO",
    "ECHO",
    "NOISE",
    "SPIRAL UP",
    "REVERB UP",
    "HPF ECHO",
    "LPF ECHO",
    "CRUSH ECHO",
    "SPIRAL DOWN",
    "REVERB DOWN",
]
for i, label in enumerate(NAMES):
    a = 207 + 25.2 * i if i < 5 else 153 - 25.2 * (i - 4)
    add(
        f"scene_{i}",
        label,
        "sector",
        244,
        78,
        35,
        52,
        "scene_type + scene_on",
        "select; selected effect pressed again bypasses Scene FX",
        i,
        height=2.4,
    )
    CONTROLS[-1].update(a=a + 1.2, b=a + 25.2 - 1.2)

# Optical apertures. Their lenses/light guides need prototype verification.
OPTICS = []
for row, y in enumerate((21.25, 35.25)):
    for i in range(20):
        OPTICS.append([f"meter_{row}_{i}", "rect", 43.9 + 3 * i, y, 1.8, 2.5, 0, 0])
for i in range(4):
    OPTICS.append([f"bank_led_{i}", "knob", 82 + 19 * i, 103, 2.2, 2.2, 0, 0])
for i in range(8):
    angle = math.radians(45 * i)
    OPTICS.append(
        [f"ring_light_{i}", "knob", 244 + 24 * math.cos(angle), 78 + 24 * math.sin(angle), 3, 3, 0, 0]
    )


def point(c, r, a):
    return c["x"] + r * math.cos(math.radians(a)), c["y"] + r * math.sin(math.radians(a))


def polygon(c):
    if c["kind"] == "sector":
        angles = [c["a"] + (c["b"] - c["a"]) * i / 32 for i in range(33)]
        return [point(c, c["h"], a) for a in angles] + [point(c, c["w"], a) for a in reversed(angles)]
    if c["kind"] == "knob":
        return [point(c, c["w"] / 2, i * 360 / 96) for i in range(96)]
    x, y, w, h = (c[k] for k in ["x", "y", "w", "h"])
    return [(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]


def distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def inside(p, poly):
    result = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            result = not result
    return result


def orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def gap(a, b):
    ea, eb = list(zip(a, a[1:] + a[:1])), list(zip(b, b[1:] + b[:1]))
    if inside(a[0], b) or inside(b[0], a):
        return 0
    for p, q in ea:
        for r, s in eb:
            if (
                orientation(p, q, r) * orientation(p, q, s) < 0
                and orientation(r, s, p) * orientation(r, s, q) < 0
            ):
                return 0
    return min(
        min(distance(p, r, s) for p in a for r, s in eb), min(distance(p, r, s) for p in b for r, s in ea)
    )


def validate():
    # Checks nominal visible envelopes only, not ergonomic clearance or hidden parts.
    nearest = (float("inf"), "", "")
    shapes = [(c, polygon(c)) for c in CONTROLS]
    for i, (c, poly) in enumerate(shapes):
        assert all(4.6 < x < W - 4.6 and 4.6 < y < D - 4.6 for x, y in poly), c["id"]
        for other, other_poly in shapes[i + 1 :]:
            d = gap(poly, other_poly)
            assert d >= 0.75, f"Control collision: {c['id']} / {other['id']}: {d:.2f} mm"
            nearest = min(nearest, (d, c["id"], other["id"]))
        for p in FASTENERS:
            assert (
                not inside(p, poly)
                and min(distance(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1])) > 4.5
            ), f"Boss interference: {c['id']}"
    params = (ROOT / "../runtime/include/rmx/Parameters.h").resolve().read_text()
    for c in CONTROLS:
        for target in c["target"].split(" + "):
            if target != "events" and not target.startswith("EventType::"):
                assert f'"{target}"' in params, target
    hardware = (ROOT / "../runtime/include/rmx/controls/HardwareControls.h").resolve().read_text()
    for name, kinds in [("knobIds", ("knob",)), ("buttonIds", ("button", "sector"))]:
        source = re.search(rf"{name}\s*\{{(.*?)\}};", hardware, re.S).group(1)
        ids = re.findall(r'"([a-z0-9_]+)"', source)
        assert ids == [c["id"] for c in CONTROLS if c["kind"] in kinds], (
            f"CAD/firmware input order differs: {name}"
        )
    print(
        f"{len(CONTROLS)} controls: visible envelopes and boss clearance pass. Minimum gap {nearest[0]:.2f} mm ({nearest[1]} / {nearest[2]})."
    )


def scad():
    rows, caps = [], []
    for c in CONTROLS:
        k = c["kind"]
        if k == "sector":
            opening = [c["id"], k, c["x"], c["y"], 35.6, 51.4, c["a"] + 0.5, c["b"] - 0.5]
            cap = [c["id"], k, c["x"], c["y"], c["w"], c["h"], c["a"], c["b"]]
        else:
            w, h = (9.3, 9.3) if k == "knob" else (12, 26) if k == "lever" else (c["w"] - 1, c["h"] - 1)
            opening = [c["id"], k, c["x"], c["y"], w, h, 0, 0]
            cap = [c["id"], k, c["x"], c["y"], c["w"], c["h"], c["height"], 0]
        rows.append(opening)
        caps.append(cap)
    rows.extend(OPTICS)
    return (
        "// Generated by ../generate.py; do not edit.\n"
        + "\n".join(
            f"{name} = {json.dumps(value)};"
            for name, value in [
                ("body_width", W),
                ("body_depth", D),
                ("fasteners", FASTENERS),
                ("openings", rows),
                ("caps", caps),
            ]
        )
        + "\n"
    )


def shape(c, fill, stroke, cut=False):
    x, y, w, h = (c[k] for k in ["x", "y", "w", "h"])
    attrs = f'fill="{fill}" stroke="{stroke}" stroke-width="0.25"'
    if c["kind"] == "sector":
        if cut:
            c = dict(c, w=35.6, h=51.4, a=c["a"] + 0.5, b=c["b"] - 0.5)
        pts = " ".join(f"{a:.4f},{b:.4f}" for a, b in polygon(c))
        return f'<polygon points="{pts}" {attrs}/>'
    if c["kind"] == "knob":
        return f'<circle cx="{x}" cy="{y}" r="{4.65 if cut else w / 2}" {attrs}/>'
    if cut:
        w, h = (12, 26) if c["kind"] == "lever" else (w - 1, h - 1)
    return f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" {attrs}/>'


def text(x, y, label, size=2.4, fill="#cfd3d7", anchor="middle"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}">{html.escape(label)}</text>'


def svg(cut=False):
    if cut:
        output = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{D}mm" viewBox="0 0 {W} {D}">',
            "<title>A02 standalone provisional panel apertures — not released for fabrication</title>",
            '<rect x="3.1" y="3.1" width="327.8" height="150.8" rx="3.9" fill="none" stroke="black" stroke-width="0.1"/>',
        ]
    else:
        output = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="378mm" height="215mm" viewBox="0 0 378 215">',
            "<title>RMX standalone enclosure A02 — top view and control layout</title>",
            '<rect width="378" height="215" fill="#101214"/>',
            '<g font-family="Arial,Helvetica,sans-serif">',
            text(22, 12, "RMX / HOUSING + CONTROL STUDY", 4.4, "#f1f3f4", "start"),
            text(356, 12, "A02 · STANDALONE · mm", 3, "#70d4c9", "end"),
            '<g transform="translate(22 30)">',
            '<rect width="334" height="157" rx="7" fill="#24282b" stroke="#565c61" stroke-width="0.7"/>',
            '<rect x="3.1" y="3.1" width="327.8" height="150.8" rx="3.9" fill="#1a1d20" stroke="#42474b" stroke-width="0.25"/>',
            '<path d="M5 52H174L190 73L174 100H5Z" fill="#474b4e"/>',
            text(244, 16, "SCENE FX", 3.4),
            text(312, 117, "RMX", 5, "#e4e8ea"),
            text(312, 122, "PERFORMANCE FX", 1.8),
            text(108, 99, "ISOLATE FX", 2.5),
            text(108, 122, "X-PAD FX", 2.5),
            '<circle cx="244" cy="78" r="26" fill="none" stroke="#62d8cd" stroke-width="1.1"/>',
        ]
        # Input/output meters and sample-bank indicators are optical envelopes only.
        for y in (20, 34):
            for i in range(20):
                col = "#6cc9ab" if i < 15 else "#e8b65e" if i < 19 else "#e46c60"
                output.append(f'<rect x="{43 + i * 3}" y="{y}" width="1.8" height="2.5" fill="{col}"/>')
        for i in range(4):
            output.append(text(82 + 19 * i, 103, str(i + 1), 2, "#70d4c9"))
        for x, y in FASTENERS:
            output.append(
                f'<circle cx="{x}" cy="{y}" r="1.7" fill="#101214" stroke="#60666c" stroke-width="0.35"/>'
            )
    for c in CONTROLS:
        if cut:
            output.append(shape(c, "none", "black", True))
            continue
        kind = c["kind"]
        color = "#e7b46b" if kind == "sector" and c["value"] < 5 else "#70d4c9"
        output.append(
            shape(
                c,
                "#262b2f" if kind not in ("display", "strip") else "#0c1719",
                color if kind in ("sector", "strip") else "#777f85",
            )
        )
        if kind == "knob":
            output.append(
                f'<path d="M{c["x"]} {c["y"] - c["w"] / 2 + 2}v{c["w"] * 0.28}" stroke="#f1f3f4" stroke-width="0.7"/>'
            )
            if c["id"] != "scene_depth":
                output.append(text(c["x"], c["y"] - c["w"] / 2 - 2.5, c["label"], 2.15))
        elif kind == "sector":
            x, y = point(c, 43.5, (c["a"] + c["b"]) / 2)
            words = c["label"].split()
            if len(words) > 1:
                output.append(text(x, y - 0.6, " ".join(words[:-1]), 2.1, color))
                output.append(text(x, y + 1.8, words[-1], 2.1, color))
            else:
                output.append(text(x, y + 0.8, c["label"], 2.2, color))
        elif kind in ("switch", "lever"):
            output.append(text(c["x"], c["y"] - c["h"] / 2 - 2.2, c["label"], 2))
            output.append(f'<rect x="{c["x"] - 3}" y="{c["y"] - 2}" width="6" height="4" fill="#8e969c"/>')
        elif kind == "display":
            output.append(text(c["x"], c["y"] + 2.5, c["label"], 7, "#e7b46b"))
        elif kind == "strip":
            for i in range(8):
                x = c["x"] - c["w"] / 2 + i * c["w"] / 8
                output.append(f'<path d="M{x} 127v14" stroke="#548b88" stroke-width="0.2"/>')
                output.append(
                    text(
                        x + 4.25, 135, ["1/16", "1/8", "1/4", "1/2", "3/4", "1", "2", "4"][i], 1.8, "#70d4c9"
                    )
                )
        else:
            output.append(text(c["x"], c["y"] + 0.8, c["label"], 1.65))
    if cut:
        for _, kind, x, y, w, h, _, _ in OPTICS:
            if kind == "knob":
                output.append(
                    f'<circle cx="{x}" cy="{y}" r="{w / 2}" fill="none" stroke="black" stroke-width="0.1"/>'
                )
            else:
                output.append(
                    f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" fill="none" stroke="black" stroke-width="0.1"/>'
                )
        for x, y in FASTENERS:
            output.append(
                f'<circle cx="{x}" cy="{y}" r="1.7" fill="none" stroke="black" stroke-width="0.1"/>'
            )
    else:
        output += [
            "</g>",
            '<g fill="none" stroke="#89939b" stroke-width="0.2"><path d="M22 25V19M356 25V19M22 22H356M362 30H368M362 187H368M365 30V187"/></g>',
            text(189, 20, "334", 2.7),
            '<text x="369" y="109" fill="#cfd3d7" font-size="2.7" transform="rotate(90 369 109)">157</text>',
            text(
                22,
                197,
                "Body 334 × 157 × 36 · inset panel 2 · largest caps Ø29 / Ø32 · onboard stereo DSP",
                3,
                "#cfd3d7",
                "start",
            ),
            text(
                22,
                204,
                "A02 PROTOTYPE — component envelopes and lever motion modeled; physical fit pending",
                2.7,
                "#e7b46b",
                "start",
            ),
            "</g>",
        ]
    return "\n".join(output + ["</svg>"]) + "\n"


def main():
    validate()
    OUT.mkdir(exist_ok=True)
    (OUT / "layout.scad").write_text(scad())
    (OUT / "panel-layout.svg").write_text(svg())
    (OUT / "panel-apertures.svg").write_text(svg(True))
    stream = io.StringIO()
    fields = list(CONTROLS[0]) + ["a", "b"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(CONTROLS)
    (OUT / "controls.csv").write_text(stream.getvalue())
    print(f"Wrote layout.scad, panel-layout.svg, panel-apertures.svg and controls.csv to {OUT}")


if __name__ == "__main__":
    main()
