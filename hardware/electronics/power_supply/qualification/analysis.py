"""Audit the actual routed supply; conditional models never become physical passes."""

import argparse
import contextlib
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.sexpr import children, first, read_sexpr
from .. import verify
from ..routing import check as copper

ROOT = Path(__file__).resolve().parent
SUPPLY = ROOT.parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated"
NATIVE = OUT / "native-routing"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def resistor(parts, ref):
    return verify.number(parts[ref].findtext("value"))


def buck_interval(top, bottom, reference, tolerance=0.001, bias=150e-9):
    assert top > 0 and bottom > 0 and 0 <= tolerance < 1 and bias >= 0
    values = [
        v * (1 + top * (1 + a * tolerance) / (bottom * (1 + b * tolerance)))
        + leak * top * (1 + a * tolerance)
        for v, a, b, leak in itertools.product(reference, (-1, 1), (-1, 1), (-bias, bias))
    ]
    return [min(values), max(values)]


def divider_interval(bottom, reference, low=4.9, high=5.1, excursion=0.010, loss=0.0):
    """Solve for nominal upper R; all correlated component corners retained."""
    tolerance, bias = 0.001, 150e-9
    minimum = (low + excursion + loss - reference[0]) / (
        reference[0] * (1 - tolerance) / (bottom * (1 + tolerance)) - bias * (1 - tolerance)
    )
    maximum = (high - excursion - reference[1]) / (
        reference[1] * (1 + tolerance) / (bottom * (1 - tolerance)) + bias * (1 + tolerance)
    )
    return dict(minimum_top_ohm=minimum, maximum_top_ohm=maximum, feasible=minimum <= maximum)


def critical_pins(tree):
    """Independent checks for hazardous tab/pin identities, not just net names."""
    footprints = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    result = {}
    for ref, terminal, expected in [
        ("U1", "11", "AGND"),
        ("U13", "11", "AGND"),
        ("U7", "9", "P19_SRC"),
        ("U8", "3", "P12_SRC"),
        ("U9", "9", "V5_REG_SRC"),
        ("U10", "11", "RAW_N22"),
        ("U11", "11", "RAW_N17"),
    ]:
        pads = [p for p in children(footprints[ref], "pad") if str(p[1]) == terminal]
        assert pads and all(str(first(p, "net")[-1]).lstrip("/") == expected for p in pads), ref
        result[ref] = dict(terminal=terminal, net=expected, physical_lands=len(pads))
    for ref in ("U10", "U11"):
        pads = {
            str(p[1]): str(first(p, "net")[-1]).lstrip("/") for p in children(footprints[ref], "pad") if p[1]
        }
        assert pads["8"] == pads["9"] == pads["10"] == pads["11"], ref
    return result


def no_enable_isolation(pins):
    """An unpowered boost switch does not break its VIN→L→diode→output path."""
    paths = []
    for ind, diode, switch, output in [
        ("L1", "D1", "RAW_P_SW", "RAW_P22"),
        ("L6", "D3", "LO_P_SW", "RAW_P17"),
    ]:
        assert pins[ind] == {"1": "VIN_PROTECTED", "2": switch}
        assert pins[diode] == {"1": output, "2": switch}
        paths.append(dict(inductor=ind, diode=diode, output=output, passive_precharge_path_present=True))
    return dict(
        paths=paths, shutdown_is_input_isolation=False, actual_precharge_voltage_or_time_verified=False
    )


def input_budget(screen, digital_current, guard):
    """Extend the declared 1.8 A screen without pretending P02 is installed."""
    base = screen["power"]["maximum_allocated_input_power_w"]
    extra = (digital_current - 1.8) * 5.1 / 0.85
    overhead = guard["maximum_allocated_steady_input_a"] - base / 10.5
    steady = (base + extra) / 10.5 + overhead
    ramp = guard["inrush_current_allocation_a"] + guard["digital_preconnected_bulk_ramp_input_allocation_a"]
    limit = guard["efuse_allocated_limit_a"][0]
    return dict(
        digital_load_a=digital_current,
        supply_input_power_allocation_w=base + extra,
        guard_and_auxiliary_input_allocation_a=overhead,
        steady_input_a=steady,
        preconnected_digital_and_input_bus_ramp_a=ramp,
        combined_input_a=steady + ramp,
        guard_minimum_limit_allocation_a=limit,
        steady_screen_passes=steady < limit,
        conditional_startup_screen_passes=steady + ramp < limit,
        other_rail_charging_included=False,
        late_closure_current_bounded=False,
        guaranteed_manufacturer_limit=False,
        physical_input_or_startup_verified=False,
    )


def protected_bulk(parts, model_bound):
    rows = {c["ref"]: c for c in parts}
    nominal = verify.number(rows["C20"]["part"])
    assert "20%" in rows["C20"]["part"] and {p["net"] for p in rows["C20"]["pins"]} == {"V5_REG", "AGND"}
    maximum = nominal * 1.2
    return dict(
        reference="rail_disconnect:C20",
        part=rows["C20"]["part"],
        nominal_f=nominal,
        tolerance_maximum_f=maximum,
        p02_declared_analog_upper_bound_f=model_bound,
        p02_bound_covers_this_single_capacitor=model_bound >= maximum,
        includes_other_board_or_harness_capacitance=False,
        effective_capacitance_esr_or_leakage_physically_verified=False,
    )


def p02_cap_scenario():
    """Read the corrected, source-bound scenario, not a historical hardcoded bound."""
    report = load(REPO / "hardware/electronics/power_distribution/p02/generated/analysis.json")
    return report["operating_limits"]["startup"]["capacitance_inventory"]["ANA"]["scenario_capacitance_f"]


def analyze():
    parts, pins = netlist(OUT / "netlist.xml")
    verify.contract(parts, pins)
    mapping = load(SUPPLY / "supply-map.json")
    target = load(SUPPLY / "integration.json")["normal_targets_v"]
    original = verify.corners(parts, mapping)
    original["power"] = verify.power_screen(parts, mapping)
    thermal = verify.dropout_and_thermal(original)
    tree = read_sexpr((SUPPLY / "routing/power_supply.kicad_pcb").read_text())
    paths = copper.local_paths(tree)
    top = sum(resistor(parts, n) for n in ("R10", "R51"))
    bottom = resistor(parts, "R11")
    conditional = buck_interval(top, bottom, [0.788, 0.812])
    full = buck_interval(top, bottom, [0.784, 0.816])
    current, excursion = 1.801, 0.010
    # These are the existing project's contact/switch allocations, not selected
    # hardware guarantees. Even zero wire cannot rescue this allocated corner.
    contact_each, contact_count, switch_star = 0.001, 4, 0.0035
    minimal_path = contact_count * contact_each + switch_star
    at_load = [conditional[0] - excursion - current * minimal_path, conditional[1] + excursion]
    analog = next(r for r in original["linear_stages"] if r["name"] == "V5_REG")
    analog_span = [analog["minimum_magnitude_v"], analog["maximum_magnitude_v"]]
    rho = 1.724e-8 * (1 + 0.00393 * (85 - 20))
    trace_estimates = {}
    for name, amps in [
        ("n19_load_header", 0.025),
        ("n12_load_header", 0.15),
        ("output_header", 1.8),
        ("input_feed", 2.42152380952381),
    ]:
        p = paths[name]
        trace_estimates[name] = dict(
            length_mm=p["length_mm"],
            minimum_width_mm=p["minimum_track_width_mm"],
            current_a=amps,
            assumed_temperature_c=85,
            copper_material_model_assumed=True,
            resistance_and_drop_by_hypothetical_finished_copper={
                str(um): dict(
                    trace_only_resistance_ohm=rho
                    * p["length_mm"]
                    / (p["minimum_track_width_mm"] * um * 1e-6),
                    trace_only_drop_v=amps * rho * p["length_mm"] / (p["minimum_track_width_mm"] * um * 1e-6),
                )
                for um in (35, 70)
            },
            vias_pad_spreading_connectors_and_returns_included=False,
            source_feedback_compensates_positive_path=(name == "output_header"),
            fabricated_resistance_or_ampacity_qualified=False,
        )
    guard = load(REPO / "hardware/electronics/input_protection/generated/electrical-screens.json")["load"]
    gaps = [
        dict(
            id="PSU-01",
            status="failed",
            issue="Full-junction-temperature digital accuracy misses the source target and admits no valid divider.",
            required_change="Tighter regulator/reference accuracy or an implemented and verified junction restriction; changing R10/R51 alone is insufficient.",
        ),
        dict(
            id="PSU-02",
            status="failed",
            issue="Conditional 0–85 C digital accuracy still misses the allocated load boundary with only switch/star and four contacts, before wire.",
            required_change="A complete source-to-load architecture with sufficient accuracy and a realizable resistance/return budget.",
        ),
        dict(
            id="PSU-03",
            status="failed",
            issue="At the new 2.4 A digital reserve, even the narrow preconnected startup input screen exceeds the old guard limit allocation.",
            required_change="Select and implement compatible input protection/current capacity and full startup/inrush design; do not treat P02 as installed.",
        ),
        dict(
            id="PSU-04",
            status="blocked",
            issue="No actual copper stackup, via plating or tolerance certificate is encoded; temperature and ground transfer are unqualified.",
            required_change="Fabricator stackup plus actual filled-copper multiport resistance/thermal extraction and measurement.",
        ),
        dict(
            id="PSU-05",
            status="blocked",
            issue="5 V buck sees millifarad protected capacitance after disconnect closure; no full connected-network compensation/startup proof.",
            required_change="Actual capacitor MPN/effective C/ESR model, selected switch closure behavior, Bode/load-step/startup qualification.",
        ),
        dict(
            id="PSU-06",
            status="blocked",
            issue="Positive boost rails have passive input precharge paths with switches disabled.",
            required_change="Qualify asymmetric/partial-power startup and discharge, or implement isolation where the final architecture requires it.",
        ),
        dict(
            id="PSU-07",
            status="blocked",
            issue="Raw ±22 V switch stress has only a 3 V unverified ringing allocation; hot loops and ground displacement remain unmeasured.",
            required_change="Measure loaded/hot edge ringing at each SW pin against its own local GND; validate final compensation/EMI behavior.",
        ),
        dict(
            id="PSU-08",
            status="blocked",
            issue="LDO SET loops, real output caps, reverse paths, short recovery and thermal coupling are not qualified.",
            required_change="Manufacturer-model analysis and board tests under actual wiring, load and thermal conditions.",
        ),
    ]
    return dict(
        revision="PSU-Q01",
        board="E14 actual 157-part main-supply routing candidate; not P02",
        native_pin_value_contract_passed=True,
        critical_tab_and_limit_pins=critical_pins(tree),
        source_corner_scope="Native values and declared error allocations, referred to each source feedback reference; real port ground displacement is not bounded.",
        source_linear_corner_intervals=original["linear_stages"],
        digital=dict(
            upper_resistor_ohm=top,
            lower_resistor_ohm=bottom,
            resistor_error_allocation_fraction=0.001,
            fb_leakage_bound_a=150e-9,
            source_target_v=target["5V_DIG"],
            conditional_0_to_85c_dc_v=conditional,
            full_minus40_to_150c_dc_v=full,
            full_temperature_with_excursion_v=[full[0] - excursion, full[1] + excursion],
            full_temperature_source_screen_passes=full[0] - excursion >= 4.9 and full[1] + excursion <= 5.1,
            full_temperature_divider_solution=divider_interval(bottom, [0.784, 0.816]),
            conditional_source_divider_solution=divider_interval(bottom, [0.788, 0.812]),
            conditional_load_divider_solution=divider_interval(
                bottom, [0.788, 0.812], loss=current * minimal_path
            ),
            excursion_allocation_v=excursion,
            downstream_current_a=current,
            downstream_minimal_allocated_path_ohm=minimal_path,
            contact_count=contact_count,
            each_contact_allocated_ohm=contact_each,
            switch_and_star_allocated_ohm=switch_star,
            conditional_load_interval_before_wire_v=at_load,
            conditional_load_screen_passes=at_load[0] >= 4.9 and at_load[1] <= 5.1,
            source_margin_remaining_for_all_path_ohm=(conditional[0] - 4.9 - excursion) / current,
            junction_restriction_physically_verified=False,
        ),
        analog_5v=dict(
            source_interval_v=analog_span,
            target_v=target["V5_REG"],
            maximum_total_drop_resistance_with_no_extra_ripple_ohm=(analog_span[0] - target["V5_REG"][0])
            / 0.251,
            existing_switch_and_star_allocation_ohm=0.0065,
            excludes_shared_return_and_additional_ripple=True,
            full_distribution_qualified=False,
        ),
        input_profiles={str(amps): input_budget(original, amps, guard) for amps in (1.8, 2.4)},
        thermal_requirements=thermal,
        actual_stackup_present=bool(children(first(tree, "setup"), "stackup")),
        actual_track_count=len(children(tree, "segment")),
        actual_via_count=len(children(tree, "via")),
        single_path_trace_only_hypotheses=trace_estimates,
        required_extraction_inputs=[
            "Minimum finished copper and tolerances per layer, not nominal starting foil",
            "Via finished barrel plating, hole diameter, layer spans and actual parallel attachment paths",
            "Fabricated line width/etch tolerances and measured hot conductor temperature",
            "Native filled-plane polygons with neck/pad spreading and cutouts, all return ports and source/load current vectors",
            "Contact/joint/wire material, dimensions, hot/end-of-life resistance and assembly process",
            "Thermal stackup, dielectric conductivity, airflow, enclosure and inter-board heat coupling",
        ],
        enable_off_topology=no_enable_isolation(pins),
        protected_analog_bulk=protected_bulk(
            load(REPO / "hardware/electronics/rail_disconnect/components.json"), p02_cap_scenario()
        ),
        p02_is_implemented_on_this_board=False,
        p02_capacitance_erratum=dict(
            historical_analog_capacitance_claim_f=0.0011,
            actual_retained_c20_nominal_f=0.0015,
            actual_retained_c20_tolerance_maximum_f=0.0018,
            historical_complete_upper_bound_invalid=True,
            corrected_analog_scenario_f=p02_cap_scenario(),
            corrected_total_network_bound_is_qualified=False,
            scope="Corrected P02 arithmetic does not implement or qualify P02 on this E14 PCB; archived original packets remain immutable",
        ),
        findings=gaps,
        analytical_acceptance_failed=True,
        physical_measurements_performed=0,
        electrical_performance_qualified=False,
        thermal_qualified=False,
        startup_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )


def native(cli):
    NATIVE.mkdir(parents=True, exist_ok=True)
    frozen = {
        p: sha(p)
        for p in SUPPLY.rglob("*")
        if p.is_file()
        and ROOT not in p.parents
        and "__pycache__" not in p.parts
        and p.suffix not in (".kicad_prl", ".lck")
    }
    shutil.copy2(SUPPLY / "routing/generated/routing-inputs.json", NATIVE / "routing-inputs.json")
    original_out, original_argv = copper.OUT, sys.argv
    try:
        copper.OUT = NATIVE
        sys.argv = ["qualification-native-routing", "--kicad-cli", str(cli)]
        with (OUT / "native-routing-log.txt").open("w") as log, contextlib.redirect_stdout(log):
            copper.main()
    finally:
        copper.OUT, sys.argv = original_out, original_argv
    with tempfile.TemporaryDirectory(prefix="afx-psu-qualification-") as directory:
        env = dict(os.environ, KICAD_CONFIG_HOME=str(Path(directory) / "config"))

        def run(*args):
            p = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert p.returncode == 0, (args, p.stdout, p.stderr)

        run(
            "sch",
            "erc",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "erc.json",
            SUPPLY / "power_supply.kicad_sch",
        )
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            SUPPLY / "power_supply.kicad_sch",
        )
    assert all(sha(p) == h for p, h in frozen.items()), "Qualification changed frozen parent source/evidence"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.kicad_cli:
        native(args.kicad_cli.resolve())
    record = analyze()
    native_record = load(NATIVE / "verification.json")
    for source, expected in native_record["source_sha256"].items():
        assert sha(SUPPLY / "routing" / source) == expected, (
            "Native routing evidence is stale; repeat --kicad-cli before certifying it",
            source,
        )
    erc = load(OUT / "erc.json")
    issues = [v for sheet in erc.get("sheets", []) for v in sheet.get("violations", [])]
    assert not issues, issues
    record["native_checks"] = dict(
        checked_at_utc=native_record["checked_at_utc"],
        components=native_record["components"],
        drc=native_record["native_drc_violations"],
        parity=native_record["schematic_parity_issues"],
        opens=native_record["unconnected_items"],
        erc=len(issues),
        independent_paths=len(native_record["local_paths"]),
        native_closure_is_physical_qualification=False,
    )
    files = [
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.name not in ("analysis.json", "qualification-run.txt")
    ]
    files += [
        SUPPLY / n
        for n in [
            "components.json",
            "supply-map.json",
            "integration.json",
            "verify.py",
            "power_supply.kicad_sch",
            "routing/power_supply.kicad_pcb",
        ]
    ]
    files += list((SUPPLY / "routing").glob("*.py"))
    files += [
        REPO / "hardware/electronics/input_protection/generated/electrical-screens.json",
        REPO / "hardware/electronics/rail_disconnect/components.json",
        REPO / "hardware/electronics/power_distribution/p02/analysis.py",
        REPO / "hardware/electronics/power_distribution/p02/generated/analysis.json",
        REPO / "tests/tooling/test_power_supply_qualification.py",
    ]
    record["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in sorted(set(files)) if p.exists()}
    record["source_base_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()
    content = json.dumps(record, indent=2) + "\n"
    target = OUT / "analysis.json"
    if args.check:
        saved = load(target)
        record["source_base_commit"] = saved["source_base_commit"]
        assert saved == record, "Stale main-supply qualification analysis"
    else:
        target.write_text(content)
    print(
        "Main supply: native closure passes; full-temperature/source-to-load/startup screens FAIL; physical qualification remains blocked"
    )


if __name__ == "__main__":
    main()
