#!/usr/bin/env python3
"""Native E20 schematic and dimensioned DAP32 footprint candidate."""

from ..common.flat_schematic import generate
from .spec import COMPONENTS, NOTES, ROOT


def footprint():
    # Signal lands and mask opening follow TI's current DAP0032C example.
    # Four stencil windows provide approximately73% coverage; assembler review open.
    out = [
        '(footprint "TLC5947_DAP0032C" (version 20241229) (generator pcbnew) (layer "F.Cu")',
        '(descr "TLC5947 DAP32: TI DAP0032C signal lands; 5.2x11 ground copper, 3.04x3.74 mask opening, four stencil windows. Physical package/assembly qualification pending.")',
        "(attr smd)",
        '(property "Reference" "REF**" (at 0 -6.5) (layer "F.Fab") (effects (font (size .8 .8))))',
        '(property "Value" "TLC5947DAPR" (at 0 6.5) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))',
        '(fp_rect (start -3.1 -5.5) (end 3.1 5.5) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))',
        '(fp_rect (start -4.75 -6) (end 4.75 6) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))',
    ]
    for n in range(1, 33):
        x, y = (-3.75, -4.875 + 0.65 * (n - 1)) if n <= 16 else (3.75, 4.875 - 0.65 * (n - 17))
        out.append(f'(pad "{n}" smd rect (at {x} {y:.6f}) (size 1.5 .45) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out += [
        '(pad "33" smd rect (at 0 0) (size 5.2 11) (layers "F.Cu"))',
        '(pad "" smd rect (at 0 0) (size 3.04 3.74) (layers "F.Mask"))',
    ]
    for x in (-0.7, 0.7):
        for y in (-0.9, 0.9):
            out.append(f'(pad "" smd rect (at {x} {y}) (size 1.3 1.6) (layers "F.Paste"))')
    return "\n".join(out + [")"]) + "\n"


def main():
    generate(
        ROOT,
        "E20",
        "led_driver",
        COMPONENTS,
        NOTES,
        (1040, 880),
        [("AGND", 30.48, 868.68), ("5V_DIG", 91.44, 868.68), ("V3V3_IO", 152.4, 868.68)],
    )
    local = ROOT / "RMX_LED.pretty"
    local.mkdir(exist_ok=True)
    (local / "TLC5947_DAP0032C.kicad_mod").write_text(footprint())
    print(
        f"E20 generated {len(COMPONENTS)} components; independent contracts/native ERC/PCB checks required."
    )


if __name__ == "__main__":
    main()
