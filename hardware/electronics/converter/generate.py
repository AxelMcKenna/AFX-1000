#!/usr/bin/env python3
"""Generate E09 converter core, local rails and hardware qualification schematic."""

import csv
import io
import json
import uuid

from .spec import COMPONENTS, NOTES, ROOT


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E09:" + name))


def q(text):
    return json.dumps(str(text))


def grid(value):
    return round(value, 4)


def geometry(component):
    pins = []
    span = 5.08 if component["ref"].startswith(("R", "C", "D")) else 15.24
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
    name = "E09_" + ref
    pins, halfheight = geometry(component)
    prefix = "RMX_E09:" if prefixed else ""
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
    elif ref.startswith("D"):
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
        pin_name = "~" if ref.startswith(("R", "C", "D")) else p["name"]
        out.append(
            f"(pin {p['kind']} line (at {p['x']} {p['y']} {p['angle']}) (length 2.54) (name {q(pin_name)} (effects (font (size 1 1)))) (number {q(p['number'])} (effects (font (size 1 1)))))"
        )
    return "\n".join(out + ["))"])


def schematic():
    root = uid("root")
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "User" 760 560)',
        '(title_block (title "Standalone RMX - converter core and hardware qualification") (rev "E09") (comment 1 "Schematic prototype; no routed board or bench validation"))',
        "(lib_symbols " + "\n".join(symbol(c) for c in COMPONENTS) + ")",
    ]
    for c in COMPONENTS:
        ref = c["ref"]
        x = c["x"]
        y = c["y"]
        pins, halfheight = geometry(c)
        out.append(
            f'(symbol (lib_id "RMX_E09:E09_{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})'
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
        out.append(f'(instances (project "converter" (path "/{root}" (reference "{ref}") (unit 1)))))')
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
    # External rails enter J4; local analog LDO outputs are real power sources.
    for index, net in enumerate(("V3V3_IO", "V5_REG", "AGND")):
        x = 660.4 + index * 25.4
        y = 548.64
        flag = f"FLAG{index}"
        # Pin stacking is avoided: one explicit power-output flag per rail.
        # Define a minimal off-board virtual symbol in lib_symbols below.
        out.append(
            f'(symbol (lib_id "RMX_E09:SUPPLY_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid(flag)})'
            f'(property "Reference" "#{flag}" (at {x} {y - 2.54} 0) (effects (font (size 1 1)) (hide yes)))'
            f'(property "Value" "{net} external" (at {x} {y + 2.54} 0) (effects (font (size 1 1))))'
            f'(pin "1" (uuid {uid(flag + "pin")}))'
            f'(instances (project "converter" (path "/{root}" (reference "#{flag}") (unit 1)))))'
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
    name = ("RMX_E09:" if prefix else "") + "SUPPLY_FLAG"
    return f'''(symbol "{name}" (power) (pin_names (offset 0)) (in_bom no) (on_board no)
      (property "Reference" "#PWR" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
      (property "Value" "SUPPLY_FLAG" (at 0 2.54 0) (effects (font (size 1 1))))
      (symbol "SUPPLY_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0)
        (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'''


def supervisor_footprint():
    # Original copper geometry from TI DSE0006A example, revision01/2024.
    # The generic KiCad WSON-6 enlarges pin1; this part's drawing enlarges pin2.
    out = [
        '(footprint "TI_DSE0006A_TPS3890" (version 20241229) (generator pcbnew) (layer "F.Cu")',
        '(descr "Original TPS3890 DSE0006A example copper; mask/paste/process qualification pending") (attr smd)',
        '(property "Reference" "REF**" (at 0 -1.6) (layer "F.SilkS") (effects (font (size .7 .7) (thickness .1))))',
        '(property "Value" "TPS3890_DSE" (at 0 1.6) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))',
        '(fp_rect (start -1.25 -1) (end 1.25 1) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))',
    ]
    body = [(-0.75, -0.5), (-0.5, -0.75), (0.75, -0.75), (0.75, 0.75), (-0.75, 0.75), (-0.75, -0.5)]
    for a, b in zip(body, body[1:]):
        out.append(
            f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .1) (type default)) (layer "F.Fab"))'
        )
    for n, x, y in [
        (1, -0.6, -0.5),
        (2, -0.6, 0),
        (3, -0.6, 0.5),
        (4, 0.6, 0.5),
        (5, 0.6, 0),
        (6, 0.6, -0.5),
    ]:
        out.append(
            f'(pad "{n}" smd roundrect (at {x} {y}) (size {0.8 if n == 2 else 0.7} .25) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio .15))'
        )
    return "\n".join(out + [")"])


def main():
    ROOT.mkdir(exist_ok=True)
    (ROOT / "converter.kicad_sch").write_text(schematic() + "\n")
    (ROOT / "RMX_E09.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + "\n".join(symbol(c, False) for c in COMPONENTS)
        + "\n"
        + flag_symbol(False)
        + ")\n"
    )
    table = (
        '(sym_lib_table (version 7) (lib (name "RMX_E09") (type "KiCad") (uri "'
        + "${KIPRJMOD}"
        + '/RMX_E09.kicad_sym") (options "") (descr "E09 own symbols; manufacturer pin maps")))\n'
    )
    (ROOT / "sym-lib-table").write_text(table)
    libraries = sorted(
        {
            c["footprint"].split(":")[0]
            for c in COMPONENTS
            if c["footprint"] and not c["footprint"].startswith("RMX_Converter:")
        }
    )
    fp_root = "$" + "{KICAD10_FOOTPRINT_DIR}"
    entries = [
        f'(lib (name "{name}") (type "KiCad") (uri "{fp_root}/{name}.pretty") (options "") (descr "Standard KiCad library; package candidate"))'
        for name in libraries
    ]
    entries.append(
        '(lib (name "RMX_Converter") (type "KiCad") (uri "${KIPRJMOD}/RMX_Converter.pretty") (options "") (descr "Own manufacturer-example copper geometry"))'
    )
    local = ROOT / "RMX_Converter.pretty"
    local.mkdir(exist_ok=True)
    (local / "TI_DSE0006A_TPS3890.kicad_mod").write_text(supervisor_footprint() + "\n")
    (ROOT / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    (ROOT / "converter.kicad_pro").write_text(
        json.dumps({"meta": {"filename": "converter.kicad_pro", "version": 1}}, indent=2) + "\n"
    )
    (ROOT / "components.json").write_text(json.dumps(COMPONENTS, indent=2) + "\n")
    rows = io.StringIO()
    writer = csv.writer(rows)
    writer.writerow(["Reference", "Part_or_value", "Footprint_candidate", "Datasheet", "Design_note"])
    writer.writerows([c[k] for k in ("ref", "part", "footprint", "source", "note")] for c in COMPONENTS)
    (ROOT / "bom.csv").write_text(rows.getvalue())
    print(
        f"E09 native schematic generated: {len(COMPONENTS)} physical components; ERC/footprint/bench checks required."
    )


if __name__ == "__main__":
    main()
