"""AP03 branch pressure/energy comparison; no installed cooling qualification."""

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / "sources" / name).read_text())


def density(ambient_c=40, pressure_pa=101325):
    return pressure_pa / (287.05 * (ambient_c + 273.15))


def drop(flow_m3h, area_mm2, cd, pressure_pa=101325):
    if flow_m3h < 0 or area_mm2 <= 0 or not 0 < cd <= 1:
        raise ValueError("Invalid orifice parameters")
    return density(pressure_pa=pressure_pa) / 2 * (flow_m3h / 3600 / (cd * area_mm2 * 1e-6)) ** 2


def pressure(curve, flow, rpm):
    if flow < 0 or not 0 < rpm <= 7000:
        raise ValueError("Invalid fan comparison")
    ratio = rpm / 7000
    q = flow / 2 / (0.028316846592 * 60) / ratio
    if q > curve[-1][0]:
        return None
    for (q0, p0), (q1, p1) in zip(curve, curve[1:]):
        if q0 <= q <= q1:
            return (p0 + (p1 - p0) * (q - q0) / (q1 - q0)) * 249.08891 * ratio**2 * (298.15 / 313.15)
    raise ValueError("No fan-curve segment")


def flow_for_heat(watts, ceiling, pressure_pa):
    if watts < 0 or ceiling <= 40:
        raise ValueError("Invalid energy comparison")
    return watts * 3600 / (density(pressure_pa=pressure_pa) * 1000 * (ceiling - 40))


def branches(curve, rpm, cd, inlet, exhaust, guard, meter):
    # Parallel branches meet at the fan plenum. The fan guard is common;
    # the interior ports and base meter are not mutually in series.
    fan = pressure(curve, 10, rpm)
    common = drop(5, guard, cd)
    interior = drop(8.8, inlet, cd) + drop(8.8, exhaust, cd)
    base = drop(1.2, meter, cd)
    # Zero unknown channel/pin/turn/outlet loss, not a physical upper/lower bound.
    r_int, r_base = interior / 8.8**2, base / 1.2**2
    ratio = math.sqrt(r_int / r_base)
    ideal_base = 10 * ratio / (1 + ratio)
    return dict(
        rpm_sensitivity=rpm, Cd_sensitivity=cd, meter_total_mm2=meter,
        fan_pressure_pa=fan, common_guard_loss_pa=common,
        interior_port_losses_pa=interior, base_meter_loss_pa=base,
        interior_unknown_loss_allowance_pa=fan - common - interior,
        base_unknown_loss_allowance_pa=fan - common - base,
        head_above_one_point_two_known_losses_pa=fan - 1.2 * (common + max(interior, base)),
        minimum_known_pressure_for_requested_split_pa=common + max(interior, base),
        ideal_zero_other_loss_split_at_total10=dict(interior_m3h=10 - ideal_base, base_m3h=ideal_base),
        requested_split_passes_known_loss_comparison=fan >= common + max(interior, base),
        unknown_losses_assumed_zero_only_for_ideal_split=True,
        installed_flow_verified=False,
    )


def operating_point(curve, rpm, inlet, exhaust, guard, meter, approach_each, interior_k, base_k):
    """Solve equal-pressure branches plus common guard against the fan curve.

    K values are deliberately hypothetical. Identical fan duties and equal
    division of base flow between both rear approach passages are assumed.
    """
    cd = .6
    ri = drop(1, inlet, cd) + drop(1, exhaust, cd) + interior_k * drop(1, inlet, 1)
    rb = drop(1, meter, cd) + base_k * drop(.5, approach_each, 1)
    parallel = 1 / (1 / math.sqrt(ri) + 1 / math.sqrt(rb))**2
    lo, hi = 0., 2 * curve[-1][0] * (0.028316846592 * 60) * rpm / 7000
    for _ in range(70):
        total = (lo + hi) / 2
        system = drop(total / 2, guard, cd) + parallel * total**2
        if pressure(curve, total, rpm) > system:
            lo = total
        else:
            hi = total
    total = (lo + hi) / 2
    branch_head = parallel * total**2
    interior = math.sqrt(branch_head / ri)
    base = math.sqrt(branch_head / rb)
    return dict(
        rpm_sensitivity=rpm, Cd_sensitivity=cd, interior_K_sensitivity=interior_k,
        base_approach_K_sensitivity=base_k, total_m3h=total,
        interior_m3h=interior, base_m3h=base,
        interior_pressure_coefficient=ri, base_pressure_coefficient=rb,
        branch_pressure_pa=branch_head, common_guard_pressure_pa=drop(total / 2, guard, cd),
        fan_pressure_pa=pressure(curve, total, rpm),
        actual_K_values_bounded=False, actual_fan_balance_verified=False,
        installed_flow_verified=False,
    )


def compute():
    manifest = read("manifest.json")
    for name, record in manifest.items():
        assert sha(ROOT / "sources" / name) == record["sha256"], name
    sf, nf, ap01, ap02, channel = (read(n) for n in [
        "sf01-analysis.json", "nf03c-analysis.json", "ap01-analysis.json",
        "ap02-analysis.json", "ap02-channel.json",
    ])
    curve = sf["parts"]["V1"]["curve_points_cfm_inH2O"]
    ap03 = read("ap03-channel.json")
    header = (ROOT / "sources/fh02-health.h").read_text()
    max_period = int(re.search(r"PH_PERIOD_MAX\s*=\s*(\d+)", header)[1])
    fh = read("fh02-analysis.json")
    assert math.isclose(fh["source_delta"]["NF03_capacity_heat_w"],
                        nf["power"]["new_enclosing_whole_inside_heat_requirement_w"])
    heat = fh["source_delta"]["proposed_capacity_heat_w"]
    inlet = channel["floor_port_net_faceted_mm2"]
    # Conservative downward rounding of reported native faceted areas;
    # these values must be refreshed for a later AP02 mechanical successor.
    exhaust, guard = 2557.14, 868.2
    energy = []
    for air_pressure in [101325, 80000]:
        for land_heat in [0, ap01["hypothetical_four_land_heat_w"]]:
            interior = flow_for_heat(1.2 * (heat - land_heat), 58, air_pressure)
            base = flow_for_heat(1.2 * land_heat, 60, air_pressure)
            energy.append(dict(
                pressure_pa=air_pressure, hypothetical_heat_to_base_w=land_heat,
                interior_necessary_m3h=interior, base_necessary_m3h=base,
                target_covers_necessary_energy_flow=interior <= 8.8 and base <= 1.2,
            ))
    fr = read("fr01-port-shadow.json")
    assert math.isclose(fr["authored_port_net_mm2"], inlet, abs_tol=1e-6)
    fr_projection = fr["port_area_outside_solid_receiver_projection_mm2"]
    assert 0 < fr_projection < inlet
    cases = []
    for rpm in [5300, 5712, 7000]:
        for cd in [0.6, 0.75, 0.9]:
            for meter in [125, 200, 250, 300, ap03["meter_actual_faceted_total_mm2"]]:
                for name, area in [
                    ("actual_floor_opening", inlet),
                    ("Trill_uncovered_projection_sensitivity", channel["nominal_vertical_projection_not_covered_by_Trill_mm2"]),
                    ("FR01_NF233_FPC84_Trill_projection_sensitivity", fr_projection),
                ]:
                    case = branches(curve, rpm, cd, area, exhaust, guard, meter)
                    case.update(inlet_area_sensitivity=name, inlet_area_mm2=area)
                    cases.append(case)
    coupled = []
    approach = ap03["bounds"]["extra_wall_plus02_component_XY_plus02_sensitivity"]["right_uniform_lower_bound_mm2"]
    energy_sea_level = [r for r in energy if r["pressure_pa"] == 101325]
    for rpm in [5300, 5712, 7000]:
        for ki in [0, 2, 4, 8, 16]:
            for kb in [0, 2, 4, 8, 16]:
                row = operating_point(curve, rpm, inlet, exhaust, guard,
                                      ap03["meter_actual_faceted_total_mm2"], approach, ki, kb)
                row["necessary_energy_comparisons"] = [{
                    "hypothetical_heat_to_base_w": e["hypothetical_heat_to_base_w"],
                    "covers_necessary_energy_transport": row["interior_m3h"] >= e["interior_necessary_m3h"] and row["base_m3h"] >= e["base_necessary_m3h"],
                } for e in energy_sea_level]
                coupled.append(row)
    return dict(
        revision="AP04-NF03C-FH02-and-AP03-conditional-operating-points",
        source_manifest_sha256=sha(ROOT / "sources/manifest.json"),
        heat_capacity_requirement_w=heat, heat_multiplier=1.2,
        fan_motor_or_controller_extra_heat_added_w=0,
        digital_loads_are_suballocations_of_existing_capacity=True,
        proposed_DIG_capacity_a=2.42,
        new_source_current_voltage_connector_guard_startup_PDN_qualified=False,
        target=dict(interior_m3h=8.8, base_m3h=1.2, total_m3h=10),
        nominal_ap02_meter_mm2=ap02["metering"]["nominal_total_aperture_mm2"],
        area_basis=dict(inlet_faceted_mm2=inlet, exhaust_rounded_down_mm2=exhaust, guard_each_rounded_down_mm2=guard,
                        FR01_uncovered_projection_sensitivity_mm2=fr_projection,
                        FR01_projection_is_governing_throat=False,
                        FR01_opaque_bundle_is_actual_wire=False,
                        NF265_and_new_E28_assembly_included=False),
        energy_comparisons=energy, pressure_comparisons=cases,
        coupled_operating_point_comparisons=coupled,
        AP03_meter_total_faceted_mm2=ap03["meter_actual_faceted_total_mm2"],
        AP03_approach_each_area_sensitivity_mm2=approach,
        conditional_rpm_floor=dict(
            measured_period_max_ticks=max_period, complete_clock_error_requirement_fraction=0.001,
            complete_period_measurement_error_requirement_ticks=20,
            derived_minimum_rpm=60 * 125000 * (1 - 0.001) / (2 * (max_period + 20)),
            chosen_pressure_model_floor_rpm=5300,
            timing_and_speed_to_pressure_model_verified=False,
        ),
        limitations=[
            "Catalogue fan curve and affinity-law RPM scaling are sensitivities, not guaranteed installed hot pressure envelopes.",
            "Cd values are comparisons; actual effective loss coefficients have not been measured.",
            "Trill uncovered projection is a turn-loss sensitivity, not a governing throat or guaranteed lower area.",
            "Unknown board, turns, pin field, under-base outlet, leakage, inlet blockage and seal losses remain unbounded.",
            "FR01's captured NF233/FPC84/Trill vertical projection is a separate fixed-flow area sensitivity; it is not a governing throat, a flow bound or adoption of the changing NF265/E28 assemblies.",
            "The original AP03 coupled-flow geometry excludes NF/FPC receiving bodies and actual complete wiring; local turning losses and installed blockage remain unbounded.",
            "Meter areas200/250/300 are geometry proposals only; no adoption or native fit is inferred here.",
            "Bulk energy flow does not prove local pot, MCU, converter, capacitor, TIM or surface temperatures.",
            "Altitude sensitivity is not a user-selected environmental requirement.",
        ],
        installed_flow_verified=False, thermal_qualified=False, fabrication_released=False,
    )


if __name__ == "__main__":
    result = compute()
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    for row in result["pressure_comparisons"]:
        if row["rpm_sensitivity"] == 5300 and row["Cd_sensitivity"] == 0.6 and row["inlet_area_sensitivity"] == "actual_floor_opening":
            print(row["meter_total_mm2"], "mm2: base unknown-loss allowance", round(row["base_unknown_loss_allowance_pa"], 4), "Pa")
