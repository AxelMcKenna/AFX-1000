"""TI primary YWP0012A and DSE0006A board/stencil patterns, top view."""

from ...common.sexpr import children, first, read_sexpr, sexpr
from .manufacturer import ROOT


def base(name, value, source, box):
    x, y = box
    return read_sexpr(f'''(footprint "{name}" (version 20241229) (generator pcbnew)
      (layer "F.Cu") (attr smd)
      (property "Reference" "U" (at 0 {-y - 1}) (layer "F.Fab") (effects (font (size .6 .6))))
      (property "Value" "{value}" (at 0 {y + 1}) (layer "F.Fab") (effects (font (size .6 .6)) (hide yes)))
      (property "Datasheet" "{source}" (at 0 0) (layer "F.Fab") (effects (font (size .6 .6)) (hide yes)))
      (fp_rect (start {-x - 0.25} {-y - 0.25}) (end {x + 0.25} {y + 0.25})
        (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start {-x} {-y}) (end {x} {y})
        (stroke (width .05) (type default)) (fill none) (layer "F.Fab")))''')


def pad(number, x, y, w, h, mask):
    # TI R0.05 rounded rectangle, independent of solder-mask expansion.
    return read_sexpr(f'''(pad "{number}" smd roundrect (at {x} {y}) (size {w} {h})
      (layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio {0.05 / min(w, h)})
      (solder_mask_margin {mask}))''')


def efuse():
    fp = base(
        "TPS259482L_YWP0012A",
        "TPS259482LYWP",
        "https://www.ti.com/lit/ds/symlink/tps25948.pdf",
        (1.2355, 0.879),
    )
    # Package underside is flipped vertically into the §5 top pin diagram.
    # It is not rotated into the TI Q5B convention.
    for n, x, y, w, h in (
        (1, -1.06, -0.675, 0.2, 0.25),
        (2, -1.06, -0.225, 0.2, 0.2),
        (3, -1.06, 0.225, 0.2, 0.2),
        (4, -1.06, 0.675, 0.2, 0.25),
        (5, -0.476, 0.45, 0.5, 0.5),
        (6, 0.476, 0.45, 0.5, 0.5),
        (7, 1.06, 0.675, 0.2, 0.25),
        (8, 1.06, 0.225, 0.2, 0.2),
        (9, 1.06, -0.225, 0.2, 0.2),
        (10, 1.06, -0.675, 0.2, 0.25),
        (11, 0.476, -0.45, 0.5, 0.5),
        (12, -0.476, -0.45, 0.5, 0.5),
    ):
        fp.append(pad(n, x, y, w, h, 0.05))
    return fp


def supervisor():
    fp = base(
        "TPS389001_DSE0006A", "TPS389001DSET", "https://www.ti.com/lit/ds/symlink/tps3890.pdf", (0.775, 0.775)
    )
    for n, x, y, w in (
        (1, -0.55, -0.5, 0.8),
        (2, -0.6, 0, 0.7),
        (3, -0.6, 0.5, 0.7),
        (4, 0.6, 0.5, 0.7),
        (5, 0.6, 0, 0.7),
        (6, 0.6, -0.5, 0.7),
    ):
        # DSE drawing explicitly calls pads1..3 solder-mask-defined,4..6 NSMD.
        fp.append(pad(n, x, y, w, 0.25, -0.05 if n <= 3 else 0.05))
    return fp


def aup():
    fp = base(
        "SN74AUP2G08_DCU0008A",
        "SN74AUP2G08DCUR",
        "https://www.ti.com/lit/ds/symlink/sn74aup2g08.pdf",
        (1.15, 1.0),
    )
    # TI4225266/A copper/stencil:0.85x0.30, columns3.10 apart,0.50pitch.
    for n, x, y in (
        (1, -1.55, -0.75),
        (2, -1.55, -0.25),
        (3, -1.55, 0.25),
        (4, -1.55, 0.75),
        (5, 1.55, 0.75),
        (6, 1.55, 0.25),
        (7, 1.55, -0.25),
        (8, 1.55, -0.75),
    ):
        fp.append(pad(n, x, y, 0.85, 0.3, 0.05))
    # The courtyard must include the actual copper outer edges, not only body.
    rect = next(r for r in children(fp, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
    first(rect, "start")[1:] = [-2.225, -1.25]
    first(rect, "end")[1:] = [2.225, 1.25]
    return fp


def pw14():
    fp = base("TLV1824_PW0014A", "TLV1824PWR", "https://www.ti.com/lit/ds/symlink/tlv1824.pdf", (2.25, 2.55))
    rect = next(r for r in children(fp, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
    first(rect, "start")[1:] = [-3.9, -2.8]
    first(rect, "end")[1:] = [3.9, 2.8]
    for n in range(1, 15):
        x = -2.9 if n <= 7 else 2.9
        y = (n - 4) * 0.65 if n <= 7 else (11 - n) * 0.65
        fp.append(pad(n, x, round(y, 6), 1.5, 0.45, 0.05))
    return fp


def check_pw14(fp):
    pins = {str(p[1]): p for p in children(fp, "pad")}
    assert set(pins) == {str(i) for i in range(1, 15)}
    for n in range(1, 15):
        p = pins[str(n)]
        x = -2.9 if n <= 7 else 2.9
        y = round((n - 4) * 0.65 if n <= 7 else (11 - n) * 0.65, 6)
        assert tuple(map(float, first(p, "at")[1:])) == (x, y)
        assert tuple(map(float, first(p, "size")[1:])) == (1.5, 0.45)
        assert p[2:4] == ["smd", "roundrect"]
        assert abs(float(first(p, "roundrect_rratio")[1]) * 0.45 - 0.05) < 1e-10
        assert float(first(p, "solder_mask_margin")[1]) == 0.05
        assert set(first(p, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
    return dict(
        primary_drawing="PW0014A4220202/B12/2023",
        source_pdf_pages=[51, 52, 53],
        maximum_package_height_mm=1.2,
        maximum_additional_seat_allocation_mm=0.1,
        stencil_mm=0.125,
        original_pattern_visually_reviewed=True,
        assembler_accepted=False,
    )


def lvc14():
    fp = pw14()
    fp[1] = "SN74LVC14A_PW0014A"
    for prop in children(fp, "property"):
        if prop[1] == "Value":
            prop[2] = "SN74LVC14APWR"
        elif prop[1] == "Datasheet":
            prop[2] = "https://www.ti.com/lit/ds/symlink/sn74lvc14a.pdf"
    return fp


def check_lvc14(fp):
    result = check_pw14(fp)
    assert fp[1] == "SN74LVC14A_PW0014A"
    assert next(p[2] for p in children(fp, "property") if p[1] == "Value") == "SN74LVC14APWR"
    return dict(
        result,
        source_pdf_pages=[38, 39, 40],
        source_revision="SCAS285AC,April2022;package4220202/B12/2023",
        has_manufacturer_ioff_guarantee=False,
    )


def check_efuse(fp):
    pins = {str(p[1]): p for p in children(fp, "pad")}
    assert set(pins) == {str(i) for i in range(1, 13)}
    positions = {
        "1": (-1.06, -0.675),
        "2": (-1.06, -0.225),
        "3": (-1.06, 0.225),
        "4": (-1.06, 0.675),
        "5": (-0.476, 0.45),
        "12": (-0.476, -0.45),
        "6": (0.476, 0.45),
        "11": (0.476, -0.45),
        "7": (1.06, 0.675),
        "8": (1.06, 0.225),
        "9": (1.06, -0.225),
        "10": (1.06, -0.675),
    }
    for number, xy in positions.items():
        p = pins[number]
        assert tuple(map(float, first(p, "at")[1:])) == xy
        assert p[2:4] == ["smd", "roundrect"]
        assert set(first(p, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
        assert (
            abs(float(first(p, "roundrect_rratio")[1]) * min(map(float, first(p, "size")[1:])) - 0.05) < 1e-10
        )
    assert list(map(float, first(pins["1"], "at")[1:])) == [-1.06, -0.675]
    assert list(map(float, first(pins["4"], "at")[1:])) == [-1.06, 0.675]
    assert list(map(float, first(pins["5"], "at")[1:])) == [-0.476, 0.45]
    assert list(map(float, first(pins["12"], "at")[1:])) == [-0.476, -0.45]
    assert list(map(float, first(pins["6"], "at")[1:])) == [0.476, 0.45]
    assert list(map(float, first(pins["11"], "at")[1:])) == [0.476, -0.45]
    for n in ("5", "6", "11", "12"):
        assert list(map(float, first(pins[n], "size")[1:])) == [0.5, 0.5]
    for n in ("1", "4", "7", "10"):
        assert list(map(float, first(pins[n], "size")[1:])) == [0.2, 0.25]
    for n in ("2", "3", "8", "9"):
        assert list(map(float, first(pins[n], "size")[1:])) == [0.2, 0.2]
    assert all(float(first(p, "solder_mask_margin")[1]) == 0.05 for p in pins.values())
    return dict(
        primary_drawing="4228640/A 04/2022",
        stencil_mm=0.075,
        package_height_max_mm=0.376,
        mask_web_minimum_mm=0.10,
        footprint_manufacturer_reviewed=True,
        assembler_accepted=False,
    )


def check_supervisor(fp):
    pins = {str(p[1]): p for p in children(fp, "pad")}
    assert set(pins) == set("123456")
    positions = {
        "1": (-0.55, -0.5),
        "2": (-0.6, 0),
        "3": (-0.6, 0.5),
        "4": (0.6, 0.5),
        "5": (0.6, 0),
        "6": (0.6, -0.5),
    }
    for number, xy in positions.items():
        p = pins[number]
        assert tuple(map(float, first(p, "at")[1:])) == xy
        assert p[2:4] == ["smd", "roundrect"]
        assert set(first(p, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
        assert abs(float(first(p, "roundrect_rratio")[1]) * 0.25 - 0.05) < 1e-10
    assert list(map(float, first(pins["1"], "at")[1:])) == [-0.55, -0.5]
    assert list(map(float, first(pins["1"], "size")[1:])) == [0.8, 0.25]
    for n in "23456":
        assert list(map(float, first(pins[n], "size")[1:])) == [0.7, 0.25]
    for n in "123":
        assert float(first(pins[n], "solder_mask_margin")[1]) == -0.05
    for n in "456":
        assert float(first(pins[n], "solder_mask_margin")[1]) == 0.05
    return dict(
        primary_drawing="4220552/B 01/2024",
        stencil_mm=0.125,
        package_height_max_mm=0.8,
        footprint_manufacturer_reviewed=True,
        assembler_accepted=False,
    )


def check_aup(fp):
    pins = {str(p[1]): p for p in children(fp, "pad")}
    assert set(pins) == set("12345678")
    expected = {
        "1": (-1.55, -0.75),
        "2": (-1.55, -0.25),
        "3": (-1.55, 0.25),
        "4": (-1.55, 0.75),
        "5": (1.55, 0.75),
        "6": (1.55, 0.25),
        "7": (1.55, -0.25),
        "8": (1.55, -0.75),
    }
    for number, xy in expected.items():
        pad = pins[number]
        assert tuple(map(float, first(pad, "at")[1:])) == xy
        assert tuple(map(float, first(pad, "size")[1:])) == (0.85, 0.30)
        assert float(first(pad, "solder_mask_margin")[1]) == 0.05
        assert set(first(pad, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
        assert abs(float(first(pad, "roundrect_rratio")[1]) * 0.30 - 0.05) < 1e-10
    return dict(
        primary_drawing="4225266/A 09/2014",
        stencil_mm=0.125,
        mask_expansion_mm=0.05,
        assembler_accepted=False,
    )


def main():
    for name, fp, check in (
        ("TPS259482L_YWP0012A", efuse(), check_efuse),
        ("TPS389001_DSE0006A", supervisor(), check_supervisor),
        ("SN74AUP2G08_DCU0008A", aup(), check_aup),
        ("TLV1824_PW0014A", pw14(), check_pw14),
        ("SN74LVC14A_PW0014A", lvc14(), check_lvc14),
    ):
        if check:
            check(fp)
        (ROOT / "RMX_E28.pretty" / (name + ".kicad_mod")).write_text(sexpr(fp) + "\n")


if __name__ == "__main__":
    main()
