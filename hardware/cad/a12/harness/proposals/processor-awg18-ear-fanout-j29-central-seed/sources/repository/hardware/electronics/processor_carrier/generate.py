#!/usr/bin/env python3
"""Generate E19 processor-carrier schematic and socket footprint."""

from ..common.flat_schematic import generate
from ..common.sexpr import a, children, first, read_sexpr, sexpr
from .spec import COMPONENTS, NOTES, ROOT


def main():
    generate(
        ROOT,
        "E19",
        "processor_carrier",
        COMPONENTS,
        NOTES,
        (1020, 680),
        [("5V_DIG", 40.64, 670.56), ("SEED_VIN", 101.6, 670.56), ("AGND", 162.56, 670.56)],
    )
    vendor = read_sexpr((ROOT / "vendor/DAISY_SEED.kicad_mod").read_text())
    # Preserve manufacturer pad numbering and centers; adapt the carrier holes
    # to the selected SSW socket's recommended 1.04mm finished-hole layout.
    # Remove legacy Seed graphics and STEP model: they are not Seed3 geometry.
    vendor[1] = "Seed3_Socket40"
    vendor = [
        node
        for node in vendor
        if not (isinstance(node, list) and node and (str(node[0]).startswith("fp_") or node[0] == "model"))
    ]
    for pad in children(vendor, "pad"):
        first(pad, "drill")[1] = a(1.04)
    for x0, y0, x1, y1, layer in [
        (-1.38, -1.37, 16.62, 49.63, "F.Fab"),
        (-1.205, -1.525, 1.205, 49.785, "F.Fab"),
        (14.035, -1.525, 16.445, 49.785, "F.Fab"),
        (-1.68, -2.07, 16.92, 50.33, "F.CrtYd"),
    ]:
        vendor.append(
            read_sexpr(
                f"(fp_rect (start {x0} {y0}) (end {x1} {y1}) "
                f'(stroke (width .05) (type default)) (fill none) (layer "{layer}"))'
            )
        )
    for prop in children(vendor, "property"):
        if prop[1] == "Value":
            prop[2] = "Seed3 + 2xSSW-120-02-G-S"
        if prop[1] == "Datasheet":
            prop[2] = "https://docs.daisy.audio/hardware/Seed3/"
    first(vendor, "descr")[1] = (
        "Seed3 + 2xSSW-120-02-G-S: official Daisy pad centers/numbering, 1.04mm socket holes per Samtec ssw-s.pdf. Seed3/USB/stack bounds modeled separately. Electrosmith MIT license in vendor/Electrosmith-LICENSE.txt."
    )
    local = ROOT / "RMX_Carrier.pretty"
    local.mkdir(exist_ok=True)
    (local / "Seed3_Socket40.kicad_mod").write_text(sexpr(vendor) + "\n")
    print(f"E19 generated {len(COMPONENTS)} components; native electrical/PCB/fit checks required.")


if __name__ == "__main__":
    main()
