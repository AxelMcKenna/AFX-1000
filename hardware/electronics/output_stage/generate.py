#!/usr/bin/env python3
"""E05 native stereo output drivers, coupling and gain-output relay.

Receiver/codec, input stages, supplies, supervision and PCB are external.
"""

import csv
import io
import json
import uuid
from pathlib import Path

from ..common.symbols import symbol_units

ROOT = Path(__file__).resolve().parent
PARTS = []
PLACEMENTS = []
WIRES = []
LABELS = []
JUNCTIONS = []
RELAY_SOURCE = "https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf"
WIMA_SOURCE = "https://wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf"
FILM_FP = "Capacitor_THT:C_Rect_L7.2mm_W11.0mm_P5.00mm_FKS2_FKP2_MKS2_MKP2"
AMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E05:" + name))


def q(value):
    return json.dumps(str(value))


def part(ref, value, symbol, footprint, nets, x, y, unit=1, source="", mpn="", note=""):
    if not any(c["ref"] == ref for c in PARTS):
        PARTS.append(
            dict(
                ref=ref,
                value=value,
                symbol=symbol,
                footprint=footprint,
                nets=nets,
                source=source,
                mpn=mpn,
                note=note,
            )
        )
    PLACEMENTS.append(dict(ref=ref, x=x, y=y, unit=unit))


def wire(*points):
    WIRES.extend(zip(points, points[1:]))


def label(net, x, y, justify="left"):
    LABELS.append((net, x, y, justify))


def passive(ref, value, nets, x, y, vertical=False, footprint=None, **kwargs):
    kind = ref[0]
    footprint = footprint or f"{'Resistor' if kind == 'R' else 'Capacitor'}_SMD:{kind}_0805_2012Metric"
    part(
        ref, value, kind + ("V" if vertical else "H"), footprint, {"1": nets[0], "2": nets[1]}, x, y, **kwargs
    )


def stub_passive(ref, value, nets, x, y, **kwargs):
    passive(ref, value, nets, x, y, **kwargs)
    wire((x - 5.08, y), (x - 10.16, y))
    label(nets[0], x - 10.16, y, "right")
    wire((x + 5.08, y), (x + 10.16, y))
    label(nets[1], x + 10.16, y)


def build():
    for ref, value, rail, source in [
        ("U1", "OPA2992D", "19", "https://www.ti.com/lit/ds/symlink/opa2992.pdf"),
        ("U2", "OPA1612AID", "12", "https://www.ti.com/lit/ds/symlink/opa1612.pdf"),
    ]:
        mode = "M" if ref == "U1" else "S"
        nets = {
            "1": mode + "_DRV_L",
            "2": mode + "_FB_L",
            "3": "RECV_L",
            "4": "N" + rail,
            "5": "RECV_R",
            "6": mode + "_FB_R",
            "7": mode + "_DRV_R",
            "8": "P" + rail,
        }
        # Unit 3 contains only the actual package power pins, not another IC.
        part(
            ref,
            value,
            "DualAmp",
            AMP_FP,
            nets,
            535.94,
            63.5 if ref == "U1" else 223.52,
            unit=3,
            source=source,
            mpn=value,
        )
    for index, (prefix, channel, ref, unit, dx, dy) in enumerate(
        [
            ("M", "L", "U1", 1, 0, 0),
            ("M", "R", "U1", 2, 241.3, 0),
            ("S", "L", "U2", 1, 0, 160.02),
            ("S", "R", "U2", 2, 241.3, 160.02),
        ]
    ):
        c = next(c for c in PARTS if c["ref"] == ref)
        part(ref, c["value"], "DualAmp", AMP_FP, c["nets"], 69.85 + dx, 63.5 + dy, unit=unit)
        inp = "RECV_" + channel
        fb = prefix + "_FB_" + channel
        drive = prefix + "_DRV_" + channel
        series = prefix + "_SER_" + channel
        ac = prefix + "_AC_" + channel
        offset = index * 4
        passive(
            f"R{offset + 1}",
            "5.23k 0.1%" if prefix == "M" else "1.21k 0.1%",
            (fb, drive),
            95.25 + dx,
            93.98 + dy,
        )
        passive(
            f"R{offset + 2}",
            "1k 0.1%" if prefix == "M" else "2k 0.1%",
            (fb, "AGND"),
            55.88 + dx,
            119.38 + dy,
            vertical=True,
        )
        passive(
            f"R{offset + 3}",
            "100 1% 1W",
            (drive, series),
            139.7 + dx,
            63.5 + dy,
            footprint="Resistor_SMD:R_2512_6332Metric",
            note="Normal-load rating only; short/transient and thermal behavior unverified",
        )
        passive(f"R{offset + 4}", "20k 1%", (ac, "AGND"), 190.5 + dx, 99.06 + dy, vertical=True)
        for capref, cy in [(f"C{index + 1}", 63.5), (f"C{index + 13}", 88.9)]:
            passive(
                capref,
                "4.7uF film 63V 10%",
                (series, ac),
                170.18 + dx,
                cy + dy,
                footprint=FILM_FP,
                source=WIMA_SOURCE,
                mpn="MKS2C044701O00KSSD",
                note="Nonpolar PET; nominal body 7.2 x 11 x 18mm, pitch 5mm; 9.4uF per parallel pair; physical fit unverified",
            )

        def offset_wire(*points):
            wire(*[(round(x + dx, 4), round(y + dy, 4)) for x, y in points])

        def offset_label(net, x, y, justify="left"):
            label(net, round(x + dx, 4), round(y + dy, 4), justify)

        offset_wire((62.23, 60.96), (45.72, 60.96))
        offset_label(inp, 45.72, 60.96, "right")
        offset_wire((62.23, 66.04), (55.88, 66.04), (55.88, 93.98), (90.17, 93.98))
        offset_wire((55.88, 93.98), (55.88, 114.3))
        offset_label(fb, 55.88, 93.98, "right")
        offset_wire((55.88, 124.46), (55.88, 132.08))
        offset_label("AGND", 55.88, 132.08)
        offset_wire((77.47, 63.5), (115.57, 63.5), (134.62, 63.5))
        offset_wire((115.57, 63.5), (115.57, 93.98), (100.33, 93.98))
        offset_label(drive, 115.57, 63.5)
        offset_wire((144.78, 63.5), (165.1, 63.5))
        offset_label(series, 149.86, 63.5)
        offset_wire((154.94, 63.5), (154.94, 88.9), (165.1, 88.9))
        offset_wire((175.26, 88.9), (182.88, 88.9), (182.88, 63.5))
        offset_wire((175.26, 63.5), (190.5, 63.5), (190.5, 93.98))
        offset_label(ac, 190.5, 63.5)
        offset_wire((190.5, 104.14), (190.5, 111.76))
        offset_label("AGND", 190.5, 111.76)
        JUNCTIONS.extend(
            [
                (55.88 + dx, 93.98 + dy),
                (115.57 + dx, 63.5 + dy),
                (154.94 + dx, 63.5 + dy),
                (182.88 + dx, 63.5 + dy),
            ]
        )
    for ref, channel, x in [("R17", "L", 69.85), ("R18", "R", 311.15)]:
        stub_passive(
            ref,
            "100k 1%",
            ("RECV_" + channel, "AGND"),
            x,
            154.94,
            note="Input cable bias return; receiver must supply <=100Ohm source impedance",
        )
    for i, rail in enumerate(("P19", "N19", "P12", "N12")):
        x = 40.64 + i * 71.12
        stub_passive(f"C{i + 5}", "100nF 50V X7R", (rail, "AGND"), x, 350.52)
        stub_passive(
            f"C{i + 9}",
            "10uF 50V X7R",
            (rail, "AGND"),
            x,
            375.92,
            footprint="Capacitor_SMD:C_1210_3225Metric",
            note="Require effective capacitance >=4.7uF on actual rail; exact MPN/bias curve unselected",
        )
    relay = {
        "1": "5V",
        "8": "GAIN_LOW",
        "3": "PROC_OUT_L",
        "2": "M_AC_L",
        "4": "S_AC_L",
        "6": "PROC_OUT_R",
        "7": "M_AC_R",
        "5": "S_AC_R",
    }
    part(
        "K3",
        "G6K-2F-Y DC5",
        "Relay",
        "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y",
        relay,
        342.9,
        335.28,
        source=RELAY_SOURCE,
        mpn="G6K-2F-Y DC5",
        note="Released Master / energized Send-Return; second input-range relay remains external",
    )
    for ref, value, nets, y in [
        ("J1", "POST_RECEIVER", ["RECV_L", "AGND", "RECV_R"], 121.92),
        ("J2", "E03_PROCESSED_OUT", ["PROC_OUT_L", "AGND", "PROC_OUT_R"], 172.72),
        ("J3", "E02_J5_GAIN_COIL", ["5V", "GAIN_LOW"], 284.48),
        ("J4", "REGULATED_RAILS", ["P19", "AGND", "N19", "P12", "N12"], 345.44),
    ]:
        part(
            ref,
            value,
            "Header" + str(len(nets)),
            f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
            {str(i + 1): net for i, net in enumerate(nets)},
            535.94,
            y,
            note="Prototype interface; final locking connector and harness not selected",
        )


def symbol(name, prefix=True):
    out = [
        f'(symbol "{"RMX_E05:" if prefix else ""}{name}" (pin_names (offset .508) (hide yes)) (in_bom yes) (on_board yes)',
        '(property "Reference" "REF" (at 0 10.16 0) (effects (font (size 1.27 1.27))))',
        f'(property "Value" {q(name)} (at 0 -10.16 0) (effects (font (size 1.27 1.27))))',
    ]
    for unit, shape, pins in symbol_units(name):
        out.append(f'(symbol "{name}_{unit}_1" ' + shape)
        for number, function, x, y, angle, kind in pins:
            length = 0 if name == "SupplyFlag" else 2.54
            out.append(
                f"(pin {kind} line (at {x} {y} {angle}) (length {length}) (name {q(function)} (effects (font (size 1 1)))) (number {q(number)} (effects (font (size 1 1)))))"
            )
        out.append(")")
    return "\n".join(out + [")"])


def schematic():
    root = uid("root")
    names = sorted({c["symbol"] for c in PARTS} | {"SupplyFlag"})
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "A2")',
        '(title_block (title "Standalone RMX - stereo output drivers and gain relay") (rev "E05") (comment 1 "Post-receiver output-stage prototype; unrouted and unmeasured"))',
        "(lib_symbols " + "\n".join(symbol(name) for name in names) + ")",
    ]
    extra_wires = []
    extra_labels = []
    for p in PLACEMENTS:
        c = next(c for c in PARTS if c["ref"] == p["ref"])
        ref, x, y, unit = c["ref"], p["x"], p["y"], p["unit"]
        name = c["symbol"]
        pins = next(pins for u, _, pins in symbol_units(name) if u == unit)
        ident = ref + "." + str(unit)
        out.append(
            f'(symbol (lib_id "RMX_E05:{name}") (at {x} {y} 0) (unit {unit}) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ident)})'
        )
        if name == "RV":
            props = [
                ("Reference", ref, x + 10.16, y - 2.54, False),
                ("Value", c["value"], x + 10.16, y + 2.54, False),
            ]
        else:
            margin = (
                20.32
                if name == "Relay"
                else (
                    len(c["nets"]) * 2.54 + 3.81
                    if name.startswith("Header")
                    else (10.16 if name == "DualAmp" else 7.62)
                )
            )
            props = [("Reference", ref, x, y - margin, False), ("Value", c["value"], x, y + margin, False)]
        props.extend(
            (key, val, x, y, True)
            for key, val in [("Footprint", c["footprint"]), ("Datasheet", c["source"]), ("MPN", c["mpn"])]
        )
        for key, val, px, py, hide in props:
            out.append(
                f"(property {q(key)} {q(val)} (at {px} {py} 0) (effects (font (size 1.27 1.27)) {'(hide yes)' if hide else ''}))"
            )
        for number, *_ in pins:
            out.append(f"(pin {q(number)} (uuid {uid(ident + '.' + number)}))")
        out.append(
            f'(instances (project "output_stage" (path "/{root}" (reference "{ref}") (unit {unit})))))'
        )
        if name in ("Relay",) or name.startswith("Header") or (name == "DualAmp" and unit == 3):
            for number, _, px, py, angle, _ in pins:
                px, py = round(x + px, 4), round(y - py, 4)
                end = round(px + (-5.08 if angle == 0 else 5.08), 4)
                extra_wires.append(((px, py), (end, py)))
                extra_labels.append((c["nets"][number], end, py, "right" if angle == 0 else "left"))
    for i, (a, b) in enumerate(WIRES + extra_wires):
        out.append(
            f"(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {uid('wire' + str(i))}))"
        )
    for i, (net, x, y, justify) in enumerate(LABELS + extra_labels):
        out.append(
            f"(label {q(net)} (at {x} {y} 0) (effects (font (size 1 1)) (justify {justify} bottom)) (uuid {uid('label' + str(i))}))"
        )
    for i, (x, y) in enumerate(JUNCTIONS):
        out.append(f"(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid {uid('junction' + str(i))}))")
    for i, net in enumerate(("P19", "N19", "P12", "N12", "AGND")):
        x, y = 452.12, 320.04 + i * 12.7
        ref = "#FLAG" + str(i)
        out.append(
            f'(symbol (lib_id "RMX_E05:SupplyFlag") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid(ref)})'
            f'(property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'
            f'(property "Value" "External {net}" (at {x} {y + 2.54} 0) (effects (font (size 1 1))))'
            f'(pin "1" (uuid {uid(ref + "pin")}))'
            f'(instances (project "output_stage" (path "/{root}" (reference "{ref}") (unit 1)))))'
        )
        out.append(
            f'(label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(ref + "label")}))'
        )
    notes = [
        (
            20.32,
            17.78,
            "E05 - 2Vrms SINGLE-ENDED, zero-DC post-receiver input. Not the codec differential pins. Supplies regulated and supervised externally.",
        ),
        (
            20.32,
            25.4,
            "Master: OPA2992 on +/-19V. Send/Return: OPA1612 on +/-12V. Each branch retains fixed feedback, coupling and a 20k bleed.",
        ),
        (20.32, 40.64, "MASTER LEFT"),
        (261.62, 40.64, "MASTER RIGHT"),
        (20.32, 200.66, "SEND/RETURN LEFT"),
        (261.62, 200.66, "SEND/RETURN RIGHT"),
        (
            20.32,
            316.23,
            "J2 -> E03 J3 pins 4/5/6. J3 -> E02 J5 pins 1/2. K3 released=Master, energized=Send/Return.",
        ),
        (
            20.32,
            324.0,
            "Second gain coil/input-range contacts are external. ALL FOUR audio rails must qualify E02 ANALOG_OK. Firmware switches gain while dry.",
        ),
        (
            20.32,
            398.78,
            "Unrouted schematic. Verify converter/receiver, ESD, coupling leakage/distortion, stability, shorts, power ramps, click level, actual audio specs and physical fit.",
        ),
    ]
    for i, (x, y, value) in enumerate(notes):
        out.append(
            f"(text {q(value)} (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid {uid('note' + str(i))}))"
        )
    return "\n".join(out + ["(embedded_fonts no))"])


def main():
    build()
    (ROOT / "output_stage.kicad_sch").write_text(schematic() + "\n")
    from .place import project_settings

    (ROOT / "output_stage.kicad_pro").write_text(
        json.dumps(
            {
                "meta": {"filename": "output_stage.kicad_pro", "version": 1},
                "board": {"design_settings": project_settings()},
            },
            indent=2,
        )
        + "\n"
    )
    (ROOT / "RMX_E05.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + "\n".join(symbol(name, False) for name in sorted({c["symbol"] for c in PARTS} | {"SupplyFlag"}))
        + ")\n"
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table (version 7) (lib (name "RMX_E05") (type "KiCad") (uri "${KIPRJMOD}/RMX_E05.kicad_sym") (options "") (descr "Own E05 native symbols")))\n'
    )
    names = sorted({c["footprint"].split(":")[0] for c in PARTS})
    entries = [
        f'(lib (name "{name}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{name}.pretty") (options "") (descr "Standard footprint candidate"))'
        for name in names
    ]
    entries.append(
        '(lib (name "RMX_Output") (type "KiCad") (uri "${KIPRJMOD}/RMX_Output.pretty") (options "") (descr "Own E06 mounting clearance"))'
    )
    (ROOT / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    (ROOT / "components.json").write_text(json.dumps(PARTS, indent=2) + "\n")
    table = io.StringIO()
    writer = csv.writer(table)
    keys = ("ref", "value", "mpn", "footprint", "source", "note")
    writer.writerow(keys)
    writer.writerows([c[k] for k in keys] for c in PARTS)
    (ROOT / "bom.csv").write_text(table.getvalue())
    print(f"E05 generated: {len(PARTS)} physical components; native ERC and circuit checks still required.")


if __name__ == "__main__":
    main()
