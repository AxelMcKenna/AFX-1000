"""P03 source-to-load and current/heat bounds, with unresolved inputs explicit."""

import argparse
import hashlib
import itertools
import json
import math

from ...common.netlists import netlist, number
from ..p02 import distribution as retained_wiring
from . import buck_control, internal_pg, models
from .check import contract
from .spec import REPO, ROOT

OUT = ROOT / "generated"


def buck_interval(top, bottom, reference=(0.4975, 0.5025), resistor_error=0.001, bias=0.1e-6):
    assert top > 0 and bottom > 0 and 0 <= resistor_error < 1 and bias >= 0
    values = [
        v * (1 + top * (1 + a * resistor_error) / (bottom * (1 + b * resistor_error)))
        + leak * top * (1 + a * resistor_error)
        for v, a, b, leak in itertools.product(reference, (-1, 1), (-1, 1), (-bias, bias))
    ]
    return [min(values), max(values)]


def source_bounds(parts):
    def r(ref):
        return number(parts[ref].findtext("value"))

    digital = buck_interval(r("R200") + r("R206"), r("R201"), resistor_error=0.00102)
    prereg = buck_interval(r("R220"), r("R221"))
    # Original P02 guaranteed reference terms remain; the new filter has 100ohm
    # rather than10kOhm, so no fictitious millifarad reference ramp is required.
    ref_terms = dict(
        initial=0.001,
        box_temperature=5 * 2e-6 * 165,
        line=5 * 10e-6 * 9.9,
        load=5 * 80e-6 * 0.001,
        assembly_aging_humidity_allocation=0.002,
        opamp_offset=0.000350,
        positive_bias=10e-9 * r("R240"),
    )
    common = sum(ref_terms.values())
    leakage = 0.1e-6 * r("R240")  # allocated aggregate hot/aged filter leakage, not guaranteed
    ratio = r("R242") / r("R243")
    lowgain = 1 + ratio * 0.999 / 1.001
    highgain = 1 + ratio * 1.001 / 0.999
    negative_bias = 5e-9 * (r("R244") + r("R242") * r("R243") / (r("R242") + r("R243")))
    ldo_error = 0.002 + 0.0005 + 0.0003 + 0.000054
    analog = [
        (5 - common - leakage - negative_bias) * lowgain - ldo_error,
        (5 + common + negative_bias) * highgain + ldo_error,
    ]
    return dict(DIG=digital, ANA=analog), dict(
        digital_reference_interval_v=[0.4975, 0.5025],
        digital_full_junction_reference_range_c=[-40, 150],
        digital_feedback_bias_current_bound_a=0.1e-6,
        feedback_bias_bound_manufacturer_guaranteed=False,
        precision_resistor_total_error_fraction=0.001,
        digital_divider_enclosing_error_fraction=0.00102,
        digital_main_resistor_total_error_fraction=0.001,
        digital_series_trim_total_error_fraction=0.003,
        precision_error_is_lifetime_guarantee=False,
        reference_symmetric_terms_v=ref_terms,
        reference_hot_aged_filter_leakage_allocation_a=0.1e-6,
        reference_capacitor_leakage_manufacturer_guaranteed=False,
        analog_ldo_set_to_output_error_allowance_v=ldo_error,
        digital_direct_source_interval_v=digital,
        analog_local_source_interval_v=analog,
        preregulator_dc_interval_v=prereg,
        digital_lT3083_present=False,
        regulator_feedback_crosses_disconnect=False,
    )


def endpoints(
    sources,
    switch_ohm=None,
    input_current=4.0,
    contact_max=0.002,
    positive_link=0.002,
    source_port=0.001,
    ground_bar=0.002,
):
    """Independent source/load intervals with the actual revised port roles.

    Remove old AGND cable edges: the dedicated bars replace those paths.
    No perfect contact, current cancellation, or equal branch sharing is used.
    """
    switch_ohm = switch_ohm or dict(DIG=0.020 / 4, ANA=0.020 / 3)
    edges = [
        e for e in retained_wiring.ground_edges(contact_max) if e[3] not in {"PWR-ANALOG", "PWR-DIGITAL"}
    ]
    edges = [
        (a, b, ground_bar if h in {"P02-NEW-ANALOG-RETURN-STRAP", "P02-NEW-DIGITAL-RETURN-STRAP"} else r, h)
        for a, b, r, h in edges
    ]
    nodes, z = retained_wiring.transfer_bounds(edges)
    result = {}
    switch_max = {}
    for name, endpoint in retained_wiring.endpoints(contact_max).items():
        row = dict(endpoint, paths=dict(endpoint["paths"]))
        rail, board = row["rail"], row["board"]
        row["paths"][rail] = positive_link + source_port + 0.003 + switch_ohm[rail]
        dynamic = 0.003 if rail == "ANA" else 0.020
        spread = 0.0005 if rail == "ANA" else 0.002
        low, high = sources[rail][0] - dynamic - spread, sources[rail][1] + dynamic + spread
        losses = []
        for load, (loadrail, return_node, maximum) in retained_wiring.LOADS.items():
            if load == "input_return":
                maximum = -input_current
            _, upper = z[board, return_node]
            positive = retained_wiring.positive_loss(row, load, contact_max)
            if maximum >= 0:
                term = maximum * (upper + positive)
                low -= term
                losses.append((load, term))
            else:
                high -= maximum * upper
        target = [4.975, 5.025] if rail == "ANA" else [4.9, 5.1]
        row.update(
            minimum_v=low,
            maximum_v=high,
            target_v=target,
            passes=low >= target[0] and high <= target[1],
            switch_path_max_ohm=switch_ohm[rail],
            largest_low_losses_v=sorted(losses, key=lambda x: x[1], reverse=True)[:4],
        )
        total_current = sum(i for r, _, i in retained_wiring.LOADS.values() if r == rail)
        switch_max[name] = switch_ohm[rail] + (low - target[0]) / total_current
        result[name] = row
    return dict(
        endpoints=result,
        all_pass=all(x["passes"] for x in result.values()),
        ground_nodes=nodes,
        ground_edges=[dict(a=a, b=b, max_ohm=r, min_ohm=0, harness=h) for a, b, r, h in edges],
        maximum_switch_path_ohm_by_rail={
            r: min(switch_max[n] for n, x in result.items() if x["rail"] == r) for r in ("DIG", "ANA")
        },
        source_positive_link_end_to_end_acceptance_ohm=positive_link,
        additional_source_regulator_to_stud_copper_bound_ohm=source_port,
        e28_branch_copper_separate_bound_ohm=0.003,
        ground_bar_end_to_end_bound_ohm=ground_bar,
        input_guard_return_current_bound_a=input_current,
        old_generic_positive_headers_are_operating_ports=False,
        all_contacts_and_copper_measured=False,
        physical_harness_qualified=False,
        resistance_interval_method="Rayleigh/effective-resistance polarization for every independent R in [0,Rmax]; independent signed load intervals",
        physical_topology_note="Positive M3 stud leads replace source5V header current; dedicated bars replace old source/AGND cable paths.",
    )


def guard_limit(resistor):
    # Explicit manufacturer full-temperature4.02k point; not interpolation from
    # a typical18000/R curve. Temperature of the resistor is independent of IC Tj.
    assert math.isclose(resistor, 4020, rel_tol=1e-12), (
        "A different R needs a separately supported current-limit envelope"
    )
    tolerance = 0.003
    return dict(
        nominal_resistor_ohm=resistor,
        resistor_total_error_fraction=tolerance,
        manufacturer_nominal_resistor_test_current_a=[4.185, 4.815],
        current_interval_a=[4.185 / (1 + tolerance), 4.815 / (1 - tolerance)],
        manufacturer_conditions="TPS2663 RevG6.5,-40..125C,VIN-OUT1V,RILIM4.02k; reciprocalR propagation is a design model",
        full_fault_energy_and_adapter_coordination_verified=False,
    )


def power_and_heat(sources, details, raw):
    digital_current = 2.4 + 0.018 + 0.006  # protected load, retained source controls, divider/local reserve
    analog_current = 0.251 + 0.003 + 0.005  # protected load, bleed, conservative LDO ground current
    raw = sum(
        (p["positive_envelope_v"][1] + p["negative_magnitude_envelope_v"][1])
        * p["load_allocation_each_a"]
        / 0.75
        for p in raw["pairs"]
    )
    digital_power = sources["DIG"][1] * digital_current / 0.85
    analog_power = (details["preregulator_dc_interval_v"][1] + 0.05) * analog_current / 0.85
    aux_current = 0.090  # at source12V: previous75mA plus newdriver/controlreserve15mA
    total = raw + digital_power + analog_power + 13.2 * 0.030
    steady = total / 9.8 + aux_current
    digital_loss = digital_power - sources["DIG"][1] * digital_current
    analog_ldo = (details["preregulator_dc_interval_v"][1] + 0.05 - sources["ANA"][0]) * analog_current
    guard_loss = 4**2 * 0.053  # TPS2663max53mOhm fullrange, nottypical31mOhm
    return dict(
        digital_protected_a=2.4,
        analog_protected_a=0.251,
        digital_regulator_total_a=digital_current,
        analog_regulator_total_a=analog_current,
        minimum_efficiency_allocation=0.85,
        efficiency_is_manufacturer_guaranteed_at_this_operating_point=False,
        protected_input_power_w=total,
        guard_and_auxiliary_input_current_allocation_a=aux_current,
        maximum_steady_input_current_a=steady,
        input_normal_profile_a=4.0,
        steady_input_screen_passes=steady < 4.0,
        removed_Lt3083_pass_control_heat_w=3.52,
        new_digital_buck_total_loss_allocation_w=digital_loss,
        analog_postregulator_loss_w=analog_ldo,
        input_guard_4a_hot_loss_w=guard_loss,
        required_digital_complete_theta_c_per_w=(110 - 60) / digital_loss,
        required_guard_complete_theta_c_per_w=(110 - 60) / guard_loss,
        actual_board_theta_extracted=False,
        chassis_thermal_path_implemented=False,
        analog_dropout_margin_with_50mv_prereg_ripple_v=details["preregulator_dc_interval_v"][0]
        - 0.05
        - sources["ANA"][1]
        - 0.45,
        controller_soft_start_4ms_is_typical_not_guaranteed=True,
    )


def analyze():
    parts, pins = netlist(OUT / "netlist.xml")
    contract(parts, pins)
    sources, details = source_bounds(parts)
    raw = models.raw_sources(parts)
    budget = power_and_heat(sources, details, raw)
    startup = models.disconnect_startup()
    digital_start_power = (
        budget["protected_input_power_w"]
        + sources["DIG"][1] * startup["DIG"]["maximum_capacitor_current_a"] / 0.85
    )
    report = dict(
        revision="P03",
        scope="New complete native supply, distinct from legacyE14 and unimplementedP02",
        component_count=len(parts),
        sources=details,
        source_to_load=endpoints(sources),
        input_guard=guard_limit(number(parts["R107"].findtext("value"))),
        operating_budget=budget,
        raw_sources=raw,
        auxiliary=models.auxiliary(parts),
        auxiliary_current_and_heat=models.auxiliary_current(parts),
        external_ready_interface=models.ready_interface(parts),
        source_valid=models.source_valid(parts),
        internal_pg_logic=internal_pg.evaluate(parts, pins),
        buck_control_and_capacitance=buck_control.screen(parts, pins),
        negative_monitor=models.negative_monitor(parts),
        known_direct_input_capacitance=models.capacitors(parts, pins, "VIN_PROTECTED"),
        disconnect_startup=startup,
        selected_input_chain=models.complete_input_chain(
            parts, budget["protected_input_power_w"], digital_start_power
        ),
        feed_scenario=dict(
            minimum_delivered_inlet_v=11.4,
            total_series_resistance_allocation_ohm=0.36,
            aggregate_series_resistance_verified=False,
            known_VH_environmental_contact_bound_ohm=4 * 0.020,
            rear_mandatory_fuse="0451006.MRL6A; exact hot operating resistance must be selected/bounded",
            redundant_P03_fuse_present=False,
            protected_steady=models.constant_power_feed(11.4, 0.36, budget["protected_input_power_w"], 0.09),
            protected_digital_start=models.constant_power_feed(11.4, 0.36, digital_start_power, 0.09),
            staged_digital_start_power_w=digital_start_power,
            complete_input_feed_and_adapter_qualified=False,
        ),
        board_routing_complete=False,
        physical_tests_performed=0,
        thermal_qualified=False,
        startup_qualified=False,
        source_to_load_physically_qualified=False,
        fabrication_released=False,
        build_ready=False,
        source_sha256={
            str(p.relative_to(REPO)): sha256(p)
            for p in [
                ROOT / "power_p03.kicad_sch",
                OUT / "netlist.xml",
                ROOT / "components.json",
                ROOT / "spec.py",
                ROOT / "analysis.py",
                ROOT / "models.py",
                ROOT / "buck_control.py",
                ROOT / "internal_pg.py",
                ROOT / "component-selections.json",
                ROOT / "check.py",
                REPO / "hardware/electronics/power_distribution/p02/distribution.py",
            ]
        },
    )
    return report


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    # Source-to-load diagnostics contain sorted (name, loss) tuples. JSON stores
    # those as arrays; compare the actual serialized schema rather than making
    # every unchanged report fail freshness on Python tuple/list differences.
    report = json.loads(json.dumps(analyze()))
    dest = OUT / "analysis.json"
    if a.check:
        assert json.loads(dest.read_text()) == report, "P03analysisstale"
    else:
        dest.write_text(json.dumps(report, indent=2) + "\n")
    print("P03conditionalendpointscreen:", report["source_to_load"]["all_pass"], "physical/release:false")
    for rail, limit in report["source_to_load"]["maximum_switch_path_ohm_by_rail"].items():
        print(rail, "maximumswitchR", limit)


if __name__ == "__main__":
    main()
