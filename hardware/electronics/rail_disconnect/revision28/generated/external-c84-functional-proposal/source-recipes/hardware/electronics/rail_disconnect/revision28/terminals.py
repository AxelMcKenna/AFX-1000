"""Real quiet-return attachment candidate: Würth 7466003R SMT M3 stud.

The official drawing's visual review and assembler approval remain pending.
OD 8.5 copper and NPTH 4.2 derive from manufacturer drawing 001.004. Copper
ID 4.7 is our explicit 0.25 mm fabrication-clearance choice, not a quoted land.
"""

from ...common.sexpr import children, first, read_sexpr, sexpr
from .manufacturer import ROOT

PORTS = {"J7": (131.0, 39.5, "analog"), "J8": (124.0, 21.0, "digital")}
POWER_PORTS = {"J10": (49.5, 17.5, "V5_REG_SRC"), "J11": (115.0, 6.0, "5V_DIG_SRC")}
ALL_TERMINALS = {ref: (x, y, "AGND") for ref, (x, y, _) in PORTS.items()} | POWER_PORTS


def terminal():
    return read_sexpr("""(footprint "7466003R_M3_SMT_Annulus_NPTH" (version 20241229)
      (generator pcbnew) (layer "F.Cu") (attr smd)
      (property "Reference" "J" (at 0 -5.5) (layer "F.Fab") (effects (font (size .8 .8))))
      (property "Value" "7466003R" (at 0 5.5) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      (property "Datasheet" "https://www.we-online.com/components/products/datasheet/7466003R.pdf"
       (at 0 0) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      (pad "1" smd custom (at 3.3 0) (size .2 .2) (layers "F.Cu" "F.Mask" "F.Paste")
        (options (clearance outline) (anchor circle))
        (primitives (gr_circle (center -3.3 0) (end 0 0) (width 1.9) (fill no))))
      (pad "" np_thru_hole circle (at 0 0) (size 4.2 4.2) (drill 4.2) (layers "*.Cu" "*.Mask"))
      (solder_mask_margin .05)
      (fp_circle (center 0 0) (end 3.5 0) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))
      (fp_rect (start -5 -5) (end 5 5) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start -5 -5) (end 5 5) (stroke (width .05) (type default)) (fill none) (layer "B.CrtYd")))""")


def check_terminal(fp):
    pads = children(fp, "pad")
    assert len(pads) == 2
    electrical, hole = pads
    assert electrical[1:4] == ["1", "smd", "custom"]
    assert first(electrical, "layers")[1:] == ["F.Cu", "F.Mask", "F.Paste"]
    circle = first(first(electrical, "primitives"), "gr_circle")
    assert list(map(float, first(circle, "center")[1:])) == [-3.3, 0]
    assert list(map(float, first(circle, "end")[1:])) == [0, 0]
    assert float(first(circle, "width")[1]) == 1.9
    assert not hole[1] and hole[2] == "np_thru_hole"
    assert float(first(hole, "drill")[1]) == 4.2
    assert not children(hole, "net"), "The locating hole is not a plated electrical terminal"
    return dict(
        copper_od_mm=8.5,
        copper_id_mm=4.7,
        npth_mm=4.2,
        access_mm=[10, 10],
        body_od_mm=7,
        top_height_mm=5,
        spigot_mm=[4, 1],
        maximum_torque_nm=0.5,
        contact_resistance_limit_mohm=0.35,
        contact_resistance_measured=False,
        original_drawing_visual_reviewed=False,
        assembler_approved=False,
    )


def main():
    fp = terminal()
    check_terminal(fp)
    (ROOT / "RMX_E28.pretty/7466003R_M3_SMT_Annulus_NPTH.kicad_mod").write_text(sexpr(fp) + "\n")


if __name__ == "__main__":
    main()
