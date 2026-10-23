#!/usr/bin/env python3
"""E18 native KiCad schematic and assembly list."""

import csv
import io
import json
import uuid

from .spec import COMPONENTS, NOTES, ROOT


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:E18:" + name))


def q(value):
    return json.dumps(str(value))


def geometry(c):
    passive = c["ref"].startswith(("R", "C"))
    span = 5.08 if passive else 15.24
    pins = []
    for side in ("L", "R"):
        group = [p for p in c["pins"] if p["side"] == side]
        for i, p in enumerate(group):
            pins.append(
                dict(
                    p,
                    x=-span if side == "L" else span,
                    y=round((len(group) - 1) * 2.54 - i * 5.08, 4),
                    angle=0 if side == "L" else 180,
                )
            )
    return pins, max(5.08, max(sum(p["side"] == side for p in pins) for side in ("L", "R")) * 2.54)


def symbol(c, prefix=True):
    name = "E18_" + c["ref"]
    pins, h = geometry(c)
    graphic = f"(rectangle (start -12.7 {h}) (end 12.7 {-h}) (stroke (width .254) (type default)) (fill (type none)))"
    if c["ref"].startswith("R"):
        graphic = "(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width .254) (type default)) (fill (type none)))"
    elif c["ref"].startswith("C"):
        graphic = "".join(
            "(polyline (pts "
            + "".join(f"(xy {x} {y})" for x, y in points)
            + ") (stroke (width .254) (type default)) (fill (type none)))"
            for points in [
                [(-2.54, 0), (-1.27, 0)],
                [(-1.27, -3.81), (-1.27, 3.81)],
                [(1.27, -3.81), (1.27, 3.81)],
                [(1.27, 0), (2.54, 0)],
            ]
        )
    out = [
        f'(symbol "{("RMX_E18:" if prefix else "") + name}" (pin_names (offset .508)) (in_bom yes) (on_board yes)',
        f'(property "Reference" "{c["ref"][0]}" (at 0 {h + 3.81} 0) (effects (font (size 1.27 1.27))))',
        f'(property "Value" {q(c["part"])} (at 0 {-h - 3.81} 0) (effects (font (size 1.27 1.27))))',
        f'(symbol "{name}_0_1" {graphic})',
        f'(symbol "{name}_1_1"',
    ]
    for p in pins:
        out.append(
            f"(pin {p['kind']} line (at {p['x']} {p['y']} {p['angle']}) (length 2.54) (name {q(p['name'])} (effects (font (size 1 1)))) (number {q(p['number'])} (effects (font (size 1 1)))))"
        )
    return "\n".join(out + ["))"])


def flag(prefix=True):
    return f'''(symbol "{"RMX_E18:" if prefix else ""}SUPPLY_FLAG" (power) (in_bom no) (on_board no)
    (property "Reference" "#PWR" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
    (property "Value" "SUPPLY_FLAG" (at 0 2.54 0) (effects (font (size 1 1))))
    (symbol "SUPPLY_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0)
      (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'''


def main():
    root = uid("root")
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "User" 560 425)',
        '(title_block (title "Standalone RMX - Digital control inputs") (rev "E18") (comment 1 "Prototype; physical scan, EMI, fit and complete system unverified"))',
        "(lib_symbols " + flag() + "\n" + "\n".join(symbol(c) for c in COMPONENTS) + ")",
    ]
    for c in COMPONENTS:
        ref, x, y = c["ref"], c["x"], c["y"]
        pins, h = geometry(c)
        out.append(
            f'(symbol (lib_id "RMX_E18:E18_{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})'
        )
        for k, v, py, hide in [
            ("Reference", ref, y - h - 3.81, False),
            ("Value", c["part"], y + h + 3.81, False),
            ("Footprint", c["footprint"], y, True),
            ("Datasheet", c["source"], y, True),
        ]:
            out.append(
                f"(property {q(k)} {q(v)} (at {x} {round(py, 4)} 0) (effects (font (size 1.27 1.27)) {'(hide yes)' if hide else ''}))"
            )
        out.extend(f"(pin {q(p['number'])} (uuid {uid(ref + '.' + p['number'])}))" for p in pins)
        out.append(f'(instances (project "control_inputs" (path "/{root}" (reference "{ref}") (unit 1)))))')
        for p in pins:
            px, py = round(x + p["x"], 4), round(y - p["y"], 4)
            id = ref + "." + p["number"]
            if p["net"] is None:
                out.append(f"(no_connect (at {px} {py}) (uuid {uid('nc' + id)}))")
                continue
            end = round(px + (-5.08 if p["side"] == "L" else 5.08), 4)
            out.append(
                f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {uid('w' + id)}))"
            )
            out.append(
                f"(label {q(p['net'])} (at {end} {py} 0) (effects (font (size 1 1)) (justify {'right' if p['side'] == 'L' else 'left'} bottom)) (uuid {uid('l' + id)}))"
            )
    for i, net in enumerate(("V3V3_IO", "AGND")):
        x, y = 30.48 + 50.8 * i, 411.48
        ref = f"#FLAG{i}"
        out.append(
            f'(symbol (lib_id "RMX_E18:SUPPLY_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid(ref)})'
            f'(property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'
            f'(property "Value" "{net} external" (at {x} {y + 2.54} 0) (effects (font (size 1 1))))'
            f'(pin "1" (uuid {uid(ref + "pin")})) (instances (project "control_inputs" (path "/{root}" (reference "{ref}") (unit 1)))))'
        )
        out.append(
            f'(label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(ref + "net")}))'
        )
    for i, (x, y, note) in enumerate(NOTES):
        out.append(
            f"(text {q(note)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid('note' + str(i))}))"
        )
    (ROOT / "control_inputs.kicad_sch").write_text("\n".join(out + ["(embedded_fonts no))"]) + "\n")
    (ROOT / "RMX_E18.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + flag(False)
        + "\n"
        + "\n".join(symbol(c, False) for c in COMPONENTS)
        + ")\n"
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table (version 7) (lib (name "RMX_E18") (type "KiCad") (uri "${KIPRJMOD}/RMX_E18.kicad_sym") (options "") (descr "E18 own MCP23017 manufacturer pin symbols")))\n'
    )
    libraries = sorted({c["footprint"].split(":")[0] for c in COMPONENTS})
    entries = [
        f'(lib (name "{n}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty") (options "") (descr "KiCad standard package candidate"))'
        for n in libraries
    ]
    entries.append(
        '(lib (name "RMX_Control") (type "KiCad") (uri "${KIPRJMOD}/RMX_Control.pretty") (options "") (descr "E18 mounting hole"))'
    )
    (ROOT / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    pro = ROOT / "control_inputs.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": pro.name, "version": 1}}, indent=2) + "\n")
    (ROOT / "components.json").write_text(json.dumps(COMPONENTS, indent=2) + "\n")
    rows = io.StringIO()
    writer = csv.writer(rows)
    writer.writerow(["Reference", "Part_or_value", "Footprint", "Source", "Note"])
    writer.writerows([c[k] for k in ("ref", "part", "footprint", "source", "note")] for c in COMPONENTS)
    (ROOT / "bom.csv").write_text(rows.getvalue())
    print("E18: generated15 circuit components and all32 front inputs; native verification required.")


if __name__ == "__main__":
    main()
