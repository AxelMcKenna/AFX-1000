"""P01 rejects missing losses, unsafe substitutions and false release claims."""

import copy
import math
import unittest

from hardware.electronics.power_distribution.analyze import analyze, source_corners, validate_circuit
from hardware.electronics.power_distribution.spec import candidate, circuit


class PowerDistributionTests(unittest.TestCase):
    def test_new_sources_only_conditionally_meet_unchanged_star_targets(self):
        result = analyze()
        self.assertTrue(result["allocated_voltage_envelopes_pass"])
        for name, target in (("V5_REG", [4.975, 5.025]), ("5V_DIG", [4.9, 5.1])):
            row = result["rails"][name]
            self.assertEqual(row["target_v"], target)
            self.assertGreaterEqual(row["candidate_at_e25_protected_star_v"][0], target[0])
            self.assertLessEqual(row["candidate_at_e25_protected_star_v"][1], target[1])
            self.assertLess(row["baseline_with_same_complete_path_v"][0], target[0])
            self.assertFalse(row["implemented_on_current_psu"])
            self.assertFalse(row["hardware_voltage_verified"])

    def test_full_temperature_digital_corners_include_divider_and_leakage(self):
        row = source_corners(candidate())["5V_DIG"]
        self.assertEqual(row["corners"], 16)
        self.assertAlmostEqual(row["dc_v"][0], 4.96493913100031, places=12)
        self.assertAlmostEqual(row["dc_v"][1], 5.075039727796486, places=12)
        bad = candidate()
        bad["digital_feedback"]["full_temperature_reference_fraction"] = 0.006
        with self.assertRaises(AssertionError):
            source_corners(bad)

    def test_analog_return_and_cross_domain_ground_are_not_single_load_returns(self):
        result = analyze()
        a = result["rails"]["V5_REG"]["path"]
        self.assertAlmostEqual(a["shared_analog_return_magnitude_bound_a"], 0.605)
        self.assertAlmostEqual(a["own_return_current_bound_a"], 0.605)
        self.assertAlmostEqual(a["common_ground_transfer_current_bound_a"], 2.406)
        self.assertAlmostEqual(a["common_ground_transfer_error_v"], 0.002406)
        self.assertGreater(a["return_drop_or_rise_bound_v"], 0.004)
        self.assertGreater(a["maximum_high_side_ground_rise_v"], 0.006)

    def test_extra_load_harness_contacts_can_exhaust_digital_margin(self):
        config = candidate()
        config["rails"]["5V_DIG"]["distribution"]["mated_contacts_per_conductor"] = 4
        result = analyze(config)
        self.assertFalse(result["rails"]["5V_DIG"]["allocated_voltage_envelope_passes"])
        self.assertLess(result["rails"]["5V_DIG"]["low_side_margin_v"], 0)
        self.assertFalse(result["outgoing_load_harness_voltage_budget_closed"])

    def test_typical_connector_resistance_is_not_silently_free(self):
        config = candidate()
        for row in config["rails"].values():
            row["distribution"]["contact_resistance_hot_end_of_life_max_ohm"] = 0.010
        result = analyze(config)
        self.assertFalse(result["allocated_voltage_envelopes_pass"])
        self.assertFalse(result["build_ready"])

    def test_missing_or_nonfinite_return_requirements_are_rejected(self):
        for value in (None, math.inf, math.nan, -0.001):
            config = candidate()
            config["rails"]["V5_REG"]["distribution"]["return_length_m"] = value
            with self.subTest(value=value), self.assertRaises(AssertionError):
                analyze(config)
        config = candidate()
        del config["rails"]["V5_REG"]["distribution"]["return_length_m"]
        with self.assertRaises(KeyError):
            analyze(config)

    def test_ground_pad_and_local_feedback_contracts_reject_unsafe_substitutions(self):
        for device, pin, net in [
            ("U9_NEW", "11", "V5_REG_SRC"),
            ("U9_NEW", "9", "V5_REG"),
            ("U2_NEW", "3", "5V_DIG"),
            ("U14_NEW", "2", "5V_DIG_SRC"),
        ]:
            changed = copy.deepcopy(circuit())
            changed["devices"][device]["pins"][pin] = net
            with self.subTest(device=device, pin=pin), self.assertRaises(AssertionError):
                validate_circuit(changed)
        changed = circuit()
        changed["feedback_crosses_disconnect"] = True
        with self.assertRaises(AssertionError):
            validate_circuit(changed)

    def test_set_current_and_fault_clamp_are_independent_of_dc_accuracy(self):
        normal = analyze()["analog_input_and_set_screen"]
        self.assertEqual(normal["set_current_sink_requirement_a"], 102e-6)
        self.assertTrue(normal["set_clamp_current_screen_passes"])
        self.assertGreater(normal["set_buffer_minimum_drive_v"], 4)
        config = candidate()
        config["analog_reference"]["set_isolation_ohm"] = 100
        self.assertFalse(analyze(config)["analog_input_and_set_screen"]["set_clamp_current_screen_passes"])

    def test_unknown_stability_aging_and_physical_results_never_become_release(self):
        result = analyze()
        self.assertTrue(result["allocated_voltage_envelopes_pass"])
        digital = result["digital_startup_and_thermal_screen"]
        self.assertTrue(digital["direct_local_capacitance_in_datasheet_range"])
        self.assertTrue(digital["connected_bulk_exceeds_direct_capacitance_limit"])
        self.assertFalse(digital["capacitance_series_damping_and_closed_loop_stability_verified"])
        self.assertFalse(digital["late_disconnect_closure_inrush_limited"])
        self.assertFalse(
            result["analog_input_and_set_screen"]["reference_aging_hysteresis_humidity_bound_guaranteed"]
        )
        self.assertFalse(result["sd_card_3v3_current_inrush_and_partial_power_budget_closed"])
        for flag in (
            "native_schematic_implemented",
            "native_pcb_routed",
            "physical_fit_verified",
            "physical_power_verified",
            "design_qualified",
            "fabrication_released",
            "build_ready",
        ):
            self.assertFalse(result[flag], flag)


if __name__ == "__main__":
    unittest.main()
