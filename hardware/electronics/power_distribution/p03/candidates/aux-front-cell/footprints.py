"""Manufacturer-dimensioned P03 lands, kept local and independently inspectable."""

import shutil

from .spec import REPO, ROOT


def write():
    target = ROOT / "RMX_P03.pretty"
    target.mkdir(exist_ok=True)
    # These are actual retained package lands, not replacement package guesses.
    old = REPO / "hardware/electronics/power_supply/RMX_Power.pretty"
    for path in old.glob("*.kicad_mod"):
        shutil.copyfile(path, target / path.name)
    entries = []

    def rect(number, x, y, w, h, layers='"F.Cu" "F.Paste" "F.Mask"', margin=""):
        entries.append(f'(pad "{number}" smd rect (at {x} {y}) (size {w} {h}) (layers {layers}) {margin})')

    # TI4225171/D08/2022,RPY0014A example board layout,top view.
    # Two same-number rectangles form each L without a fictional thermal EP.
    # Paste is authored separately for the four reduced-coverage L terminals.
    for number, sign in ((1, -1), (5, 1)):
        rect(number, -1.3875, sign * 0.9875, 0.625, 0.225, '"F.Cu" "F.Mask"')
        rect(number, -1.2125, sign * 1.1625, 0.275, 0.575, '"F.Cu" "F.Mask"')
        rect("", -1.4125, sign * 0.9875, 0.575, 0.225, '"F.Paste"')
        rect("", -1.2125, sign * 1.1625, 0.275, 0.575, '"F.Paste"')
    for number, y in ((2, -0.5), (3, 0), (4, 0.5)):
        rect(number, -1.4125, y, 0.575, 0.25)
    for number, x, sign in ((6, -0.7, 1), (7, -0.2, 1), (14, -0.7, -1), (13, -0.2, -1)):
        rect(number, x, sign * 1.1625, 0.25, 0.575)
    for number, sign in ((8, 1), (12, -1)):
        rect(number, 0.35, sign * 1.025, 0.35, 0.85)
    for number, sign in ((9, 1), (11, -1)):
        rect(number, 0.975, sign * 1.025, 0.4, 0.85, '"F.Cu" "F.Mask"')
        rect(number, 1.4125, sign * 0.8, 0.575, 0.4, '"F.Cu" "F.Mask"')
        rect("", 0.975, sign * 1.025, 0.35, 0.85, '"F.Paste"')
        rect("", 1.4375, sign * 0.8, 0.525, 0.35, '"F.Paste"')
    # Pin10 is solder-mask defined. Three contiguous pieces form the C-shaped
    # copper; explicit mask and stencil polygons preserve the notch and avoid
    # internal seams from individually shrinking mask/paste rectangles.
    rect(10, 0.7125, 0, 1.275, 0.9, '"F.Cu"')
    rect(10, 1.55, -0.2875, 0.4, 0.325, '"F.Cu"')
    rect(10, 1.55, 0.2875, 0.4, 0.325, '"F.Cu"')

    def aperture(layer, points):
        # Numbered mask-only pad retains the SW-net association, unlike an
        # unassociated graphical mask polygon which KiCad reports as a bridge.
        number = "10" if layer == "F.Mask" else ""
        pts = " ".join(f"(xy {x - 0.2} {y})" for x, y in points)
        entries.append(
            f'(pad "{number}" smd custom (at .2 0) (size .01 .01) (layers "{layer}") (options (clearance outline) (anchor rect)) (primitives (gr_poly (pts {pts}) (width 0) (fill yes))))'
        )

    aperture(
        "F.Mask",
        [
            (0.125, -0.4),
            (1.7, -0.4),
            (1.7, -0.125),
            (1.35, -0.125),
            (1.35, 0.125),
            (1.7, 0.125),
            (1.7, 0.4),
            (0.125, 0.4),
        ],
    )
    aperture(
        "F.Paste",
        [
            (0.163, -0.35),
            (1.7, -0.35),
            (1.7, -0.125),
            (1.312, -0.125),
            (1.312, 0.125),
            (1.7, 0.125),
            (1.7, 0.35),
            (0.163, 0.35),
        ],
    )
    body = """(footprint "TPS543620_RPY0014A" (version 20241229) (generator pcbnew)
      (layer "F.Cu") (attr smd)
      (descr "TI RPY0014A board/stencil4225171D08/2022;14electricalterminals,noEP")
      (property "Reference" "REF**" (at 0 -2.4) (layer "F.SilkS") (effects (font (size .8 .8))))
      (property "Value" "TPS543620" (at 0 2.4) (layer "F.Fab") (effects (font (size .8 .8))))
      (fp_rect (start -1.25 -1.5) (end 1.25 1.5) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))
      (fp_rect (start -1.95 -1.7) (end 2 -0) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start -1.95 0) (end 2 1.7) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_circle (center -1.6 -1.8) (end -1.5 -1.8) (stroke (width .1) (type default)) (fill none) (layer "F.SilkS"))
    """
    # A single closed courtyard is required, not two touching rectangles.
    body = body.replace("(fp_rect (start -1.95 -1.7) (end 2 -0)", "(fp_rect (start -1.95 -1.7) (end 2 1.7)")
    body = body.replace(
        '      (fp_rect (start -1.95 0) (end 2 1.7) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))\n',
        "",
    )
    (target / "TPS543620_RPY0014A.kicad_mod").write_text(body + "\n".join(entries) + ")\n")
    (
        target / "Probe2_P2.54_D1.kicad_mod"
    ).write_text("""(footprint "Probe2_P2.54_D1" (version 20241229) (generator pcbnew)
      (layer "F.Cu") (attr smd exclude_from_bom)
      (property "Reference" "REF**" (at 0 -1) (layer "F.Fab") (effects (font (size .6 .6))))
      (property "Value" "Bare probe pads" (at 0 3.6) (layer "F.Fab") (effects (font (size .6 .6))))
      (fp_rect (start -.75 -.75) (end .75 3.29) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (pad "1" smd circle (at 0 0) (size 1 1) (layers "F.Cu" "F.Mask"))
      (pad "2" smd circle (at 0 2.54) (size 1 1) (layers "F.Cu" "F.Mask")))\n""")
    shared = (
        REPO
        / "hardware/electronics/rail_disconnect/revision28/RMX_E28.pretty/7466003R_M3_SMT_Annulus_NPTH.kicad_mod"
    )
    if not shared.exists():
        raise FileNotFoundError("The reviewed conditional shared annular stud land is required")
    # Identical electrical/manufacturing geometry across the real mating ports.
    # Its alternate4.7mmcopper-ID/stencil still needs manufacturer/assembler review.
    shutil.copyfile(shared, target / "Wurth_7466003R.kicad_mod")
