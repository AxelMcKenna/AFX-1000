"""Conservation and pressure-budget study; no installed cooling qualification."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
THERMAL = ROOT.parent
LAND_IDS = {
    "DIG_converter_loss",
    "P12_LDO_drop",
    "N12_LDO_drop",
    "RAW_N17_ldo_ground_current_envelope_a",
    "U13_converter_loss",
}
# Transcribed from the visually inspected Noctua 5V specification, page 6.
PQ = [(0, 1.78), (1.9, 1.32), (4.3, 0.71), (6.5, 0.51), (8.2, 0)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def required_flow(heat_w, ambient_c, air_ceiling_c, pressure_pa=101325):
    if heat_w < 0 or air_ceiling_c <= ambient_c or pressure_pa <= 0:
        raise ValueError("Nonnegative heat and positive air-temperature rise/pressure required")
    density = pressure_pa / (287.05 * (ambient_c + 273.15))
    return heat_w * 3600 / (density * 1000 * (air_ceiling_c - ambient_c))


def fan_pressure(flow_m3h, ambient_c=40, curve_scale=0.9):
    """Two parallel fans; scaled catalogue interpolation is ONLY a sensitivity."""
    if flow_m3h < 0 or not 0 < curve_scale <= 1:
        raise ValueError("Invalid flow or sensitivity scale")
    q = flow_m3h / (2 * curve_scale)
    if q > PQ[-1][0]:
        return None
    for (q0, p0), (q1, p1) in zip(PQ, PQ[1:]):
        if q0 <= q <= q1:
            p = p0 + (p1 - p0) * (q - q0) / (q1 - q0)
            return p * curve_scale * 9.80665 * (298.15 / (ambient_c + 273.15))
    raise AssertionError("Curve interpolation failed")


def orifice_drop(flow_m3h, area_mm2, cd, ambient_c=40):
    if flow_m3h < 0 or area_mm2 <= 0 or not 0 < cd <= 1:
        raise ValueError("Invalid port conditions")
    rho = 101325 / (287.05 * (ambient_c + 273.15))
    return rho / 2 * (flow_m3h / 3600 / (cd * area_mm2 * 1e-6)) ** 2


def guard_holes():
    # OpenSCAD j%2 has the sign of j, unlike Python's modulo for negative j.
    points = []
    for j in range(-4, 5):
        for i in range(-4, 5):
            x = 5.2 * (i + math.fmod(j, 2) / 2)
            y = j * 5.2 * math.sqrt(3) / 2
            if x * x + y * y < 16.65**2:
                points.append([x, y])
    # The actual SCAD cuts are inscribed 48-gons, not ideal circles.
    single = 48 / 2 * 2.1**2 * math.sin(2 * math.pi / 48)
    return points, len(points) * single


def compute():
    ledger_path = THERMAL / "whole_unit/generated/ledger.json"
    ledger = read(ledger_path)
    fan = read(THERMAL / "forced_air_5v_supply/analysis.json")
    rows = ledger["leaf_heat_rows"]
    assert len(rows) == 89 and len({r["id"] for r in rows}) == 89
    total = math.fsum(r["watts"] for r in rows)
    assert math.isclose(total, ledger["total_internal_heat_screen_w"], abs_tol=1e-12)
    selected = [r for r in rows if r["id"] in LAND_IDS]
    assert len(selected) == len(LAND_IDS)
    land_heat = math.fsum(r["watts"] for r in selected)
    reserve = next(r for r in rows if r["id"] == "digital_reserve")
    fan_current = fan["twenty_percent_planning_provision_a"]
    motor_heat = fan_current * reserve["source_voltage_v"]
    assert fan_current < reserve["current_allocation_a"]
    # Allocation partitions an existing source-power row; it adds no second load.
    reserve_left = reserve["watts"] - motor_heat
    assert math.isclose(reserve_left + motor_heat, reserve["watts"], abs_tol=1e-12)
    holes, guard_area = guard_holes()
    scenarios = []
    for pressure in [101325, 80000]:
        for stress in [1, 1.2]:
            for base_heat in [0, land_heat]:
                for air_limit in [48, 50, 58, 60]:
                    # No motor-heat export credit. All heat not assigned to base
                    # must be carried through the interior air branch.
                    interior_w = stress * (total - base_heat)
                    base_w = stress * base_heat
                    interior_flow = required_flow(interior_w, 40, air_limit, pressure)
                    base_flow = required_flow(base_w, 40, 60, pressure)
                    assert math.isclose(interior_w + base_w, stress * total, abs_tol=1e-12)
                    scenarios.append(
                        dict(
                            pressure_pa=pressure,
                            heat_multiplier=stress,
                            assumed_heat_to_base_w=base_heat,
                            interior_air_ceiling_c=air_limit,
                            internal_air_heat_w=interior_w,
                            base_branch_heat_w=base_w,
                            internal_air_minimum_m3h=interior_flow,
                            base_branch_minimum_m3h=base_flow,
                            total_minimum_m3h=interior_flow + base_flow,
                            below_two_fan_nominal_free_air=interior_flow + base_flow <= 16.4,
                            below_scaled_free_air_sensitivity=interior_flow + base_flow <= 14.76,
                        )
                    )
    # This flow split covers the necessary energy flow for BOTH heat splits
    # at 1.2x heat, 40C/101325Pa and58C interior air. Pressure is still unproved.
    total_flow, interior_flow, base_flow = 9.2, 8.0, 1.2
    candidate = dict(
        total_m3h=total_flow,
        interior_m3h=interior_flow,
        base_m3h=base_flow,
        inlet_net_area_mm2=2200,
        exhaust_net_area_mm2=2200,
        revised_guard_net_area_each_mm2=800,
    )
    selected_scenarios = [
        r
        for r in scenarios
        if r["pressure_pa"] == 101325 and r["heat_multiplier"] == 1.2 and r["interior_air_ceiling_c"] == 58
    ]
    assert len(selected_scenarios) == 2
    assert all(
        r["internal_air_minimum_m3h"] <= interior_flow and r["base_branch_minimum_m3h"] <= base_flow
        for r in selected_scenarios
    )
    pressure_rows = []
    for scale in [1, 0.9]:
        for cd in [0.6, 0.75, 0.9]:
            available = fan_pressure(total_flow, curve_scale=scale)
            ports = 2 * orifice_drop(interior_flow, 2200, cd)
            for name, area in [("existing_perforated", guard_area), ("proposed_more_open", 800)]:
                guards = orifice_drop(total_flow / 2, area, cd)
                pressure_rows.append(
                    dict(
                        curve_scale_sensitivity=scale,
                        assumed_discharge_coefficient=cd,
                        guard=name,
                        guard_net_area_each_mm2=area,
                        fan_pressure_sensitivity_pa=available,
                        inlet_plus_exhaust_loss_sensitivity_pa=ports,
                        guard_loss_sensitivity_pa=guards,
                        remaining_for_channels_baffles_filters_and_other_losses_pa=available - ports - guards,
                    )
                )
    sources = [
        ledger_path,
        THERMAL / "whole_unit/handoff.json",
        THERMAL / "forced_air_5v_supply/analysis.json",
        THERMAL / "forced_air_5v_supply/source.json",
        THERMAL / "forced_air_5v_supply/handoff.json",
        THERMAL / "forced_air_prototype/build.py",
        THERMAL / "forced_air_prototype/handoff.json",
        Path(__file__),
    ]
    pdf = Path(read(THERMAL / "forced_air_5v_supply/source.json")["technical_pdf_external_path"])
    assert sha(pdf) == "989f5ccc244424262921a60d8cf2dbe62972d4913196d8bacf4d20834aacbc6c"
    return dict(
        revision="AP01-conservation-and-conditional-port-budget",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        primary_fan_pdf_sha256=sha(pdf),
        primary_PQ_page=6,
        catalogue_PQ_m3h_mmH2O=PQ,
        whole_unit_leaf_rows=len(rows),
        total_source_heat_screen_w=total,
        hypothetical_four_land_heat_w=land_heat,
        land_rows=[{k: r[k] for k in ["id", "watts", "source_part_ref", "basis"]} for r in selected],
        digital_reserve_partition=dict(
            original_w=reserve["watts"],
            fan_current_allocation_a=fan_current,
            fan_motor_power_allocation_w=motor_heat,
            unassigned_remaining_w=reserve_left,
            extra_heat_added_w=0,
            motor_heat_export_credit_w=0,
            note="All motor heat retained in interior load for conservative air-energy screen; fan-health logic must share remaining reserve or revise source inventory.",
        ),
        gas_assumptions=dict(
            specific_heat_j_kg_k=1000,
            gas_constant_j_kg_k=287.05,
            inlet_temperature_c=40,
            pressure_pa=[101325, 80000],
            properties_are_engineering_assumptions_not_environmental_bounds=True,
        ),
        scenarios=scenarios,
        existing_guard=dict(
            hole_count_each=len(holes),
            hole_centres_mm=holes,
            actual_48gon_net_open_area_each_mm2=guard_area,
            radius_selection_mm=16.65,
            cut_diameter_mm=4.2,
            note="Bolt holes outside fan opening are not counted as working air area.",
        ),
        candidate_air_path=candidate,
        pressure_budget_sensitivities=pressure_rows,
        candidate_covers_selected_energy_scenarios=True,
        candidate_covers_80000Pa_sensitivity=False,
        limits=[
            "Energy conservation yields a necessary bulk-air flow, not a sufficient component cooling or local temperature bound.",
            "58C air is a planning target for a proposed70C-rated control with60C body target; 2C local rise is unproved. Existing PTV09 has50C limit.",
            "Land-heat split is hypothetical; converter rows include off-package inductor/diode heat and cannot all be credited to an IC thermal pad.",
            "Base branch outlet60C with65C base goal is only an air-energy screen; no installed heat-transfer coefficient is proved.",
            "Two fans are assumed parallel with equal sharing, no recirculation, clean guards and no failed fan; actual network/flow sharing is unproved.",
            "Catalogue PQ is25C free-air data. Linear interpolation, common Q/P scaling and ideal density pressure correction are sensitivity models, not guaranteed installed curves.",
            "Cd values are sensitivities; perforation interaction, thickness, protective geometry and channel losses need measurement or defensible flow simulation.",
            "The old open under-base outlet can bypass the interior. A controlled split, sealed plenum and interior exhaust require new CAD and physical flow validation.",
            "The source ledger is provisional and predates the new negative controller; its total is a comparison scenario, not a final hot full-unit heat upper bound.",
        ],
        installed_airflow_verified=False,
        component_temperatures_verified=False,
        revised_ports_or_guards_implemented=False,
        physical_tests_performed=0,
        fabrication_released=False,
    )


def main():
    result = compute()
    ROOT.mkdir(exist_ok=True)
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    for row in result["scenarios"]:
        if row["pressure_pa"] == 101325 and row["heat_multiplier"] == 1.2:
            print(
                "base",
                round(row["assumed_heat_to_base_w"], 3),
                "W; air",
                row["interior_air_ceiling_c"],
                "C; necessary total",
                round(row["total_minimum_m3h"], 3),
                "m3/h",
            )


if __name__ == "__main__":
    main()
