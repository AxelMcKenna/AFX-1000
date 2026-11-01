"""TI DCU0008A example land pattern; retain original conservative courtyard."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original = ROOT / "sources/footprints/Package_SO__VSSOP-8_2.3x2mm_P0.5mm.kicad_mod"
    fp = read_sexpr(original.read_text())
    fp[1] = "TI_DCU0008A"
    first(fp, "descr")[1] = "TI DCU0008A example land: 0.85x0.30, pitch0.5, row3.1, R0.05. Original conservative courtyard."
    pads = children(fp, "pad")
    assert len(pads) == 8
    for pad in pads:
        n = int(pad[1])
        first(pad, "at")[1:3] = [-1.55 if n <= 4 else 1.55, -.75 + .5 * (n - 1) if n <= 4 else .75 - .5 * (n - 5)]
        first(pad, "size")[1:3] = [.85, .30]
        first(pad, "roundrect_rratio")[1] = .05 / .30
        pad.append([a("solder_mask_margin"), .025])
    folder = ROOT / "NF03P_Manufacturer.pretty"
    folder.mkdir(exist_ok=True)
    target = folder / "TI_DCU0008A.kicad_mod"
    target.write_text(sexpr(fp) + "\n")
    report = dict(
        source_footprint_sha256=sha(original), custom_footprint_sha256=sha(target),
        primary_pdf_sha256=sha(ROOT / "sources/sn74aup1g74.pdf"),
        primary_url="https://www.ti.com/lit/ds/symlink/sn74aup1g74.pdf",
        primary_page_one_based=24, drawing="DCU0008A 4225266/A 09/2014",
        same_DCU_drawing_in_LVC2T45=True,
        pad_size_mm=[.85, .30], pad_pitch_mm=.5, row_centres_mm=3.1,
        rounded_corner_radius_mm=.05, nominal_NSM_mask_expansion_mm=.025,
        mask_process_tolerance_accepted=False, package_lead_fit_verified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/manufacturer-land.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
