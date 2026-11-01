"""P03 native circuit mutations and independent electrical boundary checks."""

import copy
import math
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.electronics.power_distribution.p03 import analysis, models
from hardware.electronics.power_distribution.p03.check import contract
from hardware.electronics.power_distribution.p03.spec import ROOT


class ReplacementPower(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.pins = netlist(ROOT / "generated/netlist.xml")

    def mutate_value(self, ref, text):
        p = copy.deepcopy(self.parts)
        p[ref].find("value").text = text
        return p

    def test_circuit_rejects_swapped_ti_pin_and_live_exposed_pad(self):
        contract(self.parts, self.pins)
        for ref, pin, wrong in (("U20", "10", "AGND"), ("U11", "11", "AGND"), ("U24", "8", "RAW_P22")):
            with self.subTest(ref=ref):
                pins = copy.deepcopy(self.pins)
                pins[ref][pin] = wrong
                with self.assertRaises(AssertionError):
                    contract(self.parts, pins)

    def test_reference_bypass_cannot_replace_compensation_capacitor(self):
        contract(self.parts, self.pins)
        with self.assertRaises(AssertionError):
            contract(self.mutate_value("C73", "100nF 50V X7R"), self.pins)
        with self.assertRaises(AssertionError):
            contract(self.mutate_value("C72", "68pF 50V C0G"), self.pins)
        pins = copy.deepcopy(self.pins)
        pins["U13"]["5"] = "RAW_N17"
        with self.assertRaises(AssertionError):
            contract(self.parts, pins)

    def test_old_guard_limit_cannot_be_claimed_for_different_resistor(self):
        r = analysis.guard_limit(4020)
        self.assertGreaterEqual(r["current_interval_a"][0], 4)
        self.assertLessEqual(r["current_interval_a"][1], 5)
        with self.assertRaises(AssertionError):
            analysis.guard_limit(4990)

    def test_feedback_corners_contain_nominal_and_reject_unregulated_5v_bias(self):
        bounds = analysis.buck_interval(9076.04, 1000)
        self.assertLess(bounds[0], 0.5 * (1 + 9076.04 / 1000))
        self.assertGreater(bounds[1], 0.5 * (1 + 9076.04 / 1000))
        # A nominal 5V ±1% source cannot absorb the actual downstream resistance
        # and dynamic allocation, its initial no-load error and downstream losses.
        ideal = analysis.endpoints({"DIG": [4.95, 5.05], "ANA": [4.95, 5.05]})
        self.assertFalse(ideal["all_pass"])

    def test_parallel_switch_bound_requires_both_rail_specific_counts(self):
        sources, _ = analysis.source_bounds(self.parts)
        proper = analysis.endpoints(sources)
        self.assertTrue(proper["all_pass"])
        single = analysis.endpoints(sources, {"DIG": 0.023, "ANA": 0.023})
        self.assertFalse(single["all_pass"])
        # An unsupported equal current sharing assumption cannot hide one
        # digital branch remaining OFF after startup.
        missing = analysis.endpoints(sources, {"DIG": 0.020 / 2 + 0.003, "ANA": 0.013})
        self.assertFalse(missing["all_pass"])

    def test_auxiliary_bias_invalidates_original_high_impedance_proposal(self):
        new = models.auxiliary(self.parts)
        self.assertGreater(new["source_interval_v"][0], 2.49)
        self.assertLess(new["source_interval_v"][1], 2.70)
        self.assertGreater(new["maximum_cable_drop_before_receiver_minimum_v"], 0.033)
        self.assertGreater(new["maximum_positive_dynamic_excursion_before_characterized_ceiling_v"], 0.043)
        # Old proposed 113k/100k loses the supervisor margin from FB bias.
        old = models.divider_trip(113000, 100000, (1.193 * 0.98, 1.193 * 1.02), 100e-9)
        self.assertLess(old[0], 2.49)

    def test_aux_heat_encloses_actual_output_allocation_and_native_pullups(self):
        r = models.auxiliary_current(self.parts)
        self.assertGreater(r["known_resistive_subtotal_a"], 0.005)
        self.assertGreater(r["remaining_current_after_external_resistive_and_active_reserve_a"], 0)
        self.assertGreater(r["ldo_loss_allocation_w"], 0.95)
        self.assertFalse(r["complete_load_transients_and_hot_leakage_bound_verified"])
        changed = models.auxiliary_current(self.mutate_value("R110", "100"))
        self.assertGreater(changed["ldo_loss_allocation_w"], 0.95)
        self.assertLess(changed["remaining_current_after_external_resistive_and_active_reserve_a"], 0)

    def test_ready_open_drain_load_and_open_harness_require_both_resistor_choices(self):
        candidate = self.mutate_value("R316", "2.2k")
        new = models.ready_interface(candidate)
        self.assertGreater(new["high_remaining_offset_noise_and_uncertainty_budget_v"], 0.15)
        self.assertGreater(new["disconnected_low_margin_v"], 0.08)
        self.assertLess(new["maximum_asserted_source_sink_current_allocation_a"], 0.0025)
        # A stronger receiver pulldown cannot be imposed without checking the
        # actual source pullup. Even3.3k misses the Schmitt HIGH corner.
        old_source = models.ready_interface(self.mutate_value("R316", "3.3k"))
        self.assertLess(old_source["high_remaining_offset_noise_and_uncertainty_budget_v"], 0)
        open_fault = models.ready_interface(candidate, 47000)
        self.assertLess(open_fault["disconnected_low_margin_v"], 0)
        leak_fault = models.ready_interface(candidate, extra_output_sink_allocation_a=100e-6)
        self.assertLess(leak_fault["high_remaining_offset_noise_and_uncertainty_budget_v"], 0)
        self.assertFalse(new["physical_qualified"])

    def test_bipolar_controller_and_hot_capacity_are_not_invented(self):
        from hardware.electronics.power_distribution.p03 import bipolar

        state = bipolar.ledger(self.parts)
        self.assertLess(state["raw_local_current_ledger"]["RAW_N22"]["old_allocation_current_margin_a"], 0)
        self.assertFalse(state["full_system_startup_qualified"])
        self.assertEqual(state["controller_rejection"]["LM5067"]["manufacturer_maximum_rsense_ohm"], 0.1)
        for phase in state["staged_current_ceiling_scenarios"]:
            self.assertIsNone(phase["guaranteed_full_temperature_source_current_interval_a"])
            self.assertAlmostEqual(
                sum(phase["raw_output_power_by_converter_w"].values()), phase["raw_output_power_all_four_w"]
            )

    def test_buck_bulk_is_not_a_substitute_for_a_validated_ac_network(self):
        from hardware.electronics.power_distribution.p03.buck_control import screen

        parts = self.mutate_value("R203", "18.2k 1%")
        parts["R223"].find("value").text = "18.2k 1%"
        result = screen(parts, self.pins)
        self.assertEqual(result["DIG"]["programmed_internal_ramp_pf"], 4)
        self.assertGreater(result["DIG"]["local_fsw_over_flc_scenario_interval"][0], 40)
        self.assertFalse(result["DIG"]["local_allocated_minimum_meets_eq10_estimate"])
        self.assertFalse(result["DIG"]["downstream_bulk_treated_as_ideal_parallel_ac_capacitance"])
        self.assertFalse(result["DIG"]["phase_gain_margin_and_switching_jitter_qualified"])
        parts["R203"].find("value").text = "3.32k"
        self.assertEqual(screen(parts, self.pins)["DIG"]["programmed_internal_ramp_pf"], 1)
        parts["R203"].find("value").text = "10k"
        with self.assertRaises(ValueError):
            screen(parts, self.pins)

    def test_saved_buck_power_pairs_cannot_be_accepted_from_authoring_log(self):
        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.buck_layout import pair_inventory

        tree = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())
        result = pair_inventory(tree)
        self.assertTrue(result["eight_native_direct_pairs_present"])
        self.assertTrue(result["eight_native_hf_pairs_present"])
        victim = result["connections"][0]["matching_native_segment_uuids"][0]
        tree.remove(next(s for s in children(tree, "segment") if first(s, "uuid")[1] == victim))
        self.assertFalse(pair_inventory(tree)["eight_native_direct_pairs_present"])

    def test_internal_schmitt_gate_truth_loading_and_unproved_vcc_interval(self):
        from hardware.electronics.power_distribution.p03.internal_pg import evaluate

        r = evaluate(self.parts, self.pins)
        self.assertTrue(r["native_supported_schmitt_gate_and_pin_map"])
        self.assertTrue(r["truth_is_and"])
        self.assertGreater(r["buck_pg_low_margin_to_inferred0v58_v"], 0.07)
        self.assertGreater(r["buck_pg_loaded_high_margin_to_inferred1v87_v"], 0.5)
        self.assertFalse(r["continuous_aux_threshold_enclosure_manufacturer_verified"])
        self.assertFalse(r["physical_qualified"])
        pins = copy.deepcopy(self.pins)
        pins["U26"]["1"] = "V2V5_AUX"
        self.assertFalse(evaluate(self.parts, pins)["truth_is_and"])
        self.assertLess(
            evaluate(self.mutate_value("R246", "100k"), self.pins)[
                "buck_pg_loaded_high_margin_to_inferred1v87_v"
            ],
            0,
        )

    def test_negative_current_limit_droop_has_finite_headroom(self):
        from hardware.electronics.power_distribution.p03 import bipolar

        trial = self.mutate_value("R40", "181k")
        result = bipolar.negative_startup_droop(trial, 0.26473)
        self.assertGreater(result["remaining_raw_excursion_before_headroom_allocation_v"], 0)
        self.assertLess(result["remaining_raw_excursion_before_headroom_allocation_v"], 0.031)
        failed = bipolar.negative_startup_droop(trial, 0.270)
        self.assertLess(failed["remaining_raw_excursion_before_headroom_allocation_v"], 0)
        self.assertFalse(result["startup_qualified"])

    def test_old_stack_cannot_claim_c50_construction(self):
        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.construction import validate

        tree = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())
        validate(tree)
        layers = children(first(first(tree, "setup"), "stackup"), "layer")
        first(layers[0], "thickness")[1] = 0.070
        first(layers[1], "thickness")[1] = 0.115
        with self.assertRaisesRegex(AssertionError, "F.Cu"):
            validate(tree)

    def test_c50_array_counts_actual_native_vias_not_only_nominal_requirements(self):
        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.construction import direct_ep_inventory

        tree = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())
        current = direct_ep_inventory(tree)
        self.assertEqual(current["actual_count"], 12)
        self.assertTrue(current["implements_required_count_and_geometry"])
        xy = current["actual_vias"][0]["at_mm"]
        victim = next(
            v
            for v in children(tree, "via")
            if math.dist([float(a) - 100 for a in first(v, "at")[1:3]], xy) < 1e-7
        )
        tree.remove(victim)
        missing = direct_ep_inventory(tree)
        self.assertEqual(missing["actual_count"], 11)
        self.assertFalse(missing["implements_required_count_and_geometry"])

    def test_quiet_feedback_corridor_does_not_allow_switching_net_through_patch(self):
        import numpy as np

        from hardware.electronics.common.sexpr import read_sexpr
        from hardware.electronics.power_distribution.p03.route import PowerRouter, coded

        router = PowerRouter(coded(read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())))
        field = (router.xx > 101) & (router.xx < 116) & (router.yy > 2) & (router.yy < 14)
        quiet, _ = router.masks("LO_N_FB", 0.16)
        switching, _ = router.masks("LO_N_SW", 0.16)
        self.assertTrue(np.any(~quiet[2][field]))
        self.assertTrue(np.all(quiet[3][field]))
        self.assertTrue(np.all(quiet[5][field]))
        self.assertTrue(np.all(switching[2][field]))

    def test_native_binding_tracks_source_without_output_recursion(self):
        from hardware.electronics.power_distribution.p03.check import native_inputs

        sources = set(native_inputs())
        self.assertIn(ROOT / "power_p03.kicad_pcb", sources)
        self.assertIn(ROOT / "power_p03.kicad_sch", sources)
        self.assertIn(ROOT / "check.py", sources)
        self.assertNotIn(ROOT / "generated/verification.json", sources)
        self.assertNotIn(ROOT / "generated/analysis.json", sources)
        self.assertTrue(all(ROOT / "generated" not in p.parents for p in sources))

    def test_thermal_rebuild_preserves_quiet_corridor_but_removes_switching_transit(self):
        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.route import coded
        from hardware.electronics.power_distribution.p03.thermal import clear_u13_transit

        tree = coded(read_sexpr((ROOT / "power_p03.kicad_pcb").read_text()))
        codes = {str(n[2]).lstrip("/"): str(n[1]) for n in children(tree, "net")}
        quiet = [
            copy.deepcopy(obj)
            for obj in tree
            if isinstance(obj, list)
            and obj
            and obj[0] in {"via", "segment"}
            and str(first(obj, "net")[1]) in {codes["LO_N_FB"], codes["LO_REF_1V"]}
            and (obj[0] == "via" or first(obj, "layer")[1] == "In2.Cu")
        ]
        self.assertGreater(len(quiet), 2)
        illegal = read_sexpr(
            f'(segment (start 204 105) (end 212 105) (width .16) (layer "In2.Cu") '
            f"(net {codes['LO_N_SW']}) (uuid forbidden-switching-field))"
        )
        tree.append(illegal)
        self.assertGreater(clear_u13_transit(tree), 0)
        self.assertFalse(any(obj is illegal for obj in tree))
        self.assertTrue(all(obj in tree for obj in quiet))

    def test_guard_pg_release_is_below_real_operating_floor(self):
        new = models.source_valid(self.parts)
        self.assertTrue(new["pg_release_below_9v8"])
        old = models.source_valid(self.mutate_value("R105", "73.2k"))
        self.assertGreater(old["protected_input_pg_rising_v"][1], 10.2)
        self.assertGreaterEqual(new["minimum_presence_debounce_s"], 0.0568)
        self.assertLess(new["minimum_presence_debounce_s"], 0.057)
        self.assertTrue(new["one_nf_table_timeout_scaled_to_native_capacitance_is_unverified_allocation"])

    def test_partial_power_negative_monitor_uses_real_nodal_network(self):
        r = models.negative_monitor(self.parts)
        self.assertGreater(r["ref_unpowered_or_floating_input_interval_v"][0], -0.3)
        self.assertLess(r["maximum_reference_load_a"], 0.001)
        broken = models.negative_monitor(self.mutate_value("R315", "100k"))
        self.assertLess(broken["ref_unpowered_or_floating_input_interval_v"][0], -0.3)
        self.assertFalse(broken["off_inputs_respect_absolute_screen"])

    def test_negative_only_raw_reduction_preserves_dropout_and_positive_duty(self):
        r = models.raw_sources(self.parts)
        self.assertGreater(r["p12_control_headroom_v"], 2)
        self.assertGreater(r["n12_input_headroom_v"], 0.45)
        self.assertGreater(r["pairs"][1]["positive_minimum_duty_without_diode"], 0.15)
        old = models.raw_sources(self.mutate_value("R48", "54.9k"))
        self.assertGreater(
            old["pairs"][1]["negative_magnitude_envelope_v"][1],
            r["pairs"][1]["negative_magnitude_envelope_v"][1] + 3,
        )
        lower_positive = models.raw_sources(self.mutate_value("R44", "207k"))
        self.assertLess(lower_positive["pairs"][1]["positive_minimum_duty_without_diode"], 0.15)
        self.assertFalse(r["pairs"][1]["cuk_limit_hot_guaranteed"])

    def test_feed_quadratic_obeys_voltage_and_power_not_nominal_current(self):
        x = models.constant_power_feed(11.4, 0.36, 36.82, 0.09)
        self.assertAlmostEqual(x["protected_voltage_v"], 11.4 - 0.36 * x["current_a"])
        self.assertAlmostEqual((x["current_a"] - 0.09) * x["protected_voltage_v"], 36.82)
        self.assertGreater(x["current_a"], 36.82 / 11.4 + 0.09)
        with self.assertRaises(ValueError):
            models.constant_power_feed(5, 1, 7)

    def test_known_capacitance_is_not_complete_network(self):
        c = models.capacitors(self.parts, self.pins, "VIN_PROTECTED")
        self.assertGreater(c["maximum_known_direct_f"], 440e-6)
        self.assertFalse(c["complete_network_inventory_verified"])
        self.assertIsNone(c["complete_full_temperature_maximum_f"])
        self.assertIn("C103", c["positive_temperature_bound_missing_refs"])
        c104 = next(x for x in c["components"] if x["ref"] == "C104")
        self.assertAlmostEqual(c104["known_initial_and_dielectric_temperature_maximum_f"], 1e-6 * 1.2 * 1.15)
        changed = models.capacitors(self.mutate_value("C104", "1uF 50V X7S"), self.pins, "VIN_PROTECTED")
        self.assertGreater(
            changed["known_dielectric_temperature_adjusted_subtotal_f"],
            c["known_dielectric_temperature_adjusted_subtotal_f"],
        )
        # Digital startup calculation charges the whole scenario using ONE
        # master, not capacitance divided by the final parallel branch count.
        r = models.disconnect_startup()["DIG"]
        expected = 0.0071 * 9e-6 / (47e-9 * 0.95 * 0.997)
        self.assertTrue(math.isclose(r["maximum_capacitor_current_a"], expected))
        self.assertGreater(r["source_total_startup_current_a"], 3.8)
        self.assertFalse(r["startup_soa_measured"])

    def test_selected_bulk_dielectric_uses_its_actual_temperature_envelope(self):
        r = models.capacitors(self.parts, self.pins, "5V_DIG_SRC")
        cap = next(c for c in r["components"] if c["ref"] == "C206")
        self.assertIn("C3225X7S1E476M250AC", cap["value"])
        self.assertAlmostEqual(cap["known_initial_and_dielectric_temperature_maximum_f"], 47e-6 * 1.2 * 1.22)
        wrong = models.capacitors(self.mutate_value("C206", "47uF 25V X7R"), self.pins, "5V_DIG_SRC")
        self.assertLess(
            wrong["known_dielectric_temperature_adjusted_subtotal_f"],
            r["known_dielectric_temperature_adjusted_subtotal_f"],
        )
        self.assertIsNone(r["complete_full_temperature_maximum_f"])

    def test_cuk_ground_cathodes_cannot_be_replaced_by_an_ideal_ep_return(self):
        from hardware.electronics.power_distribution.p03.dc_ports import port_contract

        r = port_contract(self.parts, self.pins)
        self.assertFalse(r["whole_network_kcl_and_voltage_transfer_qualified"])
        for ref in ("D2", "D4"):
            pins = copy.deepcopy(self.pins)
            pins[ref]["1"] = "RAW_N17"
            with self.assertRaises(AssertionError):
                port_contract(self.parts, pins)

    def test_copper_coalescing_preserves_gaps_nets_layers_and_widths(self):
        from hardware.electronics.common.sexpr import children, read_sexpr
        from hardware.electronics.power_distribution.p03.coalesce import merge

        tree = read_sexpr(
            '(kicad_pcb(segment(start 0 0)(end 1 0)(width .16)(layer "F.Cu")(net 1))(segment(start 1 0)(end 2 0)(width .16)(layer "F.Cu")(net 1))(segment(start 2.001 0)(end 3 0)(width .16)(layer "F.Cu")(net 1))(segment(start 0 0)(end 2 0)(width .25)(layer "F.Cu")(net 1))(segment(start 0 0)(end 2 0)(width .16)(layer "B.Cu")(net 1))(segment(start 0 0)(end 2 0)(width .16)(layer "F.Cu")(net 2)))'
        )
        report = merge(tree)
        self.assertEqual(report["original_segments_removed"], 2)
        self.assertEqual(report["exact_union_segments_added"], 1)
        self.assertEqual(len(children(tree, "segment")), 5)
        self.assertEqual(merge(tree)["original_segments_removed"], 0)

    def test_dangling_staircase_cleanup_preserves_real_copper_junction(self):
        from hardware.electronics.common.sexpr import read_sexpr
        from hardware.electronics.power_distribution.p03.route import dangling_chains

        text = '(kicad_pcb(segment(start 0 0)(end .125 0)(width .25)(layer "F.Cu")(net 1)(uuid a))(segment(start .125 0)(end .125 .125)(width .25)(layer "F.Cu")(net 1)(uuid b))(segment(start .125 .125)(end .25 .125)(width .25)(layer "F.Cu")(net 1)(uuid c)))'
        self.assertEqual(dangling_chains(read_sexpr(text), {"a"}), {"a", "b", "c"})
        crossing = (
            text[:-1] + '(segment(start .125 -2)(end .125 2)(width .25)(layer "F.Cu")(net 1)(uuid branch)))'
        )
        self.assertEqual(dangling_chains(read_sexpr(crossing), {"a"}), {"a"})

    def test_tall_through_hole_part_cannot_migrate_below_board(self):
        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.assembly import constraints

        tree = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())
        self.assertTrue(constraints(tree)["front_only_through_hole_rule_checked"])
        film = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "C33"] for p in children(fp, "property"))
        )
        first(film, "layer")[1] = "B.Cu"
        with self.assertRaisesRegex(AssertionError, "C33"):
            constraints(tree)

    def test_selected_input_chain_keeps_plug_and_protected_boundaries_separate(self):
        r = models.complete_input_chain(self.parts, 28.28, 36.85)
        self.assertAlmostEqual(r["static_plug_terminal_interval_v"][0], 11.43)
        self.assertFalse(r["adapter_captive_cable_counted_again"])
        startup = r["conditional_operating_points"]["digital_master_charge_full_load"]
        self.assertGreater(startup["dc_in_before_guard_voltage_v"], startup["protected_voltage_v"])
        self.assertGreater(startup["protected_9v8_floor_margin_v"], 0)
        self.assertFalse(r["remainder_is_established_upper_bound"])
        self.assertFalse(r["complete_feed_and_dynamic_startup_qualified"])
        with self.assertRaises(ValueError):
            models.complete_input_chain(self.parts, 200, 250)

    def test_native_serialization_preserves_pad_and_routed_copper_nets(self):
        from hardware.electronics.common.sexpr import read_sexpr
        from hardware.electronics.power_distribution.p03.route import coded, electrical_identity, named

        tree = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())
        before = electrical_identity(copy.deepcopy(tree))
        after = electrical_identity(named(coded(copy.deepcopy(tree))))
        self.assertEqual(before, after)
        self.assertGreater(len(before[0]), 500)
        self.assertGreater(len(before[1]), 100)

    def test_monitor_vip_requires_declared_bore_land_and_node(self):
        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.construction import monitor_vip_inventory

        tree = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())
        inventory = monitor_vip_inventory(tree)
        self.assertTrue(inventory["implements_required_geometry"])
        centre = inventory["actual_vias"][0]["at_mm"]
        for tag, bad in (("size", 0.60), ("drill", 0.25)):
            mutated = copy.deepcopy(tree)
            via = next(
                v
                for v in children(mutated, "via")
                if all(abs(float(q) - p - 100) < 1e-6 for q, p in zip(first(v, "at")[1:3], centre))
            )
            first(via, tag)[1] = str(bad)
            self.assertFalse(monitor_vip_inventory(mutated)["implements_required_geometry"])
        self.assertFalse(inventory["drill_etch_and_registration_tolerances_approved"])

    def test_reserved_return_layer_only_reuses_actual_clear_signal_copper(self):
        from hardware.electronics.common.sexpr import read_sexpr
        from hardware.electronics.power_distribution.p03.route import STEP, PowerRouter

        text = '(kicad_pcb (net 0 "") (net 1 "/SENSE") (net 2 "/FOREIGN") (segment (start 230 120) (end 232 120) (width .25) (layer "In4.Cu") (net 1)))'
        r = PowerRouter(read_sexpr(text))
        blocked, _ = r.masks("SENSE", 0.16)
        ix, iy = round(131 / STEP), round(20 / STEP)
        self.assertFalse(blocked[4, ix, iy])
        self.assertTrue(blocked[4, ix, round(21 / STEP)])
        self.assertTrue(blocked[1, ix, iy])
        foreign = '(segment (start 231 119) (end 231 121) (width .25) (layer "In4.Cu") (net 2))'
        tree = read_sexpr(text)
        tree.append(read_sexpr(foreign))
        blocked, _ = PowerRouter(tree).masks("SENSE", 0.16)
        self.assertTrue(blocked[4, ix, iy], "Retained-net reuse must not erase a real foreign obstacle")

    def test_passive_returns_preserve_sign_bias_and_actual_native_boundary(self):
        from hardware.electronics.power_distribution.p03.passive_returns import divider_current, packet

        data = packet(self.parts, self.pins)
        rows = {r["ref"]: r for r in data["actual_passive_electrodes"]}
        self.assertLess(rows["R38"]["conditional_signed_current_a"][1], 0)
        self.assertGreater(rows["R29"]["conditional_signed_current_a"][0], 0)
        self.assertEqual(rows["R243"]["source_net"], "P03_ANA_SET")
        current = divider_current([12, 12], 10000, 10000, 0, 10e-6)
        self.assertAlmostEqual(current[0], 0.000595)
        self.assertAlmostEqual(current[1], 0.000605)
        pins = copy.deepcopy(self.pins)
        pins["R38"]["1"] = "P19_SRC"
        with self.assertRaises(AssertionError):
            packet(self.parts, pins)
        pins = copy.deepcopy(self.pins)
        pins["R206"]["1"] = "AGND"
        with self.assertRaises(AssertionError):
            packet(self.parts, pins)

    def test_isolated_u102_requires_actual_native_source_and_no_physical_promotion(self):
        import json

        from hardware.electronics.power_distribution.p03.u102_checkpoint import validate

        root = ROOT / "candidates/u102-on-42add"
        report = json.loads((root / "generated/current-native.json").read_text())
        self.assertEqual(validate(root), dict(ERC=0, DRC=0, parity=0, opens=0))
        for field, bad in (("pcb_sha256", "0" * 64), ("physical_qualified", True)):
            mutated = copy.deepcopy(report)
            mutated[field] = bad
            with self.assertRaises(AssertionError):
                validate(root, mutated)
        mutated = copy.deepcopy(report)
        mutated["native_counts"]["opens"] = 1
        with self.assertRaises(AssertionError):
            validate(root, mutated)
        mutated = copy.deepcopy(report)
        mutated["native_counts"]["opens"] = False
        with self.assertRaises(AssertionError):
            validate(root, mutated)
        mutated = copy.deepcopy(report)
        raw = next(p for p in mutated["artifact_sha256"] if p.endswith("complete-scratch-drc.json"))
        del mutated["artifact_sha256"][raw]
        with self.assertRaises(AssertionError):
            validate(root, mutated)

    def test_restored_u10_native_proof_binds_actual_front_pose_and_live_EP_array(self):
        from hardware.electronics.power_distribution.p03.u102_checkpoint import validate_u10

        for candidate in ("u10-eight-ep-on-42add", "u10-B-transits-on-f94c"):
            with self.subTest(candidate=candidate):
                self.assertEqual(
                    validate_u10(ROOT / "candidates" / candidate),
                    dict(ERC=0, DRC=0, parity=0, opens=0),
                )

    def test_composition_rejects_conflicting_uuid_edits_and_drops_inherited_fill(self):
        import copy

        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03.composition import merge

        base = read_sexpr('''(kicad_pcb
          (segment (uuid "shared") (width .16))
          (zone (uuid "plane") (net_name "AGND")
            (polygon (pts (xy 0 0) (xy 1 0) (xy 1 1)))
            (filled_polygon (layer "F.Cu") (pts (xy 0 0)))))''')
        left, right = copy.deepcopy(base), copy.deepcopy(base)
        first(first(left, "segment"), "width")[1] = ".20"
        first(first(right, "segment"), "width")[1] = ".25"
        with self.assertRaisesRegex(AssertionError, "Conflicting shared-source"):
            merge(base, left, right)
        merged, report = merge(base, left, base)
        self.assertEqual(float(first(first(merged, "segment"), "width")[1]), 0.20)
        self.assertFalse(children(first(merged, "zone"), "filled_polygon"))
        self.assertTrue(report["native_refill_erc_drc_parity_and_connectivity_required"])
        self.assertFalse(report["inherited_thermal_result_accepted"])
        self.assertFalse(report["physical_qualified"])

    def test_combined_native_composition_preserves_both_real_repair_contracts(self):
        from hardware.electronics.power_distribution.p03.combined_checkpoint import validate

        result = validate(ROOT / "candidates/aux-u10-combined")
        self.assertEqual(result["native_counts"], dict(ERC=0, DRC=0, parity=0, opens=0))
        self.assertEqual(len(result["direct_aux_loops"]["actual_direct_front_paths"]), 6)
        self.assertEqual(result["u102_actual_domain_agnd_through_via_count"], 17)
        self.assertEqual(result["u102_named_adjacent_field_barrel_count"], 2)
        self.assertFalse(result["stability_startup_and_physical_qualified"])

    def test_aux_local_cell_rejects_wrong_face_and_similar_but_wrong_input_rail(self):
        from unittest.mock import patch

        from hardware.electronics.common.sexpr import children, first, read_sexpr
        from hardware.electronics.power_distribution.p03 import aux_loop_check
        from hardware.electronics.power_distribution.p03.u102_checkpoint import validate as native

        root = ROOT / "candidates/aux-front-cell"
        self.assertEqual(native(root), dict(ERC=0, DRC=0, parity=0, opens=0))
        result = aux_loop_check.validate(root)
        self.assertIsNone(result["actual_bias_temp_aging_effective_capacitance_lower_bound_f"])
        self.assertFalse(result["independent_stability_and_loadstep_qualified"])
        tree = read_sexpr((root / "power_p03.kicad_pcb").read_text())
        for change in ("opposite_face", "wrong_input_net", "narrowed_local_input"):
            mutated = copy.deepcopy(tree)
            ref = "C106" if change == "opposite_face" else "C113"
            fp = next(
                f
                for f in children(mutated, "footprint")
                if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
            )
            if change == "opposite_face":
                first(fp, "layer")[1] = "B.Cu"
            elif change == "wrong_input_net":
                pin = next(p for p in children(fp, "pad") if str(p[1]) == "1")
                first(pin, "net")[-1] = "/VIN_PROTECTED"
            else:
                for line in children(mutated, "segment"):
                    if first(line, "layer")[1] == "F.Cu" and str(first(line, "net")[-1]) == "/VIN_IC":
                        first(line, "width")[1] = "0.16"
            with (
                self.subTest(change=change),
                patch.object(aux_loop_check, "read_sexpr", return_value=mutated),
            ):
                with self.assertRaises(AssertionError):
                    aux_loop_check.validate(root)

    def test_direct_copper_coverage_rejects_gap_and_narrowing(self):
        from hardware.electronics.power_distribution.p03.aux_loop_check import covered

        lines = [dict(start=(-2, 0), end=(1, 0), width=0.25), dict(start=(1, 0), end=(4, 0), width=0.25)]
        self.assertTrue(covered((0, 0), (2, 0), lines, 0.25))
        lines[1]["start"] = (1.01, 0)
        self.assertFalse(covered((0, 0), (2, 0), lines, 0.25))
        lines[1]["start"] = (1, 0)
        lines[1]["width"] = 0.16
        self.assertFalse(covered((0, 0), (2, 0), lines, 0.25))

    def test_analysis_does_not_promote_conditional_models_to_release(self):
        r = analysis.analyze()
        self.assertEqual(r["physical_tests_performed"], 0)
        for flag in (
            "board_routing_complete",
            "thermal_qualified",
            "startup_qualified",
            "source_to_load_physically_qualified",
            "fabrication_released",
            "build_ready",
        ):
            self.assertIs(r[flag], False)


if __name__ == "__main__":
    unittest.main()
