#!/usr/bin/env python3
"""E08 native stereo DAC I/V, common-mode feedback and receiver prototype.

Uses the project's already audited SOIC dual-amplifier symbol geometry. Circuit
generation does not approve the unresolved converter scale or board layout.
"""

import csv
import io
import json
import uuid
from pathlib import Path

from ..common import symbols as geometry

ROOT = Path(__file__).resolve().parent

AMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
TI = "https://www.ti.com/lit/ds/symlink/opa1612.pdf"
FET = "https://www.ti.com/lit/ds/symlink/opa1656.pdf"
ESS = "https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf"
WIMA = "https://wima.de/wp-content/uploads/media/e_WIMA_MKS_2.pdf"
PARTS = []
PLACEMENTS = []


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E08:" + name))


def q(value):
    return json.dumps(str(value))


def part(ref, value, symbol, nets, x, y, unit=1, footprint=None, source="", mpn="", note=""):
    x = round(round(x / 1.27) * 1.27, 4)
    y = round(round(y / 1.27) * 1.27, 4)
    if not any(p["ref"] == ref for p in PARTS):
        PARTS.append(
            dict(
                ref=ref,
                value=value,
                symbol=symbol,
                nets=nets,
                footprint=footprint,
                source=source,
                mpn=mpn,
                note=note,
            )
        )
    PLACEMENTS.append(dict(ref=ref, x=x, y=y, unit=unit))


def passive(ref, value, nets, x, y, footprint=None, **kwargs):
    kind = ref[0]
    part(
        ref,
        value,
        kind + "H",
        {"1": nets[0], "2": nets[1]},
        x,
        y,
        footprint=footprint or f"{'Resistor' if kind == 'R' else 'Capacitor'}_SMD:{kind}_0805_2012Metric",
        **kwargs,
    )


def build():
    for ch, ref in [("L", "U1"), ("R", "U2")]:
        n = {
            "1": f"IV_P_{ch}",
            "2": f"DAC_{ch}P",
            "3": f"BIAS_P_{ch}",
            "4": "N12",
            "5": f"BIAS_N_{ch}",
            "6": f"DAC_{ch}N",
            "7": f"IV_N_{ch}",
            "8": "P12",
        }
        part(
            ref,
            "OPA1612AID",
            "DualAmp",
            n,
            50 + (280 if ch == "R" else 0),
            70,
            footprint=AMP_FP,
            source=TI,
            mpn="OPA1612AID",
            note="Two I/V legs; 1.8k feedback and 510pF follow ESS figure 44 functionally; converter drive scale unverified",
        )
        part(ref, "OPA1612AID", "DualAmp", n, 50 + (280 if ch == "R" else 0), 155, unit=2)
    for ref, note, nets in [
        (
            "U3",
            "Common-mode feedback: dual OPA1612 replaces two reference OPA1611 servo units",
            {
                "1": "CM_DRV_L",
                "2": "CM_SUM_L",
                "3": "AGND",
                "4": "N12",
                "5": "AGND",
                "6": "CM_SUM_R",
                "7": "CM_DRV_R",
                "8": "P12",
            },
        ),
        (
            "U4",
            "Matched differential-to-single-ended low-pass receiver; no direct raw-DAC voltage-scale assumption",
            {
                "1": "RX_OUT_L",
                "2": "RX_NEG_L",
                "3": "RX_POS_L",
                "4": "N12",
                "5": "RX_POS_R",
                "6": "RX_NEG_R",
                "7": "RX_OUT_R",
                "8": "P12",
            },
        ),
        (
            "U5",
            "Low-bias FET unity buffer after DC-blocking film cap; preserves low source impedance at E05",
            {
                "1": "BUF_OUT_L",
                "2": "BUF_OUT_L",
                "3": "BUF_IN_L",
                "4": "N12",
                "5": "BUF_IN_R",
                "6": "BUF_OUT_R",
                "7": "BUF_OUT_R",
                "8": "P12",
            },
        ),
    ]:
        for ch, unit, dx in [("L", 1, 0), ("R", 2, 280)]:
            device = "OPA1656ID" if ref == "U5" else "OPA1612AID"
            part(
                ref,
                device,
                "DualAmp",
                nets,
                (50 if ref == "U3" else 210) + dx,
                250 if ref == "U3" else 390 if ref == "U5" else 155,
                unit=unit,
                footprint=AMP_FP,
                source=FET if ref == "U5" else TI,
                mpn=device,
                note=note,
            )
    for index, ch in enumerate(("L", "R")):
        dx = 280 * index
        ro = 12 * index
        co = 5 * index

        def n(name):
            return name + "_" + ch

        resistors = [
            (
                "1.8k 0.1%",
                (f"DAC_{ch}P", n("IV_P")),
                120,
                55,
                "I/V feedback; equivalent to ESS parallel 3.6k pair",
            ),
            ("1.8k 0.1%", (f"DAC_{ch}N", n("IV_N")), 120, 140, "I/V feedback"),
            ("4.3 1%", (n("CM_DRV"), n("BIAS_P")), 120, 105, "Noninverting-input isolation, ESS figure 44"),
            ("4.3 1%", (n("CM_DRV"), n("BIAS_N")), 120, 190, "Noninverting-input isolation"),
            ("100k 0.1%", (n("IV_P"), n("CM_SUM")), 120, 225, "Common-mode sum; do not omit either leg"),
            ("100k 0.1%", (n("IV_N"), n("CM_SUM")), 120, 250, "Common-mode sum"),
            (
                "1.2M 0.1%",
                (n("CM_SUM"), n("CM_DRV")),
                120,
                275,
                "Common-mode feedback, not a zero-DC integrator",
            ),
            (
                "499 0.01%",
                (n("IV_P"), n("RX_NEG")),
                210,
                55,
                "Matched receiver ratio; final precision resistor MPN unselected",
            ),
            (
                "499 0.01%",
                (n("IV_N"), n("RX_POS")),
                210,
                80,
                "Polarity restores positive DAC-to-RECV transfer",
            ),
            ("499 0.01%", (n("RX_NEG"), n("RX_OUT")), 210, 225, "Receiver feedback, match R8/R9/R11 ratios"),
            ("499 0.01%", (n("RX_POS"), "AGND"), 210, 250, "Receiver noninverting shunt"),
            (
                "33.2 0.1%",
                (n("BUF_OUT"), n("RECV")),
                210,
                420,
                "Output isolation; E05 supplies 100k load; harness capacitance unqualified",
            ),
        ]
        for i, (value, nets, x, y, note) in enumerate(resistors, 1):
            passive(f"R{ro + i}", value, nets, x + dx, y, note=note)
        capacitors = [
            ("510pF 50V C0G 2%", (f"DAC_{ch}P", n("IV_P")), 120, 80),
            ("510pF 50V C0G 2%", (f"DAC_{ch}N", n("IV_N")), 120, 165),
            ("51pF 50V C0G 2%", (n("CM_SUM"), n("CM_DRV")), 120, 300),
            ("1nF 50V C0G 1%", (n("RX_NEG"), n("RX_OUT")), 210, 275),
            ("1nF 50V C0G 1%", (n("RX_POS"), "AGND"), 210, 300),
        ]
        for i, (value, nets, x, y) in enumerate(capacitors, 1):
            passive(
                f"C{co + i}",
                value,
                nets,
                x + dx,
                y,
                note="C0G/NP0 required; final MPN and receiver pair matching unselected",
            )
        passive(
            f"R{25 + index}",
            "33.2k 0.1%",
            (n("HP_NODE"), "AGND"),
            120 + dx,
            350,
            note="Post-coupling bias return; FET hot bias and film-leakage allocations checked independently",
        )
        passive(
            f"R{27 + index}",
            "2.74k 0.1% 0.5W",
            (n("HP_NODE"), n("BUF_IN")),
            120 + dx,
            385,
            footprint="Resistor_SMD:R_2010_5025Metric",
            note="Input-current limiting provision; exact 0.5W part/pulse/derating qualification and rail injection review pending",
        )
        part(
            f"C{21 + index}",
            "2.2uF film 63V 10%",
            "CH",
            {"1": n("RX_OUT"), "2": n("HP_NODE")},
            120 + dx,
            325,
            footprint="Capacitor_THT:C_Rect_L7.2mm_W7.2mm_P5.00mm_FKS2_FKP2_MKS2_MKP2",
            source=WIMA,
            mpn="MKS2C042201K00KSSD",
            note="Nonpolar PET; nominal 7.2x7.2x13mm, 5mm pitch. Blocks receiver DC before low-impedance buffer; physical fit pending",
        )
    for i, ref in enumerate(("U1", "U2", "U3", "U4", "U5")):
        c = next(c for c in PARTS if c["ref"] == ref)
        x = 50 + i * 120
        part(ref, c["value"], "DualAmp", c["nets"], x, 440, unit=3)
        caprefs = (23, 24) if ref == "U5" else (11 + 2 * i, 12 + 2 * i)
        for k, rail in enumerate(("P12", "N12")):
            passive(
                f"C{caprefs[k]}",
                "100nF 50V X7R",
                (rail, "AGND"),
                x,
                465 + 25 * k,
                note="Local supply bypass; place at the actual package power pin",
            )
    for i, rail in enumerate(("P12", "N12")):
        passive(
            f"C{19 + i}",
            "10uF 50V X7R",
            (rail, "AGND"),
            560,
            440 + 25 * i,
            footprint="Capacitor_SMD:C_1210_3225Metric",
            note="Bulk: effective capacitance at 12V must be >=4.7uF; MPN/bias curve unselected",
        )
    for ref, label, nets, y in [
        ("J1", "RAW_DAC_PINS", ["DAC_LP", "DAC_LN", "AGND", "DAC_RP", "DAC_RN"], 55),
        ("J2", "E05_POST_RECEIVER", ["RECV_L", "AGND", "RECV_R"], 140),
        ("J3", "REGULATED_LOW_RAILS", ["P12", "AGND", "N12"], 225),
    ]:
        part(
            ref,
            label,
            "Header" + str(len(nets)),
            {str(i + 1): net for i, net in enumerate(nets)},
            560,
            y,
            footprint=f"Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02d}_P2.54mm_Vertical",
            note="Prototype circuit boundary, not approval for long raw-DAC wiring or final connector",
        )


def symbol(name, prefix=True):
    out = [
        f'(symbol "{"RMX_E08:" if prefix else ""}{name}" (pin_names (offset .508) (hide yes)) (in_bom yes) (on_board yes)',
        '(property "Reference" "REF" (at 0 10.16 0) (effects (font (size 1.27 1.27))))',
        f'(property "Value" {q(name)} (at 0 -10.16 0) (effects (font (size 1.27 1.27))))',
    ]
    for unit, shape, pins in geometry.symbol_units(name):
        out.append(f'(symbol "{name}_{unit}_1" ' + shape)
        for number, function, x, y, angle, kind in pins:
            out.append(
                f"(pin {kind} line (at {x} {y} {angle}) (length {0 if name == 'SupplyFlag' else 2.54}) (name {q(function)} (effects (font (size 1 1)))) (number {q(number)} (effects (font (size 1 1)))))"
            )
        out.append(")")
    return "\n".join(out + [")"])


def schematic():
    root = uid("root")
    names = sorted({c["symbol"] for c in PARTS} | {"SupplyFlag"})
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "User" 594 520)',
        '(title_block (title "Standalone RMX - stereo DAC I/V and receiver") (rev "E08") (comment 1 "ESS reference-derived I/V; loaded receiver prototype, not routed or measured"))',
        "(lib_symbols " + "\n".join(symbol(name) for name in names) + ")",
    ]
    for placement in PLACEMENTS:
        ref, x, y, unit = (placement[k] for k in ("ref", "x", "y", "unit"))
        c = next(c for c in PARTS if c["ref"] == ref)
        name = c["symbol"]
        ident = f"{ref}.{unit}"
        pins = next(pins for u, _, pins in geometry.symbol_units(name) if u == unit)
        out.append(
            f'(symbol (lib_id "RMX_E08:{name}") (at {x} {y} 0) (unit {unit}) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ident)})'
        )
        margin = (
            10.16
            if name == "DualAmp"
            else len(c["nets"]) * 2.54 + 3.81
            if name.startswith("Header")
            else 7.62
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
            f'(instances (project "dac_receiver" (path "/{root}" (reference "{ref}") (unit {unit})))))'
        )
        for number, _, px, py, angle, _ in pins:
            px, py = round(x + px, 4), round(y - py, 4)
            end = round(px + (-5.08 if angle == 0 else 5.08), 4)
            out.append(
                f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {uid(ident + 'wire' + number)}))"
            )
            out.append(
                f"(label {q(c['nets'][number])} (at {end} {py} 0) (effects (font (size 1 1)) (justify {'right' if angle == 0 else 'left'} bottom)) (uuid {uid(ident + 'label' + number)}))"
            )
    for i, net in enumerate(("P12", "N12", "AGND")):
        x = round(round((330 + i * 80) / 1.27) * 1.27, 4)
        y = 508
        ref = "#FLAG" + str(i)
        out.append(
            f'(symbol (lib_id "RMX_E08:SupplyFlag") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid(ref)})'
            f'(property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'
            f'(property "Value" "External {net}" (at {x} {y - 3} 0) (effects (font (size 1 1))))'
            f'(pin "1" (uuid {uid(ref + "pin")}))'
            f'(instances (project "dac_receiver" (path "/{root}" (reference "{ref}") (unit 1)))))'
        )
        out.append(
            f'(label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(ref + "label")}))'
        )
    notes = [
        (
            20,
            15,
            "E08 - stereo DAC I/V + common-mode feedback + filtered differential receiver. Supplies +/-12V, externally qualified.",
        ),
        (
            20,
            23,
            "ESS ES9292PRO figure 44 basis. Raw pin scale, impedance convention, power-fault protection, noise/THD and stability are not approved.",
        ),
        (20, 35, "LEFT I/V LEGS"),
        (180, 35, "LEFT RECEIVER"),
        (300, 35, "RIGHT I/V LEGS"),
        (460, 35, "RIGHT RECEIVER"),
        (20, 210, "LEFT COMMON-MODE LOOP"),
        (300, 210, "RIGHT COMMON-MODE LOOP"),
        (
            20,
            508,
            "J1 -> ES pins 5,4,ground,8,7. J2 -> E05 J1. Raw DAC scale and startup settling must be verified before processed audio is enabled.",
        ),
    ]
    for i, (x, y, value) in enumerate(notes):
        out.append(
            f"(text {q(value)} (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid {uid('note' + str(i))}))"
        )
    return "\n".join(out + ["(embedded_fonts no))"])


def main():
    build()
    ROOT.mkdir(exist_ok=True)
    (ROOT / "generated").mkdir(exist_ok=True)
    (ROOT / "dac_receiver.kicad_sch").write_text(schematic() + "\n")
    (ROOT / "dac_receiver.kicad_pro").write_text(
        json.dumps({"meta": {"filename": "dac_receiver.kicad_pro", "version": 1}}, indent=2) + "\n"
    )
    names = sorted({c["symbol"] for c in PARTS} | {"SupplyFlag"})
    (ROOT / "RMX_E08.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + "\n".join(symbol(name, False) for name in names)
        + ")\n"
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table (version 7) (lib (name "RMX_E08") (type "KiCad") (uri "${KIPRJMOD}/RMX_E08.kicad_sym") (options "") (descr "Own project E08 symbols")))\n'
    )
    entries = [
        f'(lib (name "{name}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{name}.pretty") (options "") (descr "Standard candidate footprint"))'
        for name in sorted({p["footprint"].split(":")[0] for p in PARTS})
    ]
    (ROOT / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    (ROOT / "components.json").write_text(json.dumps(PARTS, indent=2) + "\n")
    table = io.StringIO()
    writer = csv.writer(table)
    keys = ("ref", "value", "mpn", "footprint", "source", "note")
    writer.writerow(keys)
    writer.writerows([p[k] for k in keys] for p in PARTS)
    (ROOT / "bom.csv").write_text(table.getvalue())
    print(f"E08 generated: {len(PARTS)} physical components. Native ERC and loaded-circuit checks required.")


if __name__ == "__main__":
    main()
