"""Manufacturer-reference geometry plus explicit20%-stressed receiving tolerance.

Preserves old courtyard+.5 trial. No catalogue nominal is promoted to a maximum.
"""

import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .capture import ROOT, sha


def build():
    folder = ROOT / "xh_reference_variant"
    if folder.exists():
        raise RuntimeError("New XH receiving variant required")
    d = json.loads((ROOT / "generated/model233.json").read_text())
    pcb = ROOT / "inputs/FPC84/fan_power_health.kicad_pcb"
    fps = children(read_sexpr(pcb.read_text()), "footprint")
    bounds = {}
    for fp in fps:
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        value = next(p[2] for p in children(fp, "property") if p[1] == "Value")
        if not value.startswith("JST "):
            continue
        nominal = courtyard(fp, "F.Fab")
        ctyd = courtyard(fp, "F.CrtYd")
        assert all(
            abs(a - b) < 1e-6
            for a, b in zip(ctyd, [nominal[0] - 0.5, nominal[1] - 0.5, nominal[2] + 0.5, nominal[3] + 0.5])
        )
        expected = sorted([5.75, 9.9 if "B3B-" in value else 7.4])
        assert all(
            abs(a - b) < 1e-6
            for a, b in zip(sorted([nominal[2] - nominal[0], nominal[3] - nominal[1]]), expected)
        )
        bounds["FPC84_" + ref] = dict(
            nominal_native_FFab_mm=nominal,
            native_CrtYd_mm=ctyd,
            normal_requirement_mm=[2.0, 10.5],
            lateral_PROJECT_receiving_mm=0.3,
            manufacturer_max_or_tolerance_approved=False,
        )
    mates = []
    containment = []
    for old in d["mates"]:
        row = list(old)
        if row[0] in bounds:
            # Old bound=CrtYd+.5; new bound=FFab+.3=CrtYd-.2.
            row[1] += 0.7
            row[3] += 0.7
            row[4] -= 1.4
            row[6] -= 1.4
            assert all(
                old[i + 1] <= row[i + 1] and row[i + 1] + row[i + 4] <= old[i + 1] + old[i + 4] + 1e-9
                for i in range(3)
            )
            containment.append(dict(id=row[0], old_box_mm=old, new_box_mm=row, subset_verified=True))
        mates.append(row)
    folder.mkdir()
    scad = (ROOT / "matcher_fixed/components.scad").read_text()
    oldline = "fr_mates=" + json.dumps(d["mates"]) + ";"
    assert oldline in scad
    scad = scad.replace(oldline, "fr_mates=" + json.dumps(mates) + ";")
    (folder / "components.scad").write_text(scad)
    checks = (ROOT / "matcher_fixed/checks.scad").read_text()
    (folder / "checks.scad").write_text(checks)
    pdf = Path("/private/tmp/afx-jst-XH-US.pdf")
    assert pdf.is_file()
    contract = dict(
        exact_JST_parts=list(bounds),
        source_primary="https://www.jst.com/wp-content/uploads/2025/06/eXH.pdf",
        reviewed_pages=[2, 4, 5],
        reference_assembly_height_mm=9.8,
        reference_header_height_mm=7.0,
        reference_XHP_height_mm=7.5,
        reference_XHP_width_mm={"XHP-2": 7.3, "XHP-3": 9.8},
        reference_XHP_depth_mm=5.7,
        all_reference_dimensions_NOT_guaranteed_maxima=True,
        body_receiving_projection_max_mm=10.5,
        lateral_receiving_base_mm=0.25,
        lateral_receiving_stress_mm=0.30,
        reference_housing_bottom2p3_minus_receiving0p3_mm=2.0,
        external_and_neighbor_clearances_unchanged=True,
        old_exterior_passes_are_for_a_verified_superset_NOT_same_geometry=True,
        receivers=bounds,
        subset_contracts=containment,
        source_sha256={
            str(p): sha(p)
            for p in [
                Path(__file__),
                pcb,
                ROOT / "generated/model233.json",
                ROOT / "matcher_fixed/components.scad",
                pdf,
            ]
        },
        physical_qualified=False,
        manufacturer_body_tolerances_approved=False,
    )
    (folder / "contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                exact_selected_XH_receivers=len(bounds),
                all_new_receivers_subset_old=True,
                PCB_or_part_poses_changed=False,
            )
        )
    )


if __name__ == "__main__":
    build()
