#!/usr/bin/env python3
"""Generate E14 independent main rail generation schematic."""

import csv
import io
import json
import uuid

from .spec import BUCKS, COMPONENTS, NOTES, ROOT, STAGES


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E14:" + name))


def q(text):
    return json.dumps(str(text))


def grid(value):
    return round(value, 4)


def geometry(component):
    pins = []
    passive = component["ref"].startswith(("R", "C")) or (
        component["ref"].startswith("D") and len(component["pins"]) == 2
    )
    span = 5.08 if passive else 15.24
    for side in ("L", "R"):
        group = [p for p in component["pins"] if p["side"] == side]
        for index, pin in enumerate(group):
            pins.append(
                dict(
                    pin,
                    x=-span if side == "L" else span,
                    y=grid((len(group) - 1) * 2.54 - index * 5.08),
                    angle=0 if side == "L" else 180,
                )
            )
    height = max(len([p for p in pins if p["side"] == s]) for s in ("L", "R"))
    return pins, max(5.08, height * 2.54)


def symbol(component, prefixed=True):
    ref = component["ref"]
    name = "E14_" + ref
    pins, halfheight = geometry(component)
    prefix = "RMX_E14:" if prefixed else ""
    graphic = f"(rectangle (start -12.7 {halfheight}) (end 12.7 {-halfheight}) (stroke (width .254) (type default)) (fill (type none)))"

    def line(points):
        return (
            "(polyline (pts "
            + "".join(f"(xy {x} {y})" for x, y in points)
            + ") (stroke (width .254) (type default)) (fill (type none)))"
        )

    if ref.startswith("R"):
        graphic = "(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width .254) (type default)) (fill (type none)))"
    elif ref.startswith("C"):
        graphic = "".join(
            line(p)
            for p in [
                [(-2.54, 0), (-1.27, 0)],
                [(-1.27, -3.81), (-1.27, 3.81)],
                [(1.27, -3.81), (1.27, 3.81)],
                [(1.27, 0), (2.54, 0)],
            ]
        )
        if "tantalum" in component["part"]:
            graphic += '(text "+" (at -2.54 5.08 0) (effects (font (size 1.27 1.27))))'
    elif ref.startswith("D") and len(component["pins"]) == 2:
        graphic = "".join(
            line(p)
            for p in [
                [(-2.54, 0), (-1.27, 0)],
                [(1.27, 0), (2.54, 0)],
                [(-1.27, 0), (1.27, 1.905), (1.27, -1.905), (-1.27, 0)],
                [(-1.905, 1.905), (-1.27, 1.905), (-1.27, -1.905), (-0.635, -1.905)],
            ]
        )
    out = [
        f'(symbol "{prefix}{name}" (pin_names (offset .508)) (in_bom yes) (on_board yes)',
        f'(property "Reference" "{ref[0]}" (at 0 {halfheight + 3.81} 0) (effects (font (size 1.27 1.27))))',
        f'(property "Value" {q(component["part"])} (at 0 {-halfheight - 3.81} 0) (effects (font (size 1.27 1.27))))',
        f'(symbol "{name}_0_1" {graphic})',
        f'(symbol "{name}_1_1"',
    ]
    for p in pins:
        pin_name = (
            "~"
            if ref.startswith(("R", "C")) or (ref.startswith("D") and len(component["pins"]) == 2)
            else p["name"]
        )
        out.append(
            f"(pin {p['kind']} line (at {p['x']} {p['y']} {p['angle']}) (length 2.54) (name {q(pin_name)} (effects (font (size 1 1)))) (number {q(p['number'])} (effects (font (size 1 1)))))"
        )
    return "\n".join(out + ["))"])


def schematic():
    root = uid("root")
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "User" 1600 1300)',
        '(title_block (title "Standalone RMX - main rail generation") (rev "E14") (comment 1 "Schematic prototype; no routed board or bench validation"))',
        "(lib_symbols " + "\n".join(symbol(c) for c in COMPONENTS) + ")",
    ]
    for c in COMPONENTS:
        ref = c["ref"]
        x = c["x"]
        y = c["y"]
        pins, halfheight = geometry(c)
        out.append(
            f'(symbol (lib_id "RMX_E14:E14_{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})'
        )
        for key, value, py, hide in [
            ("Reference", ref, y - halfheight - 3.81, False),
            ("Value", c["part"], y + halfheight + 3.81, False),
            ("Footprint", c["footprint"], y, True),
            ("Datasheet", c["source"], y, True),
        ]:
            out.append(
                f"(property {q(key)} {q(value)} (at {x} {grid(py)} 0) (effects (font (size 1.27 1.27)) {'(hide yes)' if hide else ''}))"
            )
        for p in pins:
            out.append(f"(pin {q(p['number'])} (uuid {uid(ref + '.' + p['number'])}))")
        out.append(f'(instances (project "power_supply" (path "/{root}" (reference "{ref}") (unit 1)))))')
        for p in pins:
            px = grid(x + p["x"])
            py = grid(y - p["y"])
            ident = ref + "." + p["number"]
            if p["net"] is None:
                out.append(f"(no_connect (at {px} {py}) (uuid {uid('nc' + ident)}))")
                continue
            end = grid(px + (-5.08 if p["side"] == "L" else 5.08))
            out.append(
                f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {uid('wire' + ident)}))"
            )
            justify = "right" if p["side"] == "L" else "left"
            out.append(
                f"(label {q(p['net'])} (at {end} {py} 0) (effects (font (size 1 1)) (justify {justify} bottom)) (uuid {uid('label' + ident)}))"
            )
    # Input flags describe the off-board boundary; the other flags identify
    # converted rails reached through passive inductors/diodes (checked by nets).
    for index, net in enumerate(
        ("VIN_PROTECTED", "AGND", "RAW_P22", "RAW_N22", "RAW_P17", "RAW_N17", "5V_DIG_SRC", "V5_PRE")
    ):
        x = 30.48 + index * 40.64
        y = 1261.11
        flag = f"FLAG{index}"
        # Pin stacking is avoided: one explicit power-output flag per rail.
        # Define a minimal off-board virtual symbol in lib_symbols below.
        out.append(
            f'(symbol (lib_id "RMX_E14:SUPPLY_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid(flag)})'
            f'(property "Reference" "#{flag}" (at {x} {y - 2.54} 0) (effects (font (size 1 1)) (hide yes)))'
            f'(property "Value" "{net} source" (at {x} {y + 2.54} 0) (effects (font (size 1 1))))'
            f'(pin "1" (uuid {uid(flag + "pin")}))'
            f'(instances (project "power_supply" (path "/{root}" (reference "#{flag}") (unit 1)))))'
        )
        out.append(
            f'(label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(flag + "label")}))'
        )
    notes = NOTES
    for i, (x, y, text) in enumerate(notes):
        out.append(
            f"(text {q(text)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid('note' + str(i))}))"
        )
    result = "\n".join(out + ["(embedded_fonts no))"])
    result = result.replace("(lib_symbols ", "(lib_symbols " + flag_symbol(True) + "\n", 1)
    return result


def flag_symbol(prefix):
    name = ("RMX_E14:" if prefix else "") + "SUPPLY_FLAG"
    return f'''(symbol "{name}" (power) (pin_names (offset 0)) (in_bom no) (on_board no)
      (property "Reference" "#PWR" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
      (property "Value" "SUPPLY_FLAG" (at 0 2.54 0) (effects (font (size 1 1))))
      (symbol "SUPPLY_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0)
        (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'''


def main():
    ROOT.mkdir(exist_ok=True)
    (ROOT / "power_supply.kicad_sch").write_text(schematic() + "\n")
    (ROOT / "RMX_E14.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + "\n".join(symbol(c, False) for c in COMPONENTS)
        + "\n"
        + flag_symbol(False)
        + ")\n"
    )
    table = (
        '(sym_lib_table (version 7) (lib (name "RMX_E14") (type "KiCad") (uri "'
        + "${KIPRJMOD}"
        + '/RMX_E14.kicad_sym") (options "") (descr "E14 own symbols; manufacturer pin maps")))\n'
    )
    (ROOT / "sym-lib-table").write_text(table)
    libraries = sorted({c["footprint"].split(":")[0] for c in COMPONENTS if c["footprint"]})
    fp_root = "$" + "{KICAD10_FOOTPRINT_DIR}"
    entries = [
        f'(lib (name "{name}") (type "KiCad") (uri "{fp_root}/{name}.pretty") (options "") (descr "Standard KiCad library; package candidate"))'
        for name in libraries
    ]
    (ROOT / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    (ROOT / "power_supply.kicad_pro").write_text(
        json.dumps({"meta": {"filename": "power_supply.kicad_pro", "version": 1}}, indent=2) + "\n"
    )
    (ROOT / "components.json").write_text(json.dumps(COMPONENTS, indent=2) + "\n")
    (ROOT / "supply-map.json").write_text(json.dumps(dict(stages=STAGES, bucks=BUCKS), indent=2) + "\n")
    rows = io.StringIO()
    writer = csv.writer(rows)
    writer.writerow(["Reference", "Part_or_value", "Footprint_candidate", "Datasheet", "Design_note"])
    writer.writerows([c[k] for k in ("ref", "part", "footprint", "source", "note")] for c in COMPONENTS)
    (ROOT / "bom.csv").write_text(rows.getvalue())
    print(
        f"E14 native schematic generated: {len(COMPONENTS)} physical components; native and physical checks required."
    )


if __name__ == "__main__":
    main()
