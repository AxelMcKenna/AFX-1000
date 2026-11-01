"""Exact envelope comparison and explicit integration contracts, no new MCAD pass."""

import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def geometry(w, d, h):
    w, d, h = map(lambda x: Fraction(str(x)), (w, d, h))
    return {
        "floor_mm2": w * d,
        "box_volume_mm3": w * d * h,
        "box_outer_area_mm2": 2 * (w * d + w * h + d * h),
    }


def run():
    cfg = json.loads((ROOT / "dimensions.json").read_text())
    base = geometry(*cfg["baseline_outer_shell"])
    rows = []
    for d, h in [(157, 38), (177, 50), (177, 54), (187, 50), (187, 54), (188.4, 45.6)]:
        g = geometry(334, d, h)
        row = {"outer_shell_mm": [334, d, h]}
        for k, v in g.items():
            ratio = v / base[k]
            row[k] = float(v)
            row[k + "_ratio_exact"] = str(ratio)
            row[k + "_ratio"] = float(ratio)
        # Ideal mathematical r7 rounded-prism envelope. No aperture, boss,
        # cutout, fin, controls, foot or actual exposed-surface area credit.
        r = 7
        area = float(g["floor_mm2"]) - (4 - math.pi) * r * r
        perimeter = 2 * (334 + d) - 8 * r + 2 * math.pi * r
        row["ideal_r7_rounded_floor_mm2"] = area
        row["ideal_r7_prism_volume_mm3"] = area * h
        row["ideal_r7_prism_outer_area_mm2"] = 2 * area + perimeter * h
        rows.append(row)
    root_receipt = ROOT / "sources/hardware/cad/a12/enclosure_growth/generated/verification.json"
    root_blank = json.loads(root_receipt.read_text())
    report = dict(
        scope=__doc__,
        dimensions_sha256=sha(ROOT / "dimensions.json"),
        code_sha256=sha(Path(__file__)),
        rows=rows,
        rectangular_geometry_excludes_controls_feet_fins_ports_and_cutouts=True,
        native_historical_overall_height_mm={"shell38": 87.6, "shell54": 103.6},
        shell45p6_overall_if_same_controls_and_feet_translate_arithmetic_mm=95.2,
        root_new_enclosure_blank_receipt_sha256=sha(root_receipt),
        root_new_blank_native_checks_clear=root_blank["native_enclosure_blank_checks_clear"],
        root_new_outer_reference_actual_height_mm=root_blank["cases"]["outer_reference"]["overall_height_mm"],
        root_outer_reference_height_does_not_verify_control_PCB_shaft_alignment=True,
        shell_only_growth_relief=[
            "More empty front strip and higher panel envelope, subject to actual internal mounting/control constraints.",
            "More geometric opportunity for a new cooling assembly, service lanes and separated supply/return branches.",
        ],
        requires_actual_relayout_or_new_contract=[
            "Move/rebuild DIG copper bus or implement verified installation/removal/access sequence for H9; fixed-axis collision stays unchanged.",
            "Relocate mount/modify E19 copper attachment to widen the actual0.779689mm gate; larger shell does not change PCB geometry.",
            "Implement physical positive/return fanout for the remaining0.636A; larger volume does not create terminals.",
            "Specify control-PCB support/shaft/key/linkage changes matching panel+7.6mm; old54mm audit measured only outer envelope.",
            "Create enlarged metal base, nine-fastener map, foot placement, land/support isolation and thermal seams; old plastic shell has no metal cooling credit.",
            "Keep rear I/O cassetteY0 or explicitly relocate/requalify panel cuts and inlet wire paths. Front relocation extends 12V/output leads and changes resistance/bend budgets.",
            "Rebuild lid perimeter, new front mounts and control keepouts; old149mm row remains a source reference.",
            "Requalify local thermal contact/pressure/PCB spreading, full PDN/startup/effectiveC and physical heat rejection.",
        ],
        thermal_surface_ratio_is_not_cooling_gain=True,
        dimension_adopted=False,
        thermal_qualified=False,
        physical_tests_performed=0,
        fabrication_released=False,
    )
    (ROOT / "generated/plan.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(rows[-1], indent=2))


if __name__ == "__main__":
    run()
