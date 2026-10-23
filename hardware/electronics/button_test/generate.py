#!/usr/bin/env python3
"""Generate the B01 passive button test PCB and matching native KiCad schematic.

Dimensions come from the fit fixture and manufacturer's top-view B3F drawing.
Own small footprints/symbols are embedded and supplied locally; no global
library installation is required. Native ERC/DRC must follow generation.
"""

import json
import uuid
from pathlib import Path

from hardware.cad.button_fixture import VALUES

ROOT = Path(__file__).resolve().parent
CAD = ROOT.parents[1] / "cad"


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rmx:B01:" + name))


def text(value, x, y, layer="F.SilkS", size=0.8):
    return f'(fp_text user "{value}" (at {x} {y}) (layer "{layer}") (effects (font (size {size} {size}) (thickness 0.12))))'


def footprint(name, reference, value, pads, body, placed=None, nets=None):
    pos = f"(at {placed[0]} {placed[1]})" if placed else ""

    def prop(key, val, y, layer, x=0):
        return f'(property "{key}" "{val}" (at {x} {y}) (layer "{layer}") (effects (font (size 0.8 0.8) (thickness 0.12))))'

    parts = [
        f'(footprint "RMX_Button:{name}" (version 20240108) (generator pcbnew) (layer "F.Cu") {pos}',
        "(attr through_hole)",
        prop("Reference", reference, 0, "F.SilkS", -4.2)
        if name == "WirePair254"
        else prop("Reference", reference, -4.6, "F.SilkS"),
        prop("Value", value, 4.7, "F.Fab"),
    ]
    for number, x, y, netname in pads:
        net = f'(net {1 if netname == "SIGNAL" else 2} "/{netname}")' if nets else ""
        parts.append(
            f'(pad "{number}" thru_hole circle (at {x} {y}) (size 1.9 1.9) (drill 1) (layers "*.Cu" "*.Mask") {net})'
        )
    for layer, clear in [("F.SilkS", 0), ("F.CrtYd", 0.5)]:
        x, y, w, h = body
        if name == "B3F1000" and layer == "F.SilkS":
            for a, b in [
                ((-2, -3.4), (2, -3.4)),
                ((-2, 3.4), (2, 3.4)),
                ((-4.1, -0.7), (-4.1, 0.7)),
                ((4.1, -0.7), (4.1, 0.7)),
            ]:
                parts.append(
                    f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .12) (type solid)) (layer "{layer}"))'
                )
        else:
            parts.append(
                f'(fp_rect (start {x - clear} {y - clear}) (end {x + w + clear} {y + h + clear}) (stroke (width {0.12 if layer == "F.SilkS" else 0.05}) (type solid)) (fill none) (layer "{layer}"))'
            )
    parts.append(")")
    return "\n".join(parts)


SWITCH_PADS = [
    ("1", 3.25, 2.25, "GND"),
    ("2", -3.25, 2.25, "GND"),
    ("3", 3.25, -2.25, "SIGNAL"),
    ("4", -3.25, -2.25, "SIGNAL"),
]
HEADER_PADS = [("1", -1.27, 0, "SIGNAL"), ("2", 1.27, 0, "GND")]


def mount(reference="REF**", x=None):
    pos = f"(at {x} 50)" if x is not None else ""
    return f'''(footprint "RMX_Button:M2_Clearance" (version 20240108) (generator pcbnew) (layer "F.Cu") {pos}
      (attr board_only exclude_from_pos_files exclude_from_bom)
      (property "Reference" "{reference}" (at 0 -3.2) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))
      (property "Value" "M2" (at 0 3.2) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (fp_circle (center 0 0) (end 2.4 0) (stroke (width .12) (type solid)) (fill none) (layer "F.SilkS"))
      (fp_circle (center 0 0) (end 3 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))'''


def board():
    parts = [
        "(kicad_pcb (version 20240108) (generator pcbnew)",
        '(general (thickness 1.6)) (paper "A4")',
        '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))',
        '(setup (pad_to_mask_clearance 0)) (net 0 "") (net 1 "/SIGNAL") (net 2 "/GND")',
        footprint("B3F1000", "SW1", "B3F-1000", SWITCH_PADS, [-3, -3, 6, 6], (50, 50), True),
        footprint("WirePair254", "J1", "SIGNAL_GND", HEADER_PADS, [-2.5, -1.25, 5, 2.5], (50, 56), True),
    ]
    for index, x in enumerate((50 - VALUES["mount_pitch"] / 2, 50 + VALUES["mount_pitch"] / 2), 1):
        parts.append(mount(f"H{index}", x))
    for a, b in [((34, 42), (66, 42)), ((66, 42), (66, 58)), ((66, 58), (34, 58)), ((34, 58), (34, 42))]:
        parts.append(
            f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))'
        )
    routes = [
        ("F.Cu", "SIGNAL", [(46.75, 47.75), (53.25, 47.75), (56, 47.75), (56, 54), (48.73, 54), (48.73, 56)]),
        ("B.Cu", "GND", [(46.75, 52.25), (51.27, 52.25), (53.25, 52.25)]),
        ("B.Cu", "GND", [(51.27, 52.25), (51.27, 56)]),
    ]
    for layer, net, points in routes:
        for a, b in zip(points, points[1:]):
            parts.append(
                f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width .35) (layer "{layer}") (net {1 if net == "SIGNAL" else 2}))'
            )
    for label, x, y, size in [("B01 FIT TEST", 50, 43.4, 1), ("1:S  2:G", 50, 54, 0.8)]:
        parts.append(
            f'(gr_text "{label}" (at {x} {y}) (layer "F.SilkS") (effects (font (size {size} {size}) (thickness .12))))'
        )
    return "\n".join(parts + [")"])


def lib_symbol(name, pins, rect):
    def prop(k, val, y):
        return f'(property "{k}" "{val}" (at 0 {y} 0) (effects (font (size 1.27 1.27))))'

    x1, y1, x2, y2 = rect
    s = [
        f'(symbol "RMX:{name}" (pin_names (offset 0)) (in_bom yes) (on_board yes)',
        prop("Reference", "SW" if name == "B3F1000" else "J", 6),
        prop("Value", name, -6),
        f'(symbol "{name}_0_1" '
        + (
            "".join(
                "(polyline (pts "
                + "".join(f"(xy {x} {y})" for x, y in line)
                + ") (stroke (width .254) (type default)) (fill (type none)))"
                for line in [
                    [(-2.54, 2.54), (2.54, 2.54)],
                    [(-2.54, -2.54), (2.54, -2.54)],
                    [(0, -2.54), (1.27, 1.27)],
                ]
            )
            if name == "B3F1000"
            else f"(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width .254) (type default)) (fill (type none)))"
        )
        + ")",
        f'(symbol "{name}_1_1"',
    ]
    for number, x, y, angle in pins:
        s.append(
            f'(pin passive line (at {x} {y} {angle}) (length 2.54) (name "~" (effects (font (size 1 1)))) (number "{number}" (effects (font (size 1 1)))))'
        )
    return "\n".join(s + ["))"])


def schematic():
    root = uid("schematic")
    swpins = [("1", 5.08, -2.54, 180), ("2", -5.08, -2.54, 0), ("3", 5.08, 2.54, 180), ("4", -5.08, 2.54, 0)]
    jpins = [("1", -5.08, 0, 0), ("2", -5.08, -2.54, 0)]
    sw = lib_symbol("B3F1000", swpins, (-2.54, 3.81, 2.54, -3.81))
    j = lib_symbol("WirePair254", jpins, (-2.54, 1.27, 2.54, -3.81))
    s = [
        f'(kicad_sch (version 20250114) (generator eeschema) (uuid {root}) (paper "A4")',
        '(title_block (title "B01 button fit / closure test") (rev "B01") (comment 1 "Passive switch fixture only; no audio or power circuitry"))',
        f"(lib_symbols {sw} {j})",
    ]
    for ref, name, x, y, pins, fp, value in [
        ("SW1", "B3F1000", 100.33, 80.01, swpins, "B3F1000", "B3F-1000"),
        ("J1", "WirePair254", 139.7, 80.01, jpins, "WirePair254", "SIGNAL_GND"),
    ]:
        s.append(
            f'(symbol (lib_id "RMX:{name}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})'
        )
        for key, val, py, hide in [
            ("Reference", ref, y - 6, False),
            ("Value", value, y + 6, False),
            ("Footprint", "RMX_Button:" + fp, y, True),
        ]:
            s.append(
                f'(property "{key}" "{val}" (at {x} {py} 0) (effects (font (size 1.27 1.27)) {"(hide yes)" if hide else ""}))'
            )
        for number, *_ in pins:
            s.append(f'(pin "{number}" (uuid {uid(ref + number)}))')
        s.append(f'(instances (project "button_test" (path "/{root}" (reference "{ref}") (unit 1)))))')
    ends = [
        (105.41, 77.47, 110.49, "SIGNAL"),
        (95.25, 77.47, 90.17, "SIGNAL"),
        (105.41, 82.55, 110.49, "GND"),
        (95.25, 82.55, 90.17, "GND"),
        (134.62, 80.01, 129.54, "SIGNAL"),
        (134.62, 82.55, 129.54, "GND"),
    ]
    for i, (x, y, end, net) in enumerate(ends):
        s.append(
            f"(wire (pts (xy {x} {y}) (xy {end} {y})) (stroke (width 0) (type default)) (uuid {uid('wire' + str(i))}))"
        )
        s.append(
            f'(label "{net}" (at {end} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid("label" + str(i))}))'
        )
    s.append(
        f'(text "J1: pin 1 to a pulled-up logic input; pin 2 to GND.\\nFor bench feel/closure testing only. Verify switch pin pairs before assembly." (at 100 102 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid("note")}))'
    )
    return "\n".join(s + ["(embedded_fonts no))"])


def main():
    lib = ROOT / "RMX_Button.pretty"
    lib.mkdir(exist_ok=True)
    (lib / "B3F1000.kicad_mod").write_text(
        footprint("B3F1000", "REF**", "B3F-1000", SWITCH_PADS, [-3, -3, 6, 6]) + "\n"
    )
    (lib / "WirePair254.kicad_mod").write_text(
        footprint("WirePair254", "REF**", "SIGNAL_GND", HEADER_PADS, [-2.5, -1.25, 5, 2.5]) + "\n"
    )
    (lib / "M2_Clearance.kicad_mod").write_text(mount() + "\n")
    (ROOT / "fp-lib-table").write_text(
        '(fp_lib_table (version 7) (lib (name "RMX_Button") (type "KiCad") (uri "${KIPRJMOD}/RMX_Button.pretty") (options "") (descr "B01 own footprints from manufacturer drawing")))\n'
    )
    (ROOT / "button_test.kicad_pcb").write_text(board() + "\n")
    (ROOT / "button_test.kicad_sch").write_text(schematic() + "\n")
    swpins = [("1", 5.08, -2.54, 180), ("2", -5.08, -2.54, 0), ("3", 5.08, 2.54, 180), ("4", -5.08, 2.54, 0)]
    jpins = [("1", -5.08, 0, 0), ("2", -5.08, -2.54, 0)]
    symbols = (
        lib_symbol("B3F1000", swpins, (-2.54, 3.81, 2.54, -3.81))
        + "\n"
        + lib_symbol("WirePair254", jpins, (-2.54, 1.27, 2.54, -3.81))
    )
    (ROOT / "RMX.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator kicad_symbol_editor)\n"
        + symbols.replace('(symbol "RMX:', '(symbol "')
        + ")\n"
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table (version 7) (lib (name "RMX") (type "KiCad") (uri "${KIPRJMOD}/RMX.kicad_sym") (options "") (descr "B01 own passive symbols")))\n'
    )
    pro = {
        "board": {
            "design_settings": {
                "rules": {
                    "min_clearance": 0.25,
                    "min_track_width": 0.25,
                    "min_copper_edge_clearance": 0.3,
                    "min_through_hole_diameter": 0.3,
                    "min_via_annular_width": 0.15,
                    "min_hole_clearance": 0.25,
                }
            }
        },
        "net_settings": {
            "classes": [
                {
                    "name": "Default",
                    "clearance": 0.25,
                    "track_width": 0.35,
                    "via_diameter": 0.6,
                    "via_drill": 0.3,
                    "bus_width": 12,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "wire_width": 6,
                }
            ]
        },
        "meta": {"filename": "button_test.kicad_pro", "version": 1},
    }
    (ROOT / "button_test.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    print("Generated B01 native KiCad PCB/schematic; run native DRC/ERC before accepting.")


if __name__ == "__main__":
    main()
