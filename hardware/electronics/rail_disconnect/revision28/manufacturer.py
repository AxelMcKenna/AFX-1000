"""Source-derived TI Q5B lands, normalized to source-left/gate-bottom top view.

TI SLPS632 (March 2017) and SLPS488B (April 2017), sections 7.1–7.3.
The recommended drawing is rotated 180 degrees, never mirrored. Pin 4 is gate.
Logical schematic terminal 1 joins physical source pins 1/2/3; terminal 2 is
physical gate pin 4; terminal 3 joins physical drain pins 5/6/7/8 and exposed pad.
TI copyright and package notices remain with the linked original documents.
"""

import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "CSD18510Q5B": {
        "url": "https://www.ti.com/lit/ds/symlink/csd18510q5b.pdf",
        "document": "SLPS632, March 2017",
        "sections": ["7.1", "7.2", "7.3"],
    },
    "CSD18540Q5B": {
        "url": "https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf",
        "document": "SLPS488B, April 2017",
        "sections": ["7.1", "7.2", "7.3"],
    },
}


def rect(number, x, y, w, h, layers):
    return read_sexpr(
        f'(pad "{number}" smd rect (at {x} {y}) (size {w} {h}) '
        f"(layers {' '.join(json.dumps(v) for v in layers)}))"
    )


def q5b(part):
    assert part in SOURCES
    source = SOURCES[part]
    fp = read_sexpr(
        f'(footprint "{part}_TI_Q5B" (version 20241229) (generator pcbnew) '
        '(layer "F.Cu") (attr smd) '
        '(property "Reference" "Q" (at 0 -3.5) (layer "F.Fab") '
        "(effects (font (size .8 .8)))) "
        f'(property "Value" "{part}" (at 0 3.5) (layer "F.Fab") '
        "(effects (font (size .8 .8)) (hide yes))) "
        f'(property "Datasheet" "{source["url"]}" (at 0 0) (layer "F.Fab") '
        "(effects (font (size .8 .8)) (hide yes))))"
    )
    # Copper and mask only. Paste is independently drawn below per TI 7.3.
    for i, y in enumerate((-1.905, -0.635, 0.635, 1.905)):
        fp.append(rect("1" if i < 3 else "2", -2.770, y, 1.372, 0.710, ["F.Cu", "F.Mask"]))
    fp.append(rect("3", 0.941, 0, 3.850, 4.520, ["F.Cu", "F.Mask"]))
    for y in (-1.905, -0.635, 0.635, 1.905):
        fp.append(rect("3", 3.161, y, 0.590, 0.710, ["F.Cu", "F.Mask"]))
    for y in (-1.905, -0.635, 0.635, 1.905):
        fp.append(rect("", -2.757, y, 1.072, 0.562, ["F.Paste"]))
        fp.append(rect("", 2.910, y, 0.766, 0.508, ["F.Paste"]))
    for x in (-0.049, 1.595):
        for y in (-1.569, -0.523, 0.523, 1.569):
            fp.append(rect("", x, y, 1.294, 0.746, ["F.Paste"]))
    # Candidate process settings, not specified by the TI drawing.
    fp.append(read_sexpr("(solder_mask_margin .05)"))
    fp.append(
        read_sexpr(
            "(fp_rect (start -3.71 -2.8) (end 3.71 2.8) "
            '(stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))'
        )
    )
    fp.append(
        read_sexpr(
            "(fp_rect (start -3.05 -2.55) (end 3.05 2.55) "
            '(stroke (width .1) (type default)) (fill none) (layer "F.Fab"))'
        )
    )
    fp.append(read_sexpr('(fp_text user "G4" (at -2.77 2.55) (layer "F.Fab") (effects (font (size .5 .5))))'))
    return fp


def check_q5b(fp):
    """Independent drawing contract, including physical gate and paste apertures."""
    copper = [p for p in children(fp, "pad") if "F.Cu" in first(p, "layers")]
    paste = [p for p in children(fp, "pad") if "F.Paste" in first(p, "layers")]
    assert len(copper) == 9, "Four source/gate lands plus compound drain's five rectangles"
    assert len(paste) == 16 and all(not p[1] for p in paste), "Independent TI stencil windows"

    def dimensions(p):
        return (
            str(p[1]),
            *(round(float(x), 6) for x in first(p, "at")[1:3]),
            *(round(float(x), 6) for x in first(p, "size")[1:3]),
        )

    expected = {
        ("1", -2.77, -1.905, 1.372, 0.71),
        ("1", -2.77, -0.635, 1.372, 0.71),
        ("1", -2.77, 0.635, 1.372, 0.71),
        ("2", -2.77, 1.905, 1.372, 0.71),
        ("3", 0.941, 0.0, 3.85, 4.52),
        ("3", 3.161, -1.905, 0.59, 0.71),
        ("3", 3.161, -0.635, 0.59, 0.71),
        ("3", 3.161, 0.635, 0.59, 0.71),
        ("3", 3.161, 1.905, 0.59, 0.71),
    }
    assert {dimensions(p) for p in copper} == expected, "TI 7.2 copper/pin contract"
    assert all("F.Paste" not in first(p, "layers") for p in copper)
    expected_paste = (
        {("", -2.757, y, 1.072, 0.562) for y in (-1.905, -0.635, 0.635, 1.905)}
        | {("", 2.91, y, 0.766, 0.508) for y in (-1.905, -0.635, 0.635, 1.905)}
        | {("", x, y, 1.294, 0.746) for x in (-0.049, 1.595) for y in (-1.569, -0.523, 0.523, 1.569)}
    )
    assert {dimensions(p) for p in paste} == expected_paste, "TI 7.3 stencil contract"
    assert all(first(p, "layers")[1:] == ["F.Paste"] for p in paste)
    return {
        "copper_lands": 9,
        "stencil_apertures": 16,
        "physical_gate": 4,
        "drawing_transform": "top-view rotation 180 degrees; no mirror",
        "manufacturer_geometry_reviewed": True,
        "mask_and_stencil_process_approved": False,
    }


def main():
    folder = ROOT / "RMX_E28.pretty"
    folder.mkdir(exist_ok=True)
    for part in SOURCES:
        fp = q5b(part)
        check_q5b(fp)
        (folder / f"{part}_TI_Q5B.kicad_mod").write_text(sexpr(fp) + "\n")
    print("E28 TI Q5B copper and stencil generated; assembler/fabricator approval outstanding")


if __name__ == "__main__":
    main()
