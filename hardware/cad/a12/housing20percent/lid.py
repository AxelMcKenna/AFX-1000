"""FF02 conjugate-lid equations parameterized to explicit candidate dimensions."""

import math

from .correlations import SIGMA, upward_h, vertical_h


def lid_shell(
    base_c,
    panel_mask,
    exposed_mask,
    wall_fraction=1,
    epsilon=0.8,
    k=167,
    wall_joint_r=0,
    grid=(67, 32),
    fin_areas=None,
    fin_face_fraction=1,
    width_mm=334,
    depth_mm=157,
    wall_height_mm=36,
):
    """Conjugate 2mm lid + six-node2.8mm sidewall ladder, prescribed isothermal base.

    Actual captured panel apertures remove cells. Caps block top heat transfer but retain metal
    beneath. Full perimeter sidewall conduction neglects port cuts: optimistic separate proposal.
    No canonical housing or upper/lower thermal path is changed or accepted.
    """
    import numpy as np
    from scipy.ndimage import label
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve

    nx, ny = grid
    width, depth = width_mm / 1000, depth_mm / 1000
    labels, count = label(panel_mask)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    connected = labels == sizes.argmax()
    disconnected_area = float(np.count_nonzero(panel_mask & ~connected) * width * depth / (nx * ny))
    panel_mask = connected
    dx, dy = width / nx, depth / ny
    area = dx * dy
    coords = [(j, i) for j in range(ny) for i in range(nx) if panel_mask[j, i]]
    lookup = {xy: n for n, xy in enumerate(coords)}
    row_bounds = {
        j: (min(i for jj, i in coords if jj == j), max(i for jj, i in coords if jj == j))
        for j in range(ny)
        if any(jj == j for jj, i in coords)
    }
    col_bounds = {
        i: (min(j for j, ii in coords if ii == i), max(j for j, ii in coords if ii == i))
        for i in range(nx)
        if any(ii == i for j, ii in coords)
    }
    nl = len(coords)
    nz = 6
    n = nl + nz
    height, perimeter, wall_t = wall_height_mm / 1000, 2 * (width + depth), 0.0028
    dz = height / nz
    gw = k * wall_t * perimeter / dz
    # Bottom half cell distance plus optional whole-assembly contact resistance.
    gbase = 1 / (0.5 / gw + wall_joint_r)
    temp = np.full(n, base_c - 3)
    top_corr = upward_h(width * depth, perimeter, base_c)
    wall_corr = vertical_h(height, base_c)
    top_area = np.array([area * exposed_mask[xy] for xy in coords])
    side_area = np.full(nz, perimeter * dz * wall_fraction)
    areas = np.r_[top_area, side_area]
    fin_area = np.zeros(n)
    if fin_areas is not None:
        fin_area[:nl] = [fin_areas[xy] for xy in coords]
    hs = np.r_[np.full(nl, top_corr["h"]), np.full(nz, wall_corr["h"])]
    cond = lil_matrix((n, n))
    rhs = np.zeros(n)

    def connect(a, b, g):
        cond[a, a] += g
        cond[b, b] += g
        cond[a, b] -= g
        cond[b, a] -= g

    for (j, i), p in lookup.items():
        for di, dj in [(1, 0), (0, 1)]:
            other = (j + dj, i + di)
            if other in lookup:
                connect(p, lookup[other], k * 0.002 * (dy / dx if di else dx / dy))
        for boundary, edge in [
            (i == row_bounds[j][0], dy),
            (i == row_bounds[j][1], dy),
            (j == col_bounds[i][0], dx),
            (j == col_bounds[i][1], dx),
        ]:
            if boundary:
                # Wall half segment in series with lid half-cell conduction.
                g = 1 / ((dz / 2) / (k * wall_t * edge) + (dx if edge == dy else dy) / (2 * k * 0.002 * edge))
                connect(p, nl + nz - 1, g)
    for z in range(nz - 1):
        connect(nl + z, nl + z + 1, gw)
    cond[nl, nl] += gbase
    rhs[nl] += base_c * gbase
    matrix_base = cond.tocsr()
    for iteration in range(100):
        # Update each group coefficient at its evolving surface mean, not at the hotter base.
        top_mean = float(top_area @ temp[:nl] / top_area.sum())
        side_mean = float(temp[nl:].mean())
        top_corr = upward_h(width * depth, perimeter, top_mean)
        wall_corr = vertical_h(height, side_mean)
        hs = np.r_[np.full(nl, top_corr["h"]), np.full(nz, wall_corr["h"])]
        fin_root_mean = float(fin_area @ temp / fin_area.sum()) if fin_area.sum() else top_mean
        fin_corr = vertical_h(0.018, fin_root_mean)
        fin_ml = math.sqrt(2 * fin_corr["h"] / (k * 0.002)) * (0.018 + 0.001)
        fin_eta = math.tanh(fin_ml) / fin_ml
        fin_g = fin_face_fraction * fin_area * fin_corr["h"] * fin_eta
        kelvin = temp + 273.15
        loss = (hs * areas + fin_g) * (temp - 40) + epsilon * SIGMA * areas * (kelvin**4 - 313.15**4)
        gradient = hs * areas + fin_g + 4 * epsilon * SIGMA * areas * kelvin**3
        matrix = matrix_base.copy()
        matrix.setdiag(matrix.diagonal() + gradient)
        new = spsolve(matrix, rhs - loss + gradient * temp)
        if not np.all(np.isfinite(new)):
            raise ValueError("Rejected nonfinite/singular lid solve")
        delta = float(np.max(np.abs(new - temp)))
        temp = new
        if delta < 1e-8:
            break
    power = gbase * (base_c - temp[nl])
    conv = (hs * areas + fin_g) * (temp - 40)
    rad = epsilon * SIGMA * areas * ((temp + 273.15) ** 4 - 313.15**4)
    result = dict(
        base_prescribed_c=base_c,
        extra_fin_correlated_convection_w=float((fin_g * (temp - 40)).sum()),
        extra_fin_face_fraction_assumed=fin_face_fraction,
        extra_fin_vertical_area_credited_m2=float(fin_area.sum()),
        extra_fin_efficiency=fin_eta,
        extra_fin_correlation=fin_corr,
        extra_fin_radiation_credit_w=0,
        adjacent_surface_radiation_shadowing_and_plume_preheat_unresolved=True,
        wall_exposed_fraction_assumed=wall_fraction,
        emissivity_assumed=epsilon,
        k_al_typical_or_sensitivity=k,
        joint_r_assumed_k_per_w=wall_joint_r,
        grid=list(grid),
        disconnected_raster_island_count=int(count - 1),
        disconnected_raster_area_excluded_m2=disconnected_area,
        lid_thickness_mm=2,
        wall_height_mm=wall_height_mm,
        wall_thickness_mm=2.8,
        cap_masked_top_exposed_m2=float(top_area.sum()),
        panel_metal_area_m2=float(nl * area),
        heat_accepted_from_base_w=float(power),
        top_heat_w=float((conv[:nl] + rad[:nl]).sum()),
        side_heat_w=float((conv[nl:] + rad[nl:]).sum()),
        lid_min_c=float(temp[:nl].min()),
        lid_max_c=float(temp[:nl].max()),
        wall_bottom_c=float(temp[nl]),
        wall_top_c=float(temp[-1]),
        conduction_and_surface_energy_residual_w=float(power - (conv + rad).sum()),
        iterations=iteration + 1,
        final_delta_c=delta,
        converged=iteration < 99 and delta < 1e-8,
        top_correlation=top_corr,
        correlation_h_updated_at_group_surface_means=True,
        side_correlation=wall_corr,
        wall_ports_lateral_gradient_seam_electrical_insulation_not_resolved=True,
        installed_guarantee=False,
    )
    field = np.full((ny, nx), float("nan"))
    for xy, p in lookup.items():
        field[xy] = temp[p]
    return result, field
