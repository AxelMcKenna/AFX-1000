"""FF02 actual native fin surface/footprint extraction and conjugate-lid comparison."""

import json
import math
import re
from pathlib import Path

from hardware.cad.a12.thermal.fanless_feasibility.analyze import masks, read, sha
from hardware.cad.a12.thermal.fanless_feasibility.native_geometry import metadata

from .physics import lid_shell

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
FF01 = ROOT.parent / "fanless_feasibility"


def clip_polygon(poly, rect):
    x0, y0, x1, y1 = rect
    for axis, boundary, sign in [(0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)]:
        if not poly:
            break
        result = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            inside_a = sign * (a[axis] - boundary) >= 0
            inside_b = sign * (b[axis] - boundary) >= 0
            if inside_a:
                result.append(a)
            if inside_a != inside_b:
                t = (boundary - a[axis]) / (b[axis] - a[axis])
                p = [a[i] + t * (b[i] - a[i]) for i in range(2)]
                result.append(p)
        poly = result
    return (
        abs(math.fsum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2
        if poly
        else 0
    )


def line_fraction(a, b, rect):
    lo, hi = 0.0, 1.0
    for axis, lower, upper in [(0, rect[0], rect[2]), (1, rect[1], rect[3])]:
        delta = b[axis] - a[axis]
        if abs(delta) < 1e-12:
            if a[axis] < lower - 1e-9 or a[axis] > upper + 1e-9:
                return 0.0
        else:
            u, v = (lower - a[axis]) / delta, (upper - a[axis]) / delta
            lo = max(lo, min(u, v))
            hi = min(hi, max(u, v))
    return max(0, hi - lo)


def extract(grid):
    import numpy as np

    nx, ny = grid
    dx, dy = 334 / nx, 157 / ny
    pts = [
        [float(v) for v in row]
        for row in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", (OUT / "fins.stl").read_text())
    ]
    vertical = np.zeros((ny, nx))
    root = np.zeros((ny, nx))
    sum_vertical = 0
    sum_root = 0
    for off in range(0, len(pts), 3):
        tri = pts[off : off + 3]
        a, b, c = tri
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cross = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
        area = math.sqrt(sum(x * x for x in cross)) / 2
        xy = [p[:2] for p in tri]
        is_top = all(abs(p[2] - 56) < 1e-8 for p in tri)
        is_vertical = abs(cross[2]) < 1e-10
        if not is_top and not is_vertical:
            continue
        if is_top:
            sum_root += area
        else:
            sum_vertical += area
        x0, y0 = min(p[0] for p in tri), min(p[1] for p in tri)
        x1, y1 = max(p[0] for p in tri), max(p[1] for p in tri)
        ii = range(max(0, int(x0 / dx)), min(nx - 1, int(x1 / dx)) + 1)
        jj = range(max(0, int(y0 / dy)), min(ny - 1, int(y1 / dy)) + 1)
        pair = max(((p, q) for p in xy for q in xy), key=lambda pq: math.dist(*pq))
        for j in jj:
            for i in ii:
                rect = [i * dx, j * dy, (i + 1) * dx, (j + 1) * dy]
                if is_top:
                    root[j, i] += clip_polygon(xy, rect)
                else:
                    vertical[j, i] += area * line_fraction(*pair, rect)
    # Root area becomes unavailable for flat-lid convection/radiation; no fin radiation added.
    return (
        vertical * 1e-6,
        root / (dx * dy),
        dict(
            native_vertical_area_m2=sum_vertical * 1e-6,
            native_root_area_m2=sum_root * 1e-6,
            distributed_vertical_area_m2=float(vertical.sum() * 1e-6),
            distributed_root_area_m2=float(root.sum() * 1e-6),
            vertical_area_residual_m2=float((vertical.sum() - sum_vertical) * 1e-6),
            root_area_residual_m2=float((root.sum() - sum_root) * 1e-6),
        ),
    )


def main():
    import numpy as np

    base = read(FF01 / "generated/analysis.json")
    grid = (134, 64)
    fin_area, roots, area = extract(grid)
    panel, exposed = masks(grid)
    exposed = np.maximum(0, exposed.astype(float) - roots)
    # Reject real roots outside the inherited panel, apart from finite-grid edge occupancy.
    rows = []
    for target in [60, 65]:
        for wall_fraction, k, joint, face_fraction in [
            (1, 167, 0, 1),
            (0.7, 167, 0, 1),
            (0.7, 140, 0.05, 1),
            (0.7, 140, 0.10, 1),
            (0.7, 140, 0.2, 1),
            (0.7, 140, 0.2, 0.5),
        ]:
            r, field = lid_shell(
                target,
                panel,
                exposed,
                wall_fraction,
                0.8,
                k,
                joint,
                grid=grid,
                fin_areas=fin_area,
                fin_face_fraction=face_fraction,
            )
            bottom = next(
                v["bottom_actual_notched_mesh_assumed_capacity_w"]
                for v in base["metal_shell_proposals"]
                if v["base_prescribed_c"] == target
                and v["wall_exposed_fraction_assumed"] == 0.7
                and v["joint_r_assumed_k_per_w"] == 0
            )
            r.update(
                total_conditional_rejection_w=bottom + r["heat_accepted_from_base_w"],
                target_heat_w=base["heat_target_w"],
                conditional_margin_w=bottom + r["heat_accepted_from_base_w"] - base["heat_target_w"],
            )
            rows.append(r)
            if target == 65 and joint == 0.2 and face_fraction == 1:
                np.save(OUT / "lid-temperature.npy", field)
    geos = {
        name: metadata(OUT / file)
        for name, file in [("lid_with_fins", "lid-with-fins.stl"), ("fins", "fins.stl")]
    }
    inputs = [
        ROOT / "physics.py",
        ROOT / "analyze.py",
        OUT / "prototype.scad",
        OUT / "fins.stl",
        OUT / "lid-with-fins.stl",
        FF01 / "handoff.json",
        FF01 / "analyze.py",
        FF01 / "generated/analysis.json",
        FF01 / "sources/context/hardware/cad/a11/generated/layout.scad",
        FF01 / "sources/context/hardware/cad/a11/housing.scad",
    ]
    report = dict(
        revision="FF02-private-upward-perimeter-fin-addendum",
        envelope_overall_nominal_mm=87.6,
        fin_top_z=56,
        fin_height_mm=18,
        fin_thickness_mm=2,
        control_top_nominal_z=58.8,
        cap_xy_project_margin_mm=2,
        lid_fastener_xy_reserve_r_mm=4.2,
        areas=area,
        native=geos,
        cases=rows,
        source_sha256={str(p.relative_to(ROOT.parent)): sha(p) for p in inputs},
        no_extra_fin_radiation_credit=True,
        fin_neighbor_preheat_or_installed_h_bound=None,
        full_finger_service_access_qualified=False,
        controls_screws_lid_thermal_expansion_and_electrical_integration_qualified=False,
        physical_tests_performed=0,
        cooling_design_adopted=False,
        thermal_qualified=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "areas": area,
                "cases": [
                    {
                        k: r[k]
                        for k in [
                            "base_prescribed_c",
                            "wall_exposed_fraction_assumed",
                            "joint_r_assumed_k_per_w",
                            "extra_fin_face_fraction_assumed",
                            "extra_fin_correlated_convection_w",
                            "total_conditional_rejection_w",
                            "conditional_margin_w",
                        ]
                    }
                    for r in rows
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
