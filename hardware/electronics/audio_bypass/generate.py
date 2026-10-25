#!/usr/bin/env python3
"""Generate E03 stereo relay contacts, with native editable KiCad symbols.

This sheet completes the contact-side interface to E02, not the analog stages
or a PCB. Persist edits here when using this generator.
"""

import csv
import io
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = "https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf"
RELAY_FP = "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y"


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E03:" + name))


def q(value):
    return json.dumps(str(value))


# All components are passive. The coil's polarity is nevertheless significant.
# Manufacturer drawing, page 6: TOP view, non-latching G6K-2F-Y.
# Each pin is (number, function, local x/y, inward angle).
RELAY_PINS = [
    ("1", "COIL+", -20.32, 5.08, 0),
    ("8", "COIL-", -20.32, -5.08, 0),
    ("3", "L_COM", -5.08, -10.16, 0),
    ("2", "L_NC", 15.24, -5.08, 180),
    ("4", "L_NO", 15.24, -15.24, 180),
    ("6", "R_COM", -5.08, 10.16, 0),
    ("7", "R_NC", 15.24, 15.24, 180),
    ("5", "R_NO", 15.24, 5.08, 180),
]

COMPONENTS = [
    dict(
        ref="K1",
        name="G6K2FY",
        value="G6K-2F-Y DC5",
        footprint=RELAY_FP,
        x=144.78,
        y=60.96,
        nets={
            "1": "5V",
            "8": "BYPASS_LOW",
            "3": "OUT_L",
            "2": "IN_L",
            "4": "PROC_OUT_L",
            "6": "OUT_R",
            "7": "IN_R",
            "5": "PROC_OUT_R",
        },
        note="Output selector: released is dry; energized is processed.",
    ),
    dict(
        ref="K2",
        name="G6K2FY",
        value="G6K-2F-Y DC5",
        footprint=RELAY_FP,
        x=144.78,
        y=124.46,
        nets={
            "1": "5V",
            "8": "BYPASS_LOW",
            "3": "PROC_IN_L",
            "2": None,
            "4": "IN_L",
            "6": "PROC_IN_R",
            "7": None,
            "5": "IN_R",
        },
        note="Processing-input isolation: both NC contacts intentionally open.",
    ),
]
for ref, value, nets, x, y in [
    ("J1", "LINE_IN", ["IN_L", "AGND", "IN_R"], 50.8, 55.88),
    ("J2", "LINE_OUT", ["OUT_L", "AGND", "OUT_R"], 238.76, 55.88),
    (
        "J3",
        "ANALOG_STAGES",
        ["PROC_IN_L", "AGND", "PROC_IN_R", "PROC_OUT_L", "AGND", "PROC_OUT_R"],
        238.76,
        121.92,
    ),
    ("J4", "E02_J4_COILS", ["5V", "BYPASS_LOW"], 50.8, 121.92),
]:
    COMPONENTS.append(
        dict(
            ref=ref,
            name=f"Header{len(nets)}",
            value=value,
            footprint=f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
            x=x,
            y=y,
            nets={str(i + 1): net for i, net in enumerate(nets)},
            note="Prototype interface only; production locking connector unselected.",
        )
    )


def pins(component):
    if component["name"] == "G6K2FY":
        return RELAY_PINS
    count = len(component["nets"])
    return [(str(i + 1), str(i + 1), -5.08, round((count - 1) * 2.54 - i * 5.08, 4), 0) for i in range(count)]


def line(points, dashed=False):
    return (
        "(polyline (pts "
        + "".join(f"(xy {x} {y})" for x, y in points)
        + f") (stroke (width .254) (type {'dash' if dashed else 'default'})) (fill (type none)))"
    )


def symbol(component, prefix=True):
    name = component["name"]
    header = name.startswith("Header")
    geometry = []
    if header:
        half = len(component["nets"]) * 2.54
        geometry.append(
            f"(rectangle (start -2.54 {half}) (end 2.54 {-half}) (stroke (width .254) (type default)) (fill (type none)))"
        )
    else:
        # Closed blades show the unpowered, normally closed state. No copper
        # connection is implied between the two poles or the coil.
        geometry.append(
            "(rectangle (start -11.43 2.54) (end -8.89 -2.54) (stroke (width .254) (type default)) (fill (type none)))"
        )
        geometry.extend(
            line(p)
            for p in [
                [(-17.78, 5.08), (-10.16, 5.08), (-10.16, 2.54)],
                [(-17.78, -5.08), (-10.16, -5.08), (-10.16, -2.54)],
                [(-2.54, 10.16), (0, 10.16), (10.16, 15.24), (12.7, 15.24)],
                [(10.16, 5.08), (12.7, 5.08)],
                [(-2.54, -10.16), (0, -10.16), (10.16, -5.08), (12.7, -5.08)],
                [(10.16, -15.24), (12.7, -15.24)],
            ]
        )
        geometry.append(line([(-8.89, 0), (2.54, 0)], True))
        geometry.append(line([(2.54, 11.43), (2.54, -8.89)], True))
        # Keep functional pin names in metadata, clear of the drawn blades.
    name_visibility = "" if header else "(hide yes)"
    out = [
        f'(symbol "{"RMX_E03:" if prefix else ""}{name}" (pin_names (offset .508) {name_visibility}) (in_bom yes) (on_board yes)',
        f'(property "Reference" "{"J" if header else "K"}" (at 0 20.32 0) (effects (font (size 1.27 1.27))))',
        f'(property "Value" {q(name)} (at 0 -20.32 0) (effects (font (size 1.27 1.27))))',
        f'(symbol "{name}_0_1" ' + "".join(geometry) + ")",
        f'(symbol "{name}_1_1"',
    ]
    for number, function, x, y, angle in pins(component):
        out.append(
            f"(pin passive line (at {x} {y} {angle}) (length 2.54) (name {q(function)} (effects (font (size 1 1)))) (number {q(number)} (effects (font (size 1 1)))))"
        )
    return "\n".join(out + ["))"])


def unique_symbols():
    return list({c["name"]: c for c in COMPONENTS}.values())


def schematic():
    root = uid("root")
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "A4")',
        '(title_block (title "Standalone RMX - stereo audio bypass contacts") (rev "E03") (comment 1 "Contact-side prototype; E02 drivers external; analog stages and PCB incomplete"))',
        "(lib_symbols " + "\n".join(symbol(c) for c in unique_symbols()) + ")",
    ]
    for c in COMPONENTS:
        ref, x, y = c["ref"], c["x"], c["y"]
        halfheight = 20.32 if ref.startswith("K") else len(c["nets"]) * 2.54 + 3.81
        out.append(
            f'(symbol (lib_id "RMX_E03:{c["name"]}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})'
        )
        for key, val, py, hide in [
            ("Reference", ref, y - halfheight, False),
            ("Value", c["value"], y + halfheight, False),
            ("Footprint", c["footprint"], y, True),
            ("Datasheet", SOURCE if ref.startswith("K") else "", y, True),
        ]:
            out.append(
                f"(property {q(key)} {q(val)} (at {x} {py} 0) (effects (font (size 1.27 1.27)) {'(hide yes)' if hide else ''}))"
            )
        for number, *_ in pins(c):
            out.append(f"(pin {q(number)} (uuid {uid(ref + '.' + number)}))")
        out.append(f'(instances (project "audio_bypass" (path "/{root}" (reference "{ref}") (unit 1)))))')
        for number, _, px, py, angle in pins(c):
            px, py = round(x + px, 4), round(y - py, 4)
            net = c["nets"][number]
            ident = ref + "." + number
            if net is None:
                out.append(f"(no_connect (at {px} {py}) (uuid {uid('nc' + ident)}))")
                continue
            end = round(px + (-5.08 if angle == 0 else 5.08), 4)
            out.append(
                f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {uid('wire' + ident)}))"
            )
            out.append(
                f"(label {q(net)} (at {end} {py} 0) (effects (font (size 1 1)) (justify {'right' if angle == 0 else 'left'} bottom)) (uuid {uid('label' + ident)}))"
            )
    notes = [
        (
            20.32,
            17.78,
            "E03 - stereo contacts. Blades shown RELEASED. Non-latching 5V relays; coil pin 1 positive, pin 8 switched low.",
        ),
        (
            20.32,
            25.4,
            "Connect J4 to E02 J4 pin-for-pin through a harness. E02 owns coil drivers and suppression.",
        ),
        (
            20.32,
            157.48,
            "K1 selects dry or processed output. K2 disconnects processing inputs when released; NC pins 2/7 are open.",
        ),
        (
            20.32,
            165.1,
            "J3 connects to protected line-level analog stages, NOT directly to converter/module pins. Grounds remain continuous.",
        ),
        (
            20.32,
            172.72,
            "Separate RCA/TS sources require selection/normalling upstream of J1. Gain switching remains on the analog-stage sheet.",
        ),
        (
            20.32,
            180.34,
            "Native ERC and ideal connectivity checks do not establish contact timing, click suppression, noise or physical fit.",
        ),
        (
            20.32,
            187.96,
            "Unrouted schematic prototype. Analog-rail monitoring, converter interface, protection, ground layout and PCB remain incomplete.",
        ),
    ]
    for i, (x, y, value) in enumerate(notes):
        out.append(
            f"(text {q(value)} (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid {uid('note' + str(i))}))"
        )
    return "\n".join(out + ["(embedded_fonts no))"])


def main():
    (ROOT / "audio_bypass.kicad_sch").write_text(schematic() + "\n")
    (ROOT / "audio_bypass.kicad_pro").write_text(
        json.dumps({"meta": {"filename": "audio_bypass.kicad_pro", "version": 1}}, indent=2) + "\n"
    )
    (ROOT / "RMX_E03.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + "\n".join(symbol(c, False) for c in unique_symbols())
        + ")\n"
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table (version 7) (lib (name "RMX_E03") (type "KiCad") (uri "${KIPRJMOD}/RMX_E03.kicad_sym") (options "") (descr "Own E03 relay contact and harness symbols")))\n'
    )
    libraries = sorted({c["footprint"].split(":")[0] for c in COMPONENTS})
    entries = [
        f'(lib (name "{name}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{name}.pretty") (options "") (descr "Standard KiCad footprint candidate"))'
        for name in libraries
    ]
    (ROOT / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    (ROOT / "components.json").write_text(json.dumps(COMPONENTS, indent=2) + "\n")
    rows = io.StringIO()
    writer = csv.writer(rows)
    writer.writerow(["Reference", "Value", "Footprint_candidate", "Note"])
    writer.writerows([c[k] for k in ("ref", "value", "footprint", "note")] for c in COMPONENTS)
    (ROOT / "bom.csv").write_text(rows.getvalue())
    print("E03 generated: two stereo bypass relays and four prototype interfaces; no routed PCB.")


if __name__ == "__main__":
    main()
