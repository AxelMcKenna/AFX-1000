"""Selected real C0G timing capacitors; KEMETC1003_C0G2025-02-20.

Table1A/1B validates the actual voltage/capacitance/case combinations. Table2A
provides thickness codes; Table3LevelB provides complete copper/courtyard.
The rejected0805 placeholders had no accepted manufacturer combination.
"""

from ...common.sexpr import children, first, read_sexpr, sexpr
from .manufacturer import ROOT

SOURCE = "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf"
CAPS = {
    "100nF 50V C0G 5%": dict(
        mpn="C1210C104J5GACTU",
        case="1210",
        footprint="KEMET_C1210_LevelB",
        capacitance_f=100e-9,
        max_height_mm=1.4,
        pad_width_mm=2.7,
        courtyard_height_mm=3.2,
        body_max_mm=[3.4, 2.7],
        availability_table="1B",
        thickness_code="FG",
    ),
    "47nF 50V C0G 5%": dict(
        mpn="C1206C473J5GACTU",
        case="1206",
        footprint="KEMET_C1206_LevelB",
        capacitance_f=47e-9,
        max_height_mm=1.2,
        pad_width_mm=1.8,
        courtyard_height_mm=2.3,
        body_max_mm=[3.4, 1.8],
        availability_table="1A",
        thickness_code="EE",
    ),
}


def footprint(kind):
    c = CAPS[kind]
    height = c["courtyard_height_mm"] / 2
    bodyx, bodyy = (v / 2 for v in c["body_max_mm"])
    fp = read_sexpr(f'''(footprint "{c["footprint"]}" (version 20241229) (generator pcbnew) (layer "F.Cu") (attr smd)
      (property "Reference" "C" (at 0 {-height - 1}) (layer "F.Fab") (effects (font (size .6 .6))))
      (property "Value" "{c["mpn"]}" (at 0 {height + 1}) (layer "F.Fab") (effects (font (size .6 .6)) (hide yes)))
      (property "Datasheet" "{SOURCE}" (at 0 0) (layer "F.Fab") (effects (font (size .6 .6)) (hide yes)))
      (pad "1" smd rect (at -1.5 0) (size 1.15 {c["pad_width_mm"]}) (layers "F.Cu" "F.Mask" "F.Paste"))
      (pad "2" smd rect (at 1.5 0) (size 1.15 {c["pad_width_mm"]}) (layers "F.Cu" "F.Mask" "F.Paste"))
      (solder_mask_margin .05)
      (fp_rect (start -2.35 {-height}) (end 2.35 {height}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start {-bodyx} {-bodyy}) (end {bodyx} {bodyy}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab")))''')
    return fp


def check(fp, kind):
    c = CAPS[kind]
    pads = children(fp, "pad")
    assert len(pads) == 2
    for index, p in enumerate(pads):
        assert p[1:4] == [str(index + 1), "smd", "rect"]
        assert tuple(map(float, first(p, "at")[1:])) == ((-1.5, 0) if index == 0 else (1.5, 0))
        assert tuple(map(float, first(p, "size")[1:])) == (1.15, c["pad_width_mm"])
        assert set(first(p, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
    assert float(first(fp, "solder_mask_margin")[1]) == 0.05
    return dict(
        c,
        source=SOURCE,
        source_revision="2025-02-20",
        land_level="B",
        original_drawing_visually_reviewed=True,
        paste_coverage_fraction_candidate=1.0,
        stencil_thickness_and_process_accepted=False,
        assembler_accepted=False,
        procurement_accepted=False,
    )


def main():
    for kind, c in CAPS.items():
        fp = footprint(kind)
        check(fp, kind)
        (ROOT / "RMX_E28.pretty" / (c["footprint"] + ".kicad_mod")).write_text(sexpr(fp) + "\n")


if __name__ == "__main__":
    main()
