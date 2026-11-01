"""WU01 explicit distributed-heat version of captured T01 plate equations; no physical upper bound."""

import math
from pathlib import Path

from .base_geometry import circle_rect_area, pin_centres

ROOT = Path(__file__).resolve().parent


def base_fields(d, heat_assignment, h, grid=(67, 38)):
    """2D finite-volume aluminum screen, nonlinear radiation, explicit assumed h.

    All declared loss provision is deliberately assigned to the plate: no invented internal-air
    cooling credit. It assumes perfect board-to-base transfer for unlanded heat,
    and therefore is not a junction prediction. Every edge is adiabatic; only
    outside lower projected area radiates. Pin side area participates in
    convection; no catalog orientation or radiation view-factor proof is used.
    """
    import numpy as np
    from scipy.sparse import lil_matrix

    nx, ny = grid
    dx, dy = d["housing"][0] / 1000 / nx, d["housing"][1] / 1000 / ny
    area = dx * dy
    k = d.get("scenario_aluminum_k", 167.0)  # Scenario, not a certified minimum
    thick = d["base"]["plate_thickness"] / 1000
    pocket_web = min(thick, (1.6 - (d["base"]["plate_top_z"] - d["base"]["plate_thickness"])) / 1000)
    n = nx * ny
    conv = np.full(n, area)
    rad = np.full(n, area)

    def rect_weights(x, y, w, hh):
        xx = np.maximum(0, np.minimum((np.arange(nx) + 1) * dx, x + w) - np.maximum(np.arange(nx) * dx, x))
        yy = np.maximum(0, np.minimum((np.arange(ny) + 1) * dy, y + hh) - np.maximum(np.arange(ny) * dy, y))
        result = np.outer(yy, xx).reshape(n)
        assert result.sum() > 0
        return result / result.sum()

    m = math.sqrt(h * 0.012 / (k * 0.003 * 0.003))
    fin_mL = m * (d["base"]["fin_height"] / 1000 + 0.003 / 4)
    eta = math.tanh(fin_mL) / fin_mL
    for x, y in pin_centres(d):
        weights = rect_weights(x / 1000 - 0.0015, y / 1000 - 0.0015, 0.003, 0.003)
        # Axial square-pin fin efficiency under declared constant h.
        conv += weights * eta * 4 * 0.003 * d["base"]["fin_height"] / 1000
    covered = np.zeros((ny, nx))
    for x, y in d["feet"]["centres"]:
        for a in range(8):
            for b in range(8):
                xx = (np.arange(nx) + (a + 0.5) / 8) * dx - x / 1000
                yy = (np.arange(ny) + (b + 0.5) / 8) * dy - y / 1000
                covered += (xx[None, :] ** 2 + yy[:, None] ** 2 <= 0.009**2) / 64
    # Foot disks suppress outside plate area; no foot conduction/cooling credit.
    covered = np.minimum(1, covered).reshape(n)
    conv -= covered * area
    rad -= covered * area
    q = np.zeros(n)
    for source in heat_assignment:
        watts = source["watts"]
        px, py, w, hh = source["rect_housing_mm"]
        site = source.get("notched_land")
        weights = rect_weights(px / 1000, py / 1000, w / 1000, hh / 1000)
        if site is not None and "corner_relief" in site:
            weights = weights.reshape(ny, nx) * (w * hh)
            for j in range(ny):
                for i in range(nx):
                    if weights[j, i] <= 0:
                        continue
                    xa, ya = max(px, i * dx * 1000), max(py, j * dy * 1000)
                    xb, yb = min(px + w, (i + 1) * dx * 1000), min(py + hh, (j + 1) * dy * 1000)
                    weights[j, i] -= circle_rect_area(
                        [xa, ya, xb - xa, yb - ya],
                        site["relief_centre_global"],
                        site["corner_relief"]["metal_radius_mm"],
                    )
            weights = weights.reshape(n) / site["metal_contact_area_mm2"]
            assert abs(weights.sum() - 1) < 1e-8 and weights.min() > -1e-10
        q += watts * weights
    source_total = math.fsum(source["watts"] for source in heat_assignment)
    assert abs(q.sum() - source_total) < 1e-8
    conduction = lil_matrix((n, n))
    for j in range(ny):
        for i in range(nx):
            p = j * nx + i
            local_t = (
                pocket_web if 0.2065 < (i + 0.5) * dx < 0.2875 and 0.0405 < (j + 0.5) * dy < 0.0735 else thick
            )
            for di, dj in ((1, 0), (0, 1)):
                ii, jj = i + di, j + dj
                if ii >= nx or jj >= ny:
                    continue
                pp = jj * nx + ii
                other_t = (
                    pocket_web
                    if 0.2065 < (ii + 0.5) * dx < 0.2875 and 0.0405 < (jj + 0.5) * dy < 0.0735
                    else thick
                )
                t_eff = 2 / (1 / local_t + 1 / other_t)
                g = k * t_eff * (dy / dx if di else dx / dy)
                conduction[p, p] += g
                conduction[pp, pp] += g
                conduction[p, pp] -= g
                conduction[pp, p] -= g
    return dict(
        conduction=conduction.tocsr(),
        q=q,
        conv=conv,
        rad=rad,
        eta=eta,
        dx=dx,
        dy=dy,
        thickness=thick,
        k=k,
        source_total_w=source_total,
        rect_weights=rect_weights,
    )
