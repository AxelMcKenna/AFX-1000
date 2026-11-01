"""Native labeled schematics for component/pin specifications.

Board contracts and circuit choices belong to each board's independent verifier.
"""

import csv
import io
import json
import uuid

from .symbols import graphic_line


def geometry(component):
    span = 5.08 if component["ref"].startswith(("R", "C")) else 15.24
    pins = []
    for side in ("L", "R"):
        group = [p for p in component["pins"] if p["side"] == side]
        for index, pin in enumerate(group):
            pins.append(
                dict(
                    pin,
                    x=-span if side == "L" else span,
                    y=round((len(group) - 1) * 2.54 - index * 5.08, 4),
                    angle=0 if side == "L" else 180,
                )
            )
    return pins, max(5.08, max(sum(p["side"] == side for p in pins) for side in ("L", "R")) * 2.54)


def generate(root, revision, project, components, notes, page, flags):
    library = "RMX_" + revision

    def q(value):
        return json.dumps(str(value))

    def uid(value):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:" + revision + ":" + value))

    def symbol(component, prefix=True):
        name = revision + "_" + component["ref"]
        pins, h = geometry(component)
        shape = f"(rectangle (start -12.7 {h}) (end 12.7 {-h}) (stroke (width .254) (type default)) (fill (type none)))"
        if component["ref"].startswith("R"):
            shape = "(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width .254) (type default)) (fill (type none)))"
        elif component["ref"].startswith("C"):
            shape = "".join(
                graphic_line(points)
                for points in [
                    [(-2.54, 0), (-1.27, 0)],
                    [(-1.27, -3.81), (-1.27, 3.81)],
                    [(1.27, -3.81), (1.27, 3.81)],
                    [(1.27, 0), (2.54, 0)],
                ]
            )
        out = [
            f'(symbol "{(library + ":" if prefix else "") + name}" (pin_names (offset .508)) (in_bom yes) (on_board yes)',
            f'(property "Reference" "{component["ref"][0]}" (at 0 {h + 3.81} 0) (effects (font (size 1.27 1.27))))',
            f'(property "Value" {q(component["part"])} (at 0 {-h - 3.81} 0) (effects (font (size 1.27 1.27))))',
            f'(symbol "{name}_0_1" {shape})',
            f'(symbol "{name}_1_1"',
        ]
        for pin in pins:
            out.append(
                f"(pin {pin['kind']} line (at {pin['x']} {pin['y']} {pin['angle']}) (length 2.54) "
                f"(name {q(pin['name'])} (effects (font (size 1 1)))) (number {q(pin['number'])} (effects (font (size 1 1)))))"
            )
        return "\n".join(out + ["))"])

    def flag(prefix=True):
        return f'''(symbol "{library + ":" if prefix else ""}SUPPLY_FLAG" (power) (in_bom no) (on_board no)
        (property "Reference" "#PWR" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))
        (property "Value" "SUPPLY_FLAG" (at 0 2.54 0) (effects (font (size 1 1))))
        (symbol "SUPPLY_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0)
          (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'''

    ident = uid("root")
    out = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {ident}) (paper "User" {page[0]} {page[1]})',
        f'(title_block (title "Standalone RMX - {project}") (rev "{revision}") (comment 1 "Prototype; complete unit and physical validation unfinished"))',
        "(lib_symbols " + flag() + "\n" + "\n".join(symbol(c) for c in components) + ")",
    ]
    for component in components:
        ref, x, y = component["ref"], component["x"], component["y"]
        pins, h = geometry(component)
        out.append(
            f'(symbol (lib_id "{library}:{revision}_{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})'
        )
        for key, value, py, hide in [
            ("Reference", ref, y - h - 3.81, False),
            ("Value", component["part"], y + h + 3.81, False),
            ("Footprint", component["footprint"], y, True),
            ("Datasheet", component["source"], y, True),
        ]:
            out.append(
                f"(property {q(key)} {q(value)} (at {x} {round(py, 4)} 0) (effects (font (size 1.27 1.27)) {'(hide yes)' if hide else ''}))"
            )
        out.extend(f"(pin {q(p['number'])} (uuid {uid(ref + '.' + p['number'])}))" for p in pins)
        out.append(f'(instances (project "{project}" (path "/{ident}" (reference "{ref}") (unit 1)))))')
        for pin in pins:
            px, py = round(x + pin["x"], 4), round(y - pin["y"], 4)
            name = ref + "." + pin["number"]
            if pin["net"] is None:
                out.append(f"(no_connect (at {px} {py}) (uuid {uid('nc' + name)}))")
                continue
            end = round(px + (-5.08 if pin["side"] == "L" else 5.08), 4)
            out.append(
                f"(wire (pts (xy {px} {py}) (xy {end} {py})) (stroke (width 0) (type default)) (uuid {uid('w' + name)}))"
            )
            out.append(
                f"(label {q(pin['net'])} (at {end} {py} 0) (effects (font (size 1 1)) (justify {'right' if pin['side'] == 'L' else 'left'} bottom)) (uuid {uid('l' + name)}))"
            )
    for i, (net, x, y) in enumerate(flags):
        ref = f"#FLAG{i}"
        out.append(
            f'(symbol (lib_id "{library}:SUPPLY_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid(ref)})'
            f'(property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'
            f'(property "Value" "{net} external" (at {x} {y + 2.54} 0) (effects (font (size 1 1))))'
            f'(pin "1" (uuid {uid(ref + "pin")})) (instances (project "{project}" (path "/{ident}" (reference "{ref}") (unit 1)))))'
        )
        out.append(
            f'(label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(ref + "net")}))'
        )
    out.extend(
        f"(text {q(text)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid('note' + str(i))}))"
        for i, (x, y, text) in enumerate(notes)
    )
    root.mkdir(exist_ok=True)
    (root / (project + ".kicad_sch")).write_text("\n".join(out + ["(embedded_fonts no))"]) + "\n")
    (root / (library + ".kicad_sym")).write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + flag(False)
        + "\n"
        + "\n".join(symbol(c, False) for c in components)
        + ")\n"
    )
    (root / "sym-lib-table").write_text(
        f'(sym_lib_table (version 7) (lib (name "{library}") (type "KiCad") (uri "${{KIPRJMOD}}/{library}.kicad_sym") (options "") (descr "Own pin-contract symbols")))\n'
    )
    (root / "components.json").write_text(json.dumps(components, indent=2) + "\n")
    rows = io.StringIO()
    writer = csv.writer(rows)
    writer.writerow(["Reference", "Part_or_value", "Footprint", "Source", "Note"])
    writer.writerows([c[k] for k in ("ref", "part", "footprint", "source", "note")] for c in components)
    (root / "bom.csv").write_text(rows.getvalue())
    libraries = sorted({c["footprint"].split(":")[0] for c in components})
    entries = []
    for name in libraries:
        path = (
            "${KIPRJMOD}/" + name + ".pretty"
            if name.startswith("RMX_")
            else "${KICAD10_FOOTPRINT_DIR}/" + name + ".pretty"
        )
        entries.append(
            f'(lib (name "{name}") (type "KiCad") (uri "{path}") (options "") (descr "Package candidate"))'
        )
    (root / "fp-lib-table").write_text("(fp_lib_table (version 7)\n" + "\n".join(entries) + ")\n")
    pro = root / (project + ".kicad_pro")
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": pro.name, "version": 1}}, indent=2) + "\n")
