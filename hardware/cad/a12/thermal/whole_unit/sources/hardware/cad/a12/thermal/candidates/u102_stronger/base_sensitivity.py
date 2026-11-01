"""Explicit-source replay of captured T01 conditional plate equations, not a physical upper bound."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .base_geometry import circle_rect_area, lands, pin_centres

ROOT = Path(__file__).resolve().parent


def plate_scenario(d, heat_assignment, h, emissivity, ambient=40, radiation_view_factor=0.5, grid=(67, 32)):
    """2D finite-volume aluminum screen, nonlinear radiation, explicit assumed h.

    All declared loss provision is deliberately assigned to the plate: no invented internal-air
    cooling credit. It assumes perfect board-to-base transfer for unlanded heat,
    and therefore is not a junction prediction. Every edge is adiabatic; only
    outside lower projected area radiates. Pin side area participates in
    convection; no catalog orientation or radiation view-factor proof is used.
    """
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve

    nx, ny = grid
    dx, dy = 0.334 / nx, 0.157 / ny
    area = dx * dy
    k = 167.0  # manufacturer typical, not a certified minimum
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
    native_heat = heat_assignment
    for ref, (x, y, watts) in native_heat.items():
        site = next((s for s in lands(d) if ref in s["refs"]), None)
        if site is not None:
            px, py, w, hh = site["metal_global"]
        else:
            # Declared idealized3x3mm source only; no actual unlanded thermal path is asserted.
            px, py, w, hh = 168 + x - 1.5, 108 + y - 1.5, 3, 3
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
    reserve = d["design_allocations"]["total_heat_w"] - math.fsum(x[2] for x in heat_assignment.values())
    assert reserve >= -1e-9
    reserve = max(0, reserve)
    # Unallocated feedback/supervisor reserve goes to the hottest cluster.
    q += reserve * rect_weights(0.273, 0.112, 0.008, 0.008)
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
    sigma = 5.670374419e-8
    temp = np.full(n, ambient + 20)
    for iteration in range(100):
        kelvin = temp + 273.15
        ambk = ambient + 273.15
        grad = h * conv + 4 * emissivity * radiation_view_factor * sigma * rad * kelvin**3
        f = h * conv * (temp - ambient) + emissivity * radiation_view_factor * sigma * rad * (
            kelvin**4 - ambk**4
        )
        matrix = conduction.tocsr()
        matrix.setdiag(matrix.diagonal() + grad)
        new = spsolve(matrix, q - f + grad * temp)
        if float(np.max(np.abs(new - temp))) < 1e-8:
            temp = new
            break
        temp = new
    reject = not bool(np.all(np.isfinite(temp))) or iteration == 99
    actual_w = float(
        np.sum(
            h * conv * (temp - ambient)
            + emissivity
            * radiation_view_factor
            * sigma
            * rad
            * ((temp + 273.15) ** 4 - (ambient + 273.15) ** 4)
        )
    )
    assert not reject and abs(actual_w - d["design_allocations"]["total_heat_w"]) < 1e-6
    maximum = float(np.max(temp))
    local = {}
    for ref, (px, py, _) in heat_assignment.items():
        weights = rect_weights((168 + px - 1.5) / 1000, (108 + py - 1.5) / 1000, 0.003, 0.003)
        local[ref] = dict(
            area_weighted_base_reference_c=float(weights @ temp),
            local_peak_in_3x3mm_projection_c=float(np.max(temp[weights > 0])),
        )
    return dict(
        local_3x3mm_source_projections=local,
        h_assumed_w_per_m2k=h,
        emissivity_assumed=emissivity,
        radiation_projected_view_factor_assumed=radiation_view_factor,
        nonlinear_iterations=iteration + 1,
        converged=True,
        aluminum_k_typical_w_per_mk=k,
        grid=[nx, ny],
        pin_fin_efficiency_conditional=eta,
        outside_convection_effective_area_m2=float(conv.sum()),
        lower_projected_radiation_area_m2=float(rad.sum()),
        heat_source_area_scope="Four landed heat sources uniformly over exact metal lands; others idealized3x3mm sources with perfect transfer to plate. Neither models PCB thermal paths.",
        total_w=actual_w,
        plate_max_c=maximum,
        plate_mean_c=float(np.mean(temp)),
        conditional_peak_base_rtheta_c_per_w=(maximum - ambient) / actual_w,
        conditional_60c_coldplate_allocation_satisfied=maximum <= 60,
        ambient_assumed_c=ambient,
        convection_or_assembly_qualified=False,
    )


def main():
    source = ROOT / "sources/base-model"
    d = json.loads((source / "design.json").read_text())
    historical = json.loads((source / "generated/analysis.json").read_text())
    heat = historical["actual_native_heat_assignment"]
    paths = [
        Path(__file__).resolve(),
        ROOT / "base_geometry.py",
        *[p for p in source.rglob("*") if p.is_file()],
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    cases = []
    for h, e in [(1, 0.8), (2, 0.8), (3, 0.8), (5, 0.8), (3, 0.05)]:
        cases.append(plate_scenario(d, heat, h, e))
    reproduction = []
    for original, actual in zip(historical["conditional_plate_scenarios"], cases):
        difference = actual["plate_max_c"] - original["plate_max_c"]
        assert abs(difference) < 1e-7, "Copied source equations no longer reproduce captured report"
        reproduction.append(
            dict(
                h=actual["h_assumed_w_per_m2k"],
                emissivity=actual["emissivity_assumed"],
                plate_max_change_c=difference,
            )
        )
    thresholds = []
    for target in [60, 65]:
        for e in [0.8, 0.05]:
            low, high = 0.1, 10.0
            for _ in range(14):
                h = (low + high) / 2
                result = plate_scenario(d, heat, h, e)
                if result["plate_max_c"] > target:
                    low = h
                else:
                    high = h
            thresholds.append(
                dict(
                    target_base_c=target,
                    emissivity_assumed=e,
                    minimum_uniform_h_in_this_model_bracket_w_per_m2k=[low, high],
                    installed_h_is_bounded=False,
                    convection_qualified=False,
                )
            )
    heat_w = sum(row[2] for row in heat.values())
    report = dict(
        revision="T01-whole-base-assumption-audit",
        source_sha256=hashes,
        scope="Exact replay of historical supply-loss-only plate model; not a whole standalone unit temperature prediction",
        copied_equation_changes=[
            "Native heat values supplied explicitly from captured report instead of live canonical reader",
            "Added read-only local3x3mm source projection outputs; thermal equations unchanged",
        ],
        reproduced_historical_cases=reproduction,
        cases=cases,
        conditional_h_thresholds=thresholds,
        supply_loss_provision_w=heat_w,
        project_ambient_allocation_c=[0, 40],
        ambient_measured=False,
        required_base_to_ambient_at_60c_if_all_other_inputs_bounded_k_per_w=20 / heat_w,
        required_base_to_ambient_at_65c_if_all_other_inputs_bounded_k_per_w=25 / heat_w,
        downstream_scope=dict(
            digital_protected_current_allocation_a=2.4,
            nominal_digital_delivered_w=12.0,
            analog_protected_current_allocation_a=0.251,
            nominal_analog_delivered_w=1.255,
            delivered_power_is_measured_internal_heat=False,
            includes_bipolar_loads_in_these_numbers=False,
            fraction_into_metal_base=None,
            whole_unit_heat_upper_w=None,
        ),
        actual_base_upper_c=None,
        physical_tests_performed=0,
        whole_base_qualified=False,
        unbounded_inputs=[
            "Supply losses10.557757W are analysis allocations, not source-bound measured upper powers across all simultaneous loads/temperature/startup/fault states",
            "Delivered5V/bipolar power dissipated in processor/LED/control/audio boards is absent from supply-loss ledger; emitted optical/signal power and fraction leaving through shell/air/base are unknown",
            "Uniform h is assumed over base/pins; actual horizontal orientation, fin-channel airflow, desk clearance, loaded feet, dust and neighbouring surfaces are not characterized",
            "Radiation uses assumed emissivity and0.5 view factor to a body at ambient; actual coating/ageing/desk temperature and enclosure surroundings are not bounded",
            "Typical aluminum k167 has no received material/temperature minimum; holes/countersinks/contact changes and3D effects are not fully enclosed",
            "Unlanded device heat is placed directly onto ideal3x3mm plate source; no package/PCB/interface path or internal-air temperature is solved",
            "Only supply's own heat provision is assigned; all heat toplate is conservative only within that incomplete source set",
            "Numerical convergence/mesh agreement does not calibrate h or prove ambient/material/source boundary conditions",
        ],
        required_measurements=[
            "Complete enclosure input/output power and delivered/emitted power ledger at worst real simultaneous modes and full ambient range",
            "Actual local base temperatures under every hot-device contact, ambient air below fins and representative radiative surroundings with positive expanded uncertainty",
            "Assembled finite-clearance airflow/orientation/loaded-foot/finish sensitivity and steady-state/transient thermal soak",
            "Whole-path junction-to-local-base measurements and independent received TIM, copper-wall and package/interface bounds",
        ],
    )
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    (ROOT / "generated").mkdir(exist_ok=True)
    (ROOT / "generated/base-model-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            [
                dict(
                    h=c["h_assumed_w_per_m2k"],
                    e=c["emissivity_assumed"],
                    peak=c["plate_max_c"],
                    u102=c["local_3x3mm_source_projections"]["U102"],
                )
                for c in cases
            ],
            indent=2,
        )
    )
    print(json.dumps(thresholds, indent=2))


if __name__ == "__main__":
    main()
