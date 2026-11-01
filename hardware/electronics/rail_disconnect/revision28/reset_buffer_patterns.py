"""Selected triple-Schmitt and bypass lands from inspected manufacturer drawings."""

from ...common.sexpr import a, children, first
from .positive_footprints import aup, base, pad

TRIPLE = "RMX_E28:SN74LVC3G17_DCU0008A"
BYPASS = "RMX_E28:KEMET_C0603_LevelB"


def triple():
    fp = aup()
    fp[1] = TRIPLE.split(":")[1]
    for p in children(fp, "property"):
        if p[1] == "Value":
            p[2] = "SN74LVC3G17DCUR"
        if p[1] == "Datasheet":
            p[2] = "https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf"
    # Package2.4x2.1 max, plus0.15/side possible mold flash and0.25 court.
    rect = next(r for r in children(fp, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
    first(rect, "start")[1:] = [a("-2.225"), a("-1.45")]
    first(rect, "end")[1:] = [a("2.225"), a("1.45")]
    return fp


def bypass():
    fp = base(
        BYPASS.split(":")[1],
        "C0603C104K4RACTU",
        "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
        (0.875, 0.475),
    )
    r = next(r for r in children(fp, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
    first(r, "start")[1:] = [a("-1.55"), a("-.75")]
    first(r, "end")[1:] = [a("1.55"), a(".75")]
    # KEMET2026-09-01 p12: C=centre offset.80,Y=horizontal.95,X=vertical1.00.
    for n, x in ((1, -0.8), (2, 0.8)):
        p = pad(n, x, 0, 0.95, 1, 0.05)
        fp.append(p)
    return fp


def validate(fp):
    p = {str(p[1]): p for p in children(fp, "pad")}
    if str(fp[1]).split(":")[-1] == TRIPLE.split(":")[-1]:
        assert set(p) == set(map(str, range(1, 9)))
        for n in range(1, 9):
            x = -1.55 if n <= 4 else 1.55
            y = (n - 2.5) * 0.5 if n <= 4 else (6.5 - n) * 0.5
            assert tuple(map(float, first(p[str(n)], "at")[1:3])) == (x, y)
            assert tuple(map(float, first(p[str(n)], "size")[1:])) == (0.85, 0.3)
            assert abs(float(first(p[str(n)], "roundrect_rratio")[1]) * 0.3 - 0.05) < 1e-9
    else:
        assert str(fp[1]).split(":")[-1] == BYPASS.split(":")[-1]
        assert set(p) == {"1", "2"}
        for n, x in (("1", -0.8), ("2", 0.8)):
            assert tuple(map(float, first(p[n], "at")[1:3])) == (x, 0)
            assert tuple(map(float, first(p[n], "size")[1:])) == (0.95, 1)
    for v in p.values():
        assert set(first(v, "layers")[1:]) == {"F.Cu", "F.Mask", "F.Paste"}
        assert float(first(v, "solder_mask_margin")[1]) == 0.05
    return {"manufacturer_land_example": True, "process_approved": False}
