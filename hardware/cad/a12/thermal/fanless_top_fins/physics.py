"""FF01 finite-volume conduction plus explicitly scoped natural-convection correlations."""

import math

SIGMA = 5.670374419e-8
G = 9.80665


def air(surface_c, ambient_c=40):
    """Film-temperature ideal dry air; NIST conductivity interpolation, NASA viscosity.

    cp/R and linear interpolation are declared engineering approximations, not a property bound.
    """
    t = (surface_c + ambient_c) / 2 + 273.15
    if not 300 <= t <= 400:
        raise ValueError("Air interpolation outside captured 300..400K table interval")
    rho = 101325 / (287.05 * t)
    mu = 1.458e-6 * t**1.5 / (t + 110.4)
    k = (26.4 + (t - 300) * (33.5 - 26.4) / 100) / 1000
    cp = 1007.0
    return dict(film_k=t, rho=rho, mu=mu, nu=mu / rho, alpha=k / (rho * cp), k=k, cp=cp, pr=mu * cp / k)


def rayleigh(length, surface_c, ambient_c=40):
    a = air(surface_c, ambient_c)
    return G / a["film_k"] * (surface_c - ambient_c) * length**3 / (a["nu"] * a["alpha"])


def downward_h(spacing, surface_c, ambient_c=40):
    """Tari/Mehrtash2013 Eq4/11, horizontal-downward; no table correction invented."""
    if spacing <= 0 or surface_c <= ambient_c:
        raise ValueError("Positive spacing and temperature difference required")
    a = air(surface_c, ambient_c)
    ra = rayleigh(spacing, surface_c, ambient_c)
    if ra >= 1.8e4:
        raise ValueError("Downward correlation Rayleigh limit exceeded")
    nu = 0.0149 * math.sqrt(ra)
    return dict(Ra_s=ra, Nu_s=nu, h=nu * a["k"] / spacing)


def vertical_h(height, surface_c, ambient_c=40):
    """Churchill/Chu1975 Eq5: laminar vertical plate, NOT its squared all-Ra form."""
    a = air(surface_c, ambient_c)
    ra = rayleigh(height, surface_c, ambient_c)
    if not 0 < ra < 1e9:
        raise ValueError("Vertical laminar correlation limit exceeded")
    nu = 0.68 + 0.670 * ra**0.25 / (1 + (0.492 / a["pr"]) ** (9 / 16)) ** (4 / 9)
    return dict(Ra_h=ra, Nu_h=nu, h=nu * a["k"] / height)


def upward_h(area, perimeter, surface_c, ambient_c=40):
    """Lloyd/Moran1974 laminar A/P correlation; mass/heat analogy and masking are conditional."""
    a = air(surface_c, ambient_c)
    length = area / perimeter
    ra = rayleigh(length, surface_c, ambient_c)
    if not 2.2e4 <= ra <= 8e6:
        raise ValueError("Upward laminar source interval exceeded")
    return dict(Ra_l=ra, L_star=length, h=0.54 * ra**0.25 * a["k"] / length)


def radiation(area, surface_c, ambient_c=40, emissivity=1, view=1):
    if not 0 <= emissivity <= 1 or not 0 <= view <= 1 or area < 0:
        raise ValueError("Invalid radiation geometry/emissivity")
    return SIGMA * area * emissivity * view * ((surface_c + 273.15) ** 4 - (ambient_c + 273.15) ** 4)


def plate_fins(n, thickness_mm, height_mm, surface_c, length_mm=334, width_mm=157, k_al=167):
    """Optimistic full-span array before mounting exclusions; finite fin efficiency."""
    l, w, t, height = (v / 1000 for v in [length_mm, width_mm, thickness_mm, height_mm])
    gap = (w - n * t) / (n - 1)
    corr = downward_h(gap, surface_c)
    h = corr["h"]
    ml = math.sqrt(2 * h / (k_al * t)) * (height + t / 2)
    eta = math.tanh(ml) / ml
    # Tips replace their projected root area; end faces also included.
    side = 2 * n * height * (l + t)
    wetted = l * w + side
    effective = l * w + side * eta
    aperture = l * w + 2 * (l + w) * height
    return dict(
        count=n,
        thickness_mm=thickness_mm,
        height_mm=height_mm,
        gap_mm=gap * 1000,
        length_mm=length_mm,
        width_mm=width_mm,
        correlation=corr,
        fin_efficiency=eta,
        total_wetted_area_m2=wetted,
        effective_area_m2=effective,
        external_radiation_envelope_m2=aperture,
        convection_w=h * effective * (surface_c - 40),
        radiation_black_envelope_upper_w=radiation(aperture, surface_c),
        geometry_within_original_paper_range=(
            8.8 <= gap * 1000 <= 14.7
            and 5 <= height_mm <= 25
            and thickness_mm == 3
            and 250 <= length_mm <= 340
        ),
        width157_vs_source180mm_extrapolation=True,
        table_or_foot_clearance_in_source=False,
        installed_bound=False,
    )


def stack_required_openings(heat_w, rise_mm, air_rise_c, cd):
    """Optimistic buoyancy/Bernoulli/energy bound; two equal ports, no internal loss.

    Treats whole stack as hot as outlet; real mean stack density contrast is lower.
    """
    if not 0 < cd <= 1 or rise_mm <= 0:
        raise ValueError("Stack rise and positive discharge coefficient required")
    a = air(40 + air_rise_c)
    velocity = math.sqrt(2 * G * (rise_mm / 1000) * air_rise_c / (40 + 273.15))
    equivalent = heat_w / (a["rho"] * a["cp"] * velocity * air_rise_c)
    each = math.sqrt(2) * equivalent / cd
    return dict(
        heat_w=heat_w,
        stack_height_mm=rise_mm,
        outlet_rise_c=air_rise_c,
        cd_assumed=cd,
        velocity_head_ideal_m_s=velocity,
        effective_series_opening_cm2=equivalent * 1e4,
        each_of_two_openings_cm2=each * 1e4,
        density_profile_optimistic=True,
        internal_pressure_drop_zero_assumed=True,
        actual_airflow_bound_established=False,
    )


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
    labels, count = label(panel_mask)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    connected = labels == sizes.argmax()
    disconnected_area = float(np.count_nonzero(panel_mask & ~connected) * 0.334 * 0.157 / (nx * ny))
    panel_mask = connected
    dx, dy = 0.334 / nx, 0.157 / ny
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
    height, perimeter, wall_t = 0.036, 2 * (0.334 + 0.157), 0.0028
    dz = height / nz
    gw = k * wall_t * perimeter / dz
    # Bottom half cell distance plus optional whole-assembly contact resistance.
    gbase = 1 / (0.5 / gw + wall_joint_r)
    temp = np.full(n, base_c - 3)
    top_corr = upward_h(0.334 * 0.157, perimeter, base_c)
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
        top_corr = upward_h(0.334 * 0.157, perimeter, top_mean)
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
        wall_height_mm=36,
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
