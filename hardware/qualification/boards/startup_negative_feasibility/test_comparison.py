"""Portable physical-equation crosschecks and false-guarantee mutations."""

import copy
import json
import math
import unittest

from .compare import REPO, ROOT, charge, ltc_timer, native_ss_comparison, sha, shunt_window
from .seal import claim_errors


class NegativeFeasibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ROOT / "comparison.json").read_text())

    def test_n12_fixed_shunt_has_no_overlap_even_perfect_and_n19_does(self):
        n12 = self.r["rails"]["N12"]
        for key in [
            "ltc_fixed_shunt_window",
            "ltc_fixed_shunt_window_zero_tolerance",
            "ltc_app_text_66mv_window",
            "ltc_app_text_66mv_window_zero_tolerance",
        ]:
            self.assertFalse(n12[key]["nonempty"], key)
        self.assertTrue(self.r["rails"]["N19"]["ltc_fixed_shunt_window"]["nonempty"])
        w = n12["ltc_fixed_shunt_window"]
        self.assertGreater(w["minimum_acl_ceiling_before_controller_overhead_a"], 0.277)
        self.assertTrue(shunt_window(n12["constant_load_screen_a"], 0.300)["nonempty"])

    def test_full_constant_load_and_energy_are_not_omitted(self):
        c = charge(20, 0.002, 0.050, 0.100)
        self.assertAlmostEqual(c["charge_time_s"], 0.8)
        self.assertAlmostEqual(c["capacitor_energy_j"], 0.4)
        self.assertAlmostEqual(c["mosfet_pass_energy_j"], 0.8)
        self.assertAlmostEqual(
            c["constant_load_pass_energy_j"] + c["capacitor_energy_j"], c["mosfet_pass_energy_j"]
        )
        self.assertFalse(charge(20, 0.002, 0.100, 0.100)["can_charge"])
        self.assertFalse(charge(20, 0.002, 0.101, 0.100)["can_charge"])

    def test_typical_timer_integral_independent_midpoint_sum(self):
        v, time, rd = 19.1, 0.63, 1e6
        t = ltc_timer(v, time, rd)
        count = 20000
        q = math.fsum(
            (230e-6 + 8 * max(v * (1 - (i + 0.5) / count) - 6, 0) / rd) * time / count for i in range(count)
        )
        self.assertAlmostEqual(t["exact_linear_scenario_min_ct_f"], q / 4, places=12)
        self.assertGreater(t["exact_linear_scenario_initial_delay_s"], 28)
        self.assertIsNone(t["guaranteed_fault_window_s"])
        self.assertIsNone(t["guaranteed_initial_delay_s"])

    def test_native_ss_cap_charge_independent_numerical_integration(self):
        for rail, row in self.r["rails"].items():
            ss = row["ltc_native_ss_180mohm_comparison"]
            tau = ss["typical_tau_required_s"]
            total = ss["typical_output_complete_s"]
            load = row["constant_load_screen_a"]
            count = 30000

            def current(t):
                return max(0, (0.05 * 1.4 * (1 - math.exp(-t / tau)) - 0.010) / 0.180)

            integrated = math.fsum(
                max(current((i + 0.5) * total / count) - load, 0) * total / count for i in range(count)
            )
            need = row["local_bulk_plus_initial20pct_f"] * row["voltage_max_from_frozen_ledger_v"]
            self.assertAlmostEqual(integrated, need, places=9, msg=rail)
            self.assertAlmostEqual(current(total), row["provisional_normal_start_ceiling_a"])
            # Omitting the live load would materially overestimate charge.
            wrong = math.fsum(current((i + 0.5) * total / count) * total / count for i in range(count))
            self.assertGreater(wrong, need * 1.4)
            self.assertLess(ss["typical_total_with_330nf_initial_s"], 1.1)

    def test_pre_cb_short_energy_and_fault_current_budget_remain(self):
        n19 = self.r["rails"]["N19"]["ltc_native_ss_180mohm_comparison"]
        self.assertGreater(n19["typical_pass_energy_into_short_before_cb_j"], 6)
        self.assertGreater(n19["typical_cb_activation_into_short_s"], 1.9)
        faults = self.r["ltc_180mohm_fault_screen"]
        self.assertGreater(faults["minimum_cb_a"], 0.240)
        self.assertGreater(faults["maximum_acl_a"], 0.439)
        self.assertGreater(faults["maximum_fcl_threshold_a"], 1.73)
        self.assertIsNone(faults["controller_actual_peak_current_a"])

    def test_manufacturer_range_and_shunt_rules_not_waived(self):
        self.assertFalse(self.r["lt4250"]["n12_local_supply_supported"])
        self.assertEqual(self.r["lt4250"]["local_supply_min_v"], 18)
        lm = self.r["lm5067_fixed_limit_dead_end"]
        self.assertEqual(lm["manufacturer_rs_max_ohm"], 0.1)
        self.assertGreater(lm["rs_min_for_150ma_max_limit_ohm"], 0.1)
        self.assertGreater(lm["rs_min_for_220ma_max_limit_ohm"], 0.1)
        h = self.r["ltc_n12_headroom_screen"]
        self.assertGreater(h["supply_after_feed_11p9_v"], h["comparator_vlko_max_v"])
        self.assertLess(h["if_low_zener_at24p4_step_a"], 0.030)
        self.assertIsNone(h["low_voltage_gate_drive_guarantee_v"])

    def test_invalid_inputs_and_premature_guarantees_rejected(self):
        self.assertEqual(claim_errors(self.r), [])
        for func, args in [
            (charge, [20, 0.002, 0.05, float("nan")]),
            (ltc_timer, [20, -1]),
            (shunt_window, [0.1, 0.2, 0.045, 0.0759, 1]),
            (native_ss_comparison, [20, 0.002, 0.1, 0.4]),
        ]:
            with self.assertRaises(ValueError):
                func(*args)
        for key in [
            "startup_qualified",
            "new_schematic_authored",
            "viable_with_all_current_contracts_verified",
        ]:
            r = copy.deepcopy(self.r)
            r[key] = True
            self.assertTrue(claim_errors(r))
        r = copy.deepcopy(self.r)
        r["rails"]["N19"]["ltc_fixed_shunt_candidate"]["timer"]["guaranteed_fault_window_s"] = [0.01, 0.1]
        self.assertTrue(claim_errors(r))
        r = copy.deepcopy(self.r)
        r["rails"]["N12"]["ltc_native_ss_180mohm_comparison"]["selected_css_f"] = 3.9e-6
        self.assertTrue(claim_errors(r))

    def test_sealed_inputs_and_comparison_are_intact(self):
        seal = json.loads((ROOT / "seal.json").read_text())
        self.assertTrue(seal["comparison_integrity_accepted"])
        self.assertFalse(seal["feasibility_qualified"])
        for path, expected in seal["sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)
        for path, expected in self.r["source_sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)


if __name__ == "__main__":
    unittest.main()
