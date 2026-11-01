"""Independent review of every nominal STEP piece and complete assembly."""

import json
import math
from itertools import combinations

from .generate import OUT, ROOT, sha


def permitted_thread_overlap(a, b):
    names = {a, b}
    if "BONDED-PEDESTAL" in names:
        other = next(n for n in names if n != "BONDED-PEDESTAL")
        if other in {f"{rail}-SADDLE-SCREW{i}" for rail in ("ANA", "DIG") for i in (0, 1)}:
            return (
                math.pi * (0.825**2 - 0.65**2) * 3,
                "Nominal M1.6 major/minor overlap in PEEK tapped3mm floor; no thread-strength qualification",
            )
    for rail in ("ANA", "DIG"):
        for end in (0, 1):
            prefix = f"{rail}-CAP{end}-"
            if names == {prefix + "CROSS-SCREW", prefix + "NUT"}:
                return math.pi * (
                    0.825**2 - 0.8**2
                ) * 1.3, "Nominal M1.6 nut-thread major/minor overlap; helical thread unmodeled"
    return 0, None


def main():
    import cadquery as cq

    geometry = json.loads((OUT / "geometry.json").read_text())
    parts = {
        name: cq.importers.importStep(str(OUT / (name + ".step"))).val()
        for name, row in geometry.items()
        if isinstance(row, dict) and "volume_mm3" in row and not name.endswith("-COVERED-ENVELOPE")
    }
    validity = {
        name: dict(valid=s.isValid(), solids=len(s.Solids()), volume_mm3=s.Volume())
        for name, s in parts.items()
    }
    intersections = []
    unexpected = []
    for (a, x), (b, y) in combinations(parts.items(), 2):
        aa, bb = x.BoundingBox(), y.BoundingBox()
        if any(
            getattr(aa, axis + "max") < getattr(bb, axis + "min")
            or getattr(bb, axis + "max") < getattr(aa, axis + "min")
            for axis in "xyz"
        ):
            continue
        volume = x.intersect(y).Volume()
        if volume <= 1e-7:
            continue
        upper, reason = permitted_thread_overlap(a, b)
        row = dict(
            parts=[a, b],
            volume_mm3=volume,
            permitted_nominal_thread_overlap=reason is not None and volume <= upper + 1e-6,
            thread_overlap_geometric_upper_mm3=upper,
            basis=reason,
        )
        intersections.append(row)
        if not row["permitted_nominal_thread_overlap"]:
            unexpected.append(row)
    assembly = cq.importers.importStep(str(OUT / "positive-links.step")).val()
    aggregate = sum(s.Volume() for s in parts.values())
    volume_error = abs(assembly.Volume() - aggregate)
    control = cq.Solid.makeBox(0.2, 0.2, 0.2, cq.Vector(210, 139, 13.3))
    control_volume = parts["ANA-CU"].intersect(control).Volume()
    shape_ok = all(r["valid"] and r["solids"] == 1 for r in validity.values())
    complete = len(assembly.Solids()) == len(parts) and volume_error < 1e-6 + aggregate * 1e-8
    clear = (
        shape_ok
        and complete
        and not unexpected
        and math.isclose(control_volume, 0.008, rel_tol=0.005, abs_tol=1e-6)
    )
    report = dict(
        part_count=len(parts),
        possible_pairs=len(parts) * (len(parts) - 1) // 2,
        part_validity=validity,
        nonzero_intersections=intersections,
        unexpected_intersections=unexpected,
        complete_assembly_solid_count=len(assembly.Solids()),
        assembly_volume_error_mm3=volume_error,
        complete_assembly_matches_all_individual_parts=complete,
        independent_interference_control_mm3=control_volume,
        nominal_review_clear=clear,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [ROOT / "review_geometry.py", OUT / "geometry.json", OUT / "positive-links.step"]
            + [OUT / (n + ".step") for n in parts]
        },
        assembly_sequence_and_driver_access_verified=False,
        physical_fit_verified=False,
        material_strength_thread_torque_bond_and_dielectric_qualified=False,
        fabrication_released=False,
    )
    (OUT / "complete-geometry-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "part_count",
                    "possible_pairs",
                    "unexpected_intersections",
                    "complete_assembly_solid_count",
                    "assembly_volume_error_mm3",
                    "independent_interference_control_mm3",
                    "nominal_review_clear",
                )
            },
            indent=2,
        )
    )
    return 0 if clear else 1


if __name__ == "__main__":
    raise SystemExit(main())
