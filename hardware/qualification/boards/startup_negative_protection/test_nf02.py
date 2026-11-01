"""Source-integrity and adverse-corner tests of the NF02 pre-native study."""

import copy
import json
import math
import unittest
from unittest.mock import patch

from . import analyze as model
from .capture import REPO, ROOT, sha


class NF02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = json.loads((ROOT / "parameters.json").read_text())
        cls.report = model.analyze(cls.params)

    def mutated(self, fn):
        p = copy.deepcopy(self.params)
        fn(p)
        return model.analyze(p)

    def test_actual_native_caps_polarity_and_known_test_comparison(self):
        for name, cap, nominal, subtotal in [
            ("N19", "C8", 0.0015, 0.00225),
            ("N12", "C16", 0.00022, 0.00033),
        ]:
            r = self.report["rails"][name]
            self.assertEqual(r["actual_bulk_ref"], cap)
            self.assertAlmostEqual(r["actual_bulk_nominal_f"], nominal)
            self.assertAlmostEqual(r["local_endurance_restored20c_comparison_f"], subtotal)
            self.assertFalse(r["post_endurance_comparison_is_full_temperature_or_lifetime_bound"])
        original = model.native

        def wrong_polarity(path):
            parts, pins, members = original(path)
            if path.name.startswith("e28"):
                pins["C8"] = {"1": "N19", "2": "AGND"}
            return parts, pins, members

        with patch.object(model, "native", wrong_polarity), self.assertRaises(AssertionError):
            model.analyze(self.params)

    def test_initial_tolerance_only_cap_allocation_rejected(self):
        q = self.mutated(
            lambda p: p["rails"]["N19"].update(new_full_network_capacitance_receiving_requirement_f=0.0018)
        )
        self.assertFalse(q["closed_algebraic_receiving_region"])
        self.assertFalse(q["rails"]["N19"]["capacitance_allocation_has20pct_over_known_post_test_comparison"])

    def test_missing_bulk_ref_or_misidentified_digital_bulk_rejected(self):
        with self.assertRaises(AssertionError):
            self.mutated(lambda p: p["rails"]["N19"].update(cap_ref="C24"))

    def test_early_watchdog_rejects_normal_start_region(self):
        q = self.mutated(lambda p: p["rails"]["N19"].update(watchdog_cwd_nominal_f=10e-9))
        self.assertFalse(q["rails"]["N19"]["watchdog_minimum_has20pct_over_diagnostic"])
        self.assertFalse(q["closed_algebraic_receiving_region"])

    def test_filter_rc_and_cf_are_independently_checked(self):
        q = self.mutated(lambda p: p["rails"]["N12"].update(ramp_filter_rf_ohm=100))
        self.assertFalse(q["closed_algebraic_receiving_region"])
        q = self.mutated(lambda p: p["rails"]["N12"].update(ramp_filter_cf_nominal_f=1e-6))
        self.assertFalse(q["closed_algebraic_receiving_region"])

    def test_extra_filter_charge_is_not_omitted(self):
        for r in self.report["rails"].values():
            self.assertGreater(r["additional_ramp_filter_charge_diagnostic_s"], 0.3)
            self.assertGreater(r["complete_stage_diagnostic_s"], r["output_ramp_only_diagnostic_s"] + 0.5)

    def test_bias_cannot_be_free_or_starved(self):
        q = self.mutated(lambda p: p["rails"]["N12"].update(bias_series_resistors_ohm=[1000, 1000]))
        self.assertFalse(q["closed_algebraic_receiving_region"])
        for r in self.report["rails"].values():
            calculated = (
                r["p03_internal_raw_current_excluding_new_controller_a"]
                + r["protected_peak_diagnostic_a"]
                + r["bias"]["normal_feed_current_interval_a"][1]
                + r["new_vee_bleed_source_current_a"]
                + r["new_monitor_source_current_requirement_a"]
            )
            self.assertAlmostEqual(r["total_raw_current_diagnostic_a"], calculated)
        self.assertGreater(
            self.report["new_bias_power"]["guarded_positive_direct_current_upper_requirement_a"], 0.04
        )

    def test_collapse_timing_capacitance_and_leakage_are_real_conditions(self):
        for fn in [
            lambda p: p.update(bias_switch_full_path_disable_receiving_requirement_s=50e-6),
            lambda p: p.update(after_bank_to_agnd_effective_cap_minimum_requirement_f=1e-6),
            lambda p: p.update(bias_switch_complete_off_leakage_receiving_requirement_a=20e-6),
        ]:
            q = self.mutated(fn)
            self.assertFalse(q["partial_power"]["has20pct_margin_to0p3v_pin_floor"])
            self.assertFalse(q["closed_algebraic_receiving_region"])

    def test_large_shunt_breaks_retained_source_to_load_budget(self):
        q = self.mutated(lambda p: p["rails"]["N12"].update(fault_shunt_nominal_ohm=0.287))
        self.assertFalse(q["rails"]["N12"]["stage_dc_drop_has20pct_headroom"])
        self.assertFalse(q["closed_algebraic_receiving_region"])

    def test_watchdog_actual_cap_formula(self):
        lo, hi = model.watchdog(56e-9, 0.10)
        self.assertAlmostEqual(lo, 0.905 * (77.4 * 50.4 + 55) / 1000)
        self.assertAlmostEqual(hi, 1.095 * (77.4 * 61.6 + 55) / 1000)

    def test_invalid_or_unsupported_inputs_rejected(self):
        for bad in [math.nan, math.inf, -1, 0]:
            with self.assertRaises(ValueError):
                self.mutated(lambda p: p.update(after_bank_to_agnd_effective_cap_minimum_requirement_f=bad))
        for key in [
            "native_sources_must_remain_on_while_negative_stages_ramp",
            "protected_full_live_load_present_from_zero",
            "one_bipolar_stage_at_a_time_after_positive_5v_charge",
        ]:
            with self.assertRaises(AssertionError):
                self.mutated(lambda p: p.update({key: False}))
        with self.assertRaises(AssertionError):
            self.mutated(lambda p: p.update(full_trajectory_ramp_current_manufacturer_guaranteed=True))

    def test_simplified_normal_region_is_not_a_fault_guarantee(self):
        self.assertTrue(self.report["closed_algebraic_receiving_region"])
        for r in self.report["rails"].values():
            self.assertGreater(r["currentlimit_fault_cold_switch_peak_diagnostic_a"], 0.9)
            self.assertIsNone(r["guaranteed_fault_energy_j"])
            self.assertIsNone(r["guaranteed_complete_stage_s"])
            self.assertFalse(r["full_trajectory_current_guaranteed"])
            self.assertFalse(r["continuous_fault_source_regulation_guaranteed"])
        for k in [
            "startup_qualified",
            "soa_qualified",
            "reverse_current_qualified",
            "physical_qualified",
            "fabrication_released",
            "build_ready",
        ]:
            self.assertIs(self.report[k], False)

    def test_inlet_power_recomposition_and_kcl(self):
        q = self.report["complete_inlet_steady_diagnostic"]
        expected = (
            q["base_protected_input_power_w"]
            - q["removed_old_independent_raw_input_power_w"]
            + q["new_actual_ledger_all_four_raw_output_power_w"] / 0.75
            + 5.1 * 0.006 / 0.85
        )
        self.assertAlmostEqual(q["recomposed_protected_input_power_w"], expected)
        for row in [q] + self.report["single_negative_phase_input_diagnostics"]:
            self.assertAlmostEqual(row["protected_voltage_v"], 11.4 - 0.36 * row["current_a"])
        self.assertFalse(q["old_negative_controller_reserve_double_counted"])

    def test_iso_polarity_and_watchdog_fault_latch_contract(self):
        a = json.loads((ROOT / "architecture.json").read_text())
        controls = a["controller_standalone_controls"]
        self.assertIn("HIGH starts, LOW stops", controls["ON"])
        self.assertIn("NEVER", controls["EN"])
        self.assertIn("single accepted WDI falling edge", a["independent_protection"]["watchdog_arming"])
        self.assertIn("no periodic autoretry", a["independent_protection"]["fault_latch"])
        self.assertFalse(a["independent_protection"]["hardware_logic_implemented"])

    def test_original_sources_and_copied_primary_bytes_are_fresh(self):
        c = json.loads((ROOT / "sources/capture.json").read_text())
        for n, h in c["original_source_sha256"].items():
            self.assertEqual(sha(REPO / n), h, n)
        for n, h in c["copied_source_sha256"].items():
            self.assertEqual(sha(ROOT / n), h, n)
        sources = json.loads((ROOT / "sources/primary-sources.json").read_text())
        for n, r in sources.items():
            if r["sha256"] is not None:
                self.assertEqual(sha(ROOT / "sources/primary" / n), r["sha256"], n)
            else:
                self.assertIsNone(r["bytes"])
                self.assertFalse(r["visual_original_review_complete"])
        for n, h in self.report["source_sha256"].items():
            self.assertEqual(sha(REPO / n), h, n)


if __name__ == "__main__":
    unittest.main()
