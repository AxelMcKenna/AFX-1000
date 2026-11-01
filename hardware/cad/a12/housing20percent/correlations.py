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
