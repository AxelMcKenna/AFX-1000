"""Disjoint provisional power-flow tree: endpoints + conversion + distribution once."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
SOURCES = ROOT / "sources"
P03 = SOURCES / "hardware/electronics/power_distribution/p03"


def read(path):
    return json.loads(path.read_text())


def build():
    analysis = read(P03 / "generated/analysis.json")
    state = read(P03 / "generated/bipolar-ledger.json")["base_native"]
    loads = read(SOURCES / "normalized-loads.json")
    bodies = read(
        SOURCES / "hardware/cad/a12/thermal/candidates/u102_stronger/sources/current-body/other.json"
    )
    boards = {b[0]: b[1:3] + b[4:6] for b in bodies["boards"]}
    boards["P03"] = [168, 108, 160, 45]
    boards["E28"] = boards["disconnect_carrier"]
    aliases = {
        "processor_carrier": "dsp_carrier",
        "output_stage": "audio_carrier",
        "led_driver": "led_driver",
        "E26_D_GND": "E28",
        "E26_A_GND": "E28",
    }
    tree = read_sexpr((P03 / "power_p03.kicad_pcb").read_text())
    positions = {}
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        x, y = map(float, first(fp, "at")[1:3])
        positions[ref] = [x + 68, y + 8]
    rows = []

    def add(id, watts, category, consumer, basis, part=None, extra=None):
        assert watts >= 0 and math.isfinite(watts)
        rect = None
        placement = "Endpoint not present in captured enclosure board inventory"
        if part:
            x, y = positions[part]
            rect = [x - 1.5, y - 1.5, 3, 3]
            placement = "Actual saved P03 component position; ideal3x3mm plate injection, not a physical path"
        elif consumer in aliases:
            rect = boards[aliases[consumer]]
            placement = (
                "Actual captured board projection; uniform plate injection is an assumed heat-placement model"
            )
        elif consumer == "inlet":
            rect = boards["input_power"]
            placement = (
                "Actual captured inlet board; upstream feed heat concentrated here as an explicit scenario"
            )
        row = dict(
            id=id,
            watts=watts,
            category=category,
            consumer=consumer,
            basis=basis,
            known_projected_rect_housing_mm=rect,
            heat_placement_basis=placement,
            source_part_ref=part,
            optical_or_external_export_credit_w=0,
            actual_consumption_guaranteed=False,
        )
        if extra:
            row.update(extra)
        rows.append(row)

    digital = analysis["sources"]["digital_direct_source_interval_v"][1]
    analog = analysis["sources"]["analog_local_source_interval_v"][1]
    pre = analysis["sources"]["preregulator_dc_interval_v"][1] + 0.05
    aux = analysis["auxiliary"]["source_interval_v"][1]
    eta = analysis["operating_budget"]["minimum_efficiency_allocation"]
    assert math.isclose(sum(r["current_a"] for r in loads.values() if r["domain"] == "DIG"), 2.4)
    assert math.isclose(sum(r["current_a"] for r in loads.values() if r["domain"] == "ANA"), 0.251)
    for name, load in loads.items():
        if load["domain"] not in {"DIG", "ANA"}:
            continue
        voltage = digital if load["domain"] == "DIG" else analog
        add(
            name,
            voltage * load["current_a"],
            "delivered_endpoint",
            load["node"],
            "Captured P02 independent current allocation times P03 source high; includes distribution/return dissipation",
            extra=dict(
                source_domain=load["domain"], source_voltage_v=voltage, current_allocation_a=load["current_a"]
            ),
        )
    diglocal = analysis["operating_budget"]["digital_regulator_total_a"] - 2.4
    add(
        "DIG_local_controls_and_divider",
        digital * diglocal,
        "local_control_reserve",
        "P03",
        ".018 source controls+.006 divider/local reserve, separate from2.4A external provision",
        part="U20",
    )
    digin = digital * (2.4 + diglocal) / eta
    add(
        "DIG_converter_loss",
        digital * (2.4 + diglocal) * (1 / eta - 1),
        "converter_loss",
        "P03",
        "85% efficiency allocation; includes switching/inductor loss, not separately added again",
        part="U20",
    )
    # Distinguish LDO input-to-ground current from delivered output current.
    bleed, ground = 0.003, 0.005
    add(
        "ANA_source_bleed",
        analog * bleed,
        "local_control_reserve",
        "P03",
        "Declared3mA source bleed allocation",
        part="U22",
    )
    add(
        "ANA_LDO_drop",
        (pre - analog) * (0.251 + bleed),
        "linear_drop",
        "P03",
        "Same output corner used for delivered power and dropout; excludes ground-current term",
        part="U22",
    )
    add(
        "ANA_LDO_ground",
        pre * ground,
        "local_control_reserve",
        "P03",
        "Declared5mA LDO input-ground allocation at preregulator input",
        part="U22",
    )
    anain = pre * (0.251 + bleed + ground) / eta
    add(
        "ANA_preconverter_loss",
        pre * (0.251 + bleed + ground) * (1 / eta - 1),
        "converter_loss",
        "P03",
        "85% efficiency allocation on complete preregulator output current",
        part="U23",
    )
    e28_partial = read(
        SOURCES / "hardware/electronics/rail_disconnect/revision28/generated/local-loads-partial.json"
    )
    e28_currents = e28_partial["partial_resistive_current_requirements_a"]
    raw_inputs = {}
    bipolar_external = []
    for net, raw in state["raw_local_current_ledger"].items():
        rail = raw["rail"]
        r = state["rails"][rail]
        sign = 1 if rail.startswith("P") else -1
        vout, vin = r["source_magnitude_v"][1], raw["raw_voltage_upper_v"]
        raw_ic = "U1" if net.endswith("22") else "U13"
        ldo = {"P19": "U7", "P12": "U8", "N19": "U10", "N12": "U11"}[rail]
        candidates = [
            (k, v)
            for k, v in loads.items()
            if (
                k.endswith(f"_{sign}12")
                if "12" in rail
                else k == ("output_p19" if sign > 0 else "output_n19")
            )
        ]
        assert math.isclose(
            sum(abs(v["current_a"]) for _, v in candidates), r["external_current_allocation_a"]
        )
        for name, load in candidates:
            add(
                name,
                vout * abs(load["current_a"]),
                "delivered_endpoint",
                load["node"],
                "Absolute per-sign rail power; opposite-sign currents never cancel heat",
                extra=dict(
                    source_domain=rail,
                    source_voltage_magnitude_v=vout,
                    current_allocation_a=abs(load["current_a"]),
                ),
            )
            bipolar_external.append(name)
        for field in [
            "bleed_current_upper_allocation_a",
            "presence_monitor_current_upper_a",
            "new_controller_source_current_reserved_a",
        ]:
            add(
                rail + "_" + field,
                vout * r[field],
                "local_control_reserve",
                "P03",
                "Native source bleed/presence or UNIMPLEMENTED3mA controller allocation; external budget excluded",
                part=r["bleed_ref"] if field.startswith("bleed") else ldo,
            )
        e28_current = e28_currents[rail]
        add(
            rail + "_E28_known_resistors",
            vout * e28_current,
            "delivered_endpoint",
            "E26_D_GND",
            "Partial native E28 resistor inventory not included in external board loads; future3mA controller reserve stays separate",
        )
        add(
            rail + "_LDO_drop",
            (vin - vout) * (r["source_output_current_required_a"] + e28_current),
            "linear_drop",
            "P03",
            "Raw-to-regulated voltage drop only, same output corner; regulator output current already delivered once",
            part=ldo,
        )
        for field in [
            "opamp_iq_a",
            "reference_bias_a",
            "ldo_ground_current_envelope_a",
            "control_output_and_set_reserve_a",
            "raw_feedback_current_a",
        ]:
            target = (
                "U5"
                if net == "RAW_P22" and field == "opamp_iq_a"
                else "U6"
                if net == "RAW_N22" and field == "opamp_iq_a"
                else ldo
            )
            add(
                net + "_" + field,
                vin * raw[field],
                "raw_local_consumption",
                "P03",
                "Actual native bipolar ledger term; LT3090 ground22.5mA is counted HERE, not again as heatmap+input power",
                part=target,
            )
        actual = raw["required_raw_output_current_a"] + e28_current
        enclosing = max(actual, raw["old_independent_raw_current_allocation_a"])
        add(
            net + "_unused_current_reserve",
            vin * (enclosing - actual),
            "unassigned_reserve",
            "P03",
            "Retain greater of old.05/.20A provision and complete local requirement; reserve conservatively dissipated inside",
            part=raw_ic,
        )
        raw_inputs[net] = dict(
            voltage_magnitude_v=vin,
            complete_required_a=actual,
            retained_allocation_a=enclosing,
            old_allocation_a=raw["old_independent_raw_current_allocation_a"],
            output_power_w=vin * enclosing,
        )
    assert len(bipolar_external) == 12
    for ic, nets in [("U1", ["RAW_P22", "RAW_N22"]), ("U13", ["RAW_P17", "RAW_N17"])]:
        p = sum(raw_inputs[n]["output_power_w"] for n in nets)
        add(
            ic + "_converter_loss",
            p * (1 / 0.75 - 1),
            "converter_loss",
            "P03",
            "75% dual-converter efficiency allocation; includes external diode/inductor loss, not separately added",
            part=ic,
        )
    auxiliary = analysis["auxiliary_current_and_heat"]
    add(
        "AUX_E28",
        aux * 0.060,
        "delivered_endpoint",
        "E26_D_GND",
        "60mA total E28AUX provision; fourSi8751 maxima38mA are children, not added again",
    )
    add(
        "AUX_local_resistive",
        aux * auxiliary["known_resistive_subtotal_a"],
        "local_control_reserve",
        "P03",
        "Native resistive allocations already part of90mA U102 output",
        part="U102",
    )
    add(
        "AUX_local_active",
        aux * 0.003,
        "local_control_reserve",
        "P03",
        "3mA unverified active/dynamic/leakage reserve inside90mA",
        part="U102",
    )
    add(
        "AUX_remaining_reserve",
        aux * auxiliary["remaining_current_after_external_resistive_and_active_reserve_a"],
        "unassigned_reserve",
        "P03",
        "Unused share of90mA counted as internal heat; never90mA plus60mA",
        part="U102",
    )
    add(
        "AUX_LDO_drop",
        (13.2 - aux) * 0.09,
        "linear_drop",
        "P03",
        "Same AUX voltage corner as delivered power, not independent low-corner loss plus high-corner output",
        part="U102",
    )
    add(
        "AUX_LDO_ground",
        13.2 * 0.0001,
        "local_control_reserve",
        "P03",
        "Declared100uA input-ground reserve",
        part="U102",
    )
    add(
        "VIN_control_reserve",
        13.2 * 0.030,
        "unassigned_reserve",
        "P03",
        "Retained analysis.py30mA direct-input control reserve: composition/inclusion of U21/reference and other local circuits not closed",
        part="U24",
    )
    # Complete input-feed resistance already contains both guard transistors.
    feed = read(SOURCES / "hardware/cad/a12/harness/input-feed.json")
    total_r = feed["project"]["complete_feed_scenario_ohm"]
    guard = 0.040 + 0.053
    assert total_r >= guard
    normal_i = analysis["operating_budget"]["input_normal_profile_a"]
    add(
        "Q101_guard",
        normal_i**2 * 0.040,
        "input_distribution",
        "P03",
        "4A normal-profile engineering RDS40mohm allocation",
        part="Q101",
    )
    add(
        "U101_guard",
        normal_i**2 * 0.053,
        "input_distribution",
        "P03",
        "4A full-temperature53mohm TPS2663 Ron envelope used as allocation",
        part="U101",
    )
    add(
        "inlet_wire_fuse_and_contacts",
        normal_i**2 * (total_r - guard),
        "input_distribution",
        "inlet",
        "Complete.36ohm feed requirement MINUS already-counted.093ohm guard; adapter captive cable excluded",
        extra=dict(
            complete_feed_ohm=total_r,
            counted_guard_ohm=guard,
            remaining_feed_ohm=total_r - guard,
            current_allocation_a=normal_i,
        ),
    )
    assert len({r["id"] for r in rows}) == len(rows)
    expected = (
        digin
        + anain
        + sum(r["output_power_w"] for r in raw_inputs.values()) / 0.75
        + 13.2 * (0.0901 + 0.030)
        + normal_i**2 * total_r
    )
    total = math.fsum(r["watts"] for r in rows)
    assert math.isclose(total, expected, abs_tol=1e-10), (total, expected)
    known = math.fsum(r["watts"] for r in rows if r["known_projected_rect_housing_mm"] is not None)
    nested3v3 = {k: v for k, v in loads.items() if k.endswith("3v3")}
    return dict(
        revision="WU01-provisional-complete-source-power-tree",
        leaf_heat_rows=rows,
        total_internal_heat_screen_w=total,
        source_input_crosscheck_w=expected,
        energy_tree_residual_w=total - expected,
        delivered_and_local_power_accounted_once=True,
        input_guard_not_added_again_to_complete_feed=True,
        downstream_I2R_not_added_on_top_of_full_source_delivered_power=True,
        export_credit_w=0,
        optical_export_proved=False,
        external_export_proved=False,
        known_projected_placement_power_w=known,
        unplaced_endpoint_power_w=total - known,
        retained_raw_current_envelopes=raw_inputs,
        raw_budget_reconciliation=dict(
            old_pooled_raw_output_power_w=state["existing_coupled_raw_output_power_allocation_w"],
            complete_P03_required_raw_output_power_w=state["required_steady_raw_output_power_w"],
            new_individual_enclosing_raw_output_power_w=sum(r["output_power_w"] for r in raw_inputs.values()),
            old_pooled_power_encloses_complete_P03_required_power=state[
                "existing_coupled_raw_output_power_allocation_w"
            ]
            >= state["required_steady_raw_output_power_w"],
            old_RAW_N22_current_allocation_encloses_complete_requirement=False,
            aggregate_deficit_claimed=False,
        ),
        blocks=dict(
            digital_input_w=digin,
            analog_prereg_input_w=anain,
            bipolar_converter_input_w=sum(r["output_power_w"] for r in raw_inputs.values()) / 0.75,
            aux_complete_input_w=13.2 * 0.0901,
            other_VIN_control_reserve_w=13.2 * 0.030,
            complete_input_feed_heat_w=normal_i**2 * total_r,
        ),
        E28_partial_native_inventory=dict(
            source_and_native_metadata_agree=e28_partial["native_netlist_and_component_metadata_agree"],
            currents=e28_currents,
            all_currents_covered=False,
            bipolar_known_resistors_added_separately_from_future_controller_reserve=True,
            five_volt_known_resistors_assigned_inside_existing_DIG416mA_ANA8mA_reserves=True,
            four_Si8751_38mA_assigned_inside_AUX60mA=True,
            missing=e28_partial["missing"],
        ),
        nested_3v3_diagnostics=dict(
            loads=nested3v3,
            nominal_child_output_power_w=3.3 * sum(abs(r["current_a"]) for r in nested3v3.values()),
            separately_added_to_heat_w=0,
            parent="seed_local5V/1A allocation",
            actual_child_and_parent_current_inventory_closed=False,
        ),
        ground_current_diagnostic_excluded=dict(
            id="input_return",
            current_a=loads["input_return"]["current_a"],
            added_w=0,
            reason="Return-current signed basis is not another voltage source; branch input power already includes shared-return loss",
        ),
        old_supply_only_heatmap_w=read(P03 / "generated/heatmap.json")[
            "total_conservative_loss_allocation_w"
        ],
        actual_whole_unit_heat_upper_w=None,
        actual_source_current_upper_a=None,
        physical_tests_performed=0,
        whole_unit_heat_qualified=False,
        source_overhead_and_simultaneous_hot_capacity_qualified=False,
        assumptions=[
            "All declared source power including unused reserves becomes heat inside enclosure; no optical/audio/external export credit",
            "Digital/analog/bipolar/aux load figures are provisions, not complete measured full-temperature load bounds",
            "Source voltage intervals include unverified leakage/aging/dynamic assumptions;85/75percent efficiency minima are not guaranteed at actual hot loads",
            "3V3 consumer output is nested within Seed5V allocation; no additional supply source/efficiency has been proved",
            "P03local.024A DIG/.008A ANA and E28global reserve allocations may overlap in an eventual inventory; retained as conservative separate capacity pools, never asserted actual consumed currents",
            "Bipolar3mA/rail new-controller allocation is unimplemented; actual E28 bleeds/monitor current inventory is not yet closed",
            "P03VIN30mA reserve is unpartitioned; actual reference/logic/dynamic loads must be assigned to it or increase envelope",
            "Complete input-feed.36ohm and4A normal-profile are engineering requirements, not measured upper bounds; external adapter AC conversion/captive cable are outside plug boundary",
            "This steady screen does not cover startup cycling, short circuits, overload/hiccup or external injected signal power",
        ],
    )


def main():
    a = build()
    paths = [Path(__file__).resolve(), ROOT / "capture.json", *[p for p in SOURCES.rglob("*") if p.is_file()]]
    a["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in paths}
    OUT.mkdir(exist_ok=True)
    (OUT / "ledger.json").write_text(json.dumps(a, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: a[k]
                for k in [
                    "total_internal_heat_screen_w",
                    "blocks",
                    "unplaced_endpoint_power_w",
                    "energy_tree_residual_w",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
