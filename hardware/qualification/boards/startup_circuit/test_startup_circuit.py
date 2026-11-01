"""Portable topology/corner/hold mutations; no native tools or downloads in CI."""

import copy
import json
import math
import unittest

from hardware.electronics.common.netlists import netlist

from .analyze import OUT, ramp, sha, shunt_corners, timer_corners
from .design import REPO
from .verify import contract_errors


class StartupCircuit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.pins = netlist(OUT / "netlist.xml")
        cls.analysis = json.loads((OUT / "analysis.json").read_text())
        cls.receipt = json.loads((OUT / "verification.json").read_text())

    def test_actual_export_satisfies_independent_manufacturer_contract(self):
        self.assertEqual(contract_errors(self.parts, self.pins), [])
        self.assertEqual(len(self.parts), 56)
        self.assertEqual(
            self.pins["U2"], {"1": "P19_LED_A", "3": "P19_LED_K", "4": "P19_UV_SW_IN", "6": "P19_UV"}
        )
        self.assertEqual(self.pins["Q2"]["2"], "P19_RAMP_CAP")

    def test_reversed_diode_and_transposed_pnp_are_rejected(self):
        for ref, a, b in [
            ("D2", "1", "2"),
            ("Q2", "2", "3"),
            ("U1", "1", "2"),
            ("U2", "3", "4"),
            ("Q3", "1", "2"),
        ]:
            changed = copy.deepcopy(self.pins)
            changed[ref][a], changed[ref][b] = changed[ref][b], changed[ref][a]
            self.assertTrue(contract_errors(self.parts, changed), ref)

    def test_bulk_before_limiter_and_unbudgeted_aux_are_rejected(self):
        changed = copy.deepcopy(self.pins)
        changed["C4"]["1"] = "P19_BANK_OUT"
        self.assertTrue(contract_errors(self.parts, changed))
        changed = copy.deepcopy(self.pins)
        changed["R9"]["1"] = "V2V5_AUX"
        self.assertTrue(contract_errors(self.parts, changed))
        for value in self.analysis["rail_scenarios"].values():
            self.assertEqual(value["additional_v2v5_aux_steady_load_a"], 0)
            self.assertFalse(value["canonical_bulk_rewired"])

    def test_full_shunt_screen_includes_absolute_drift_and_not_just_initial_tolerance(self):
        r = shunt_corners()
        self.assertGreater(r["interval_ohm"][1], 0.091 * 1.04)
        self.assertLess(r["interval_ohm"][1], 0.1)
        self.assertAlmostEqual(r["current_limit_a"][0] * r["interval_ohm"][1], 0.0485)
        self.assertAlmostEqual(r["circuit_breaker_a"][1] * r["interval_ohm"][0], 0.130)
        self.assertFalse(r["all_in_received_lifetime_bound_approved"])

    def test_residual_timer_and_gate_trajectory_are_not_guaranteed(self):
        timer = timer_corners()
        self.assertIsNone(timer["initial_timer_upper_bound_before_each_fault_v"])
        self.assertIsNone(timer["guaranteed_fault_interval_s"])
        self.assertLess(timer["fault_s"][0], timer["fault_s"][1])
        self.assertLess(timer["insertion_s"][1], 1)
        slower = timer_corners(c_nom=940e-9)
        self.assertAlmostEqual(slower["fault_s"][1], 2 * timer["fault_s"][1])
        with self.assertRaises(ValueError):
            timer_corners(leakage=3e-6)
        with self.assertRaises(ValueError):
            ramp(float("nan"), 0.001, 0.1, 1e-6)
        for r in self.analysis["rail_scenarios"].values():
            self.assertIsNone(r["ramp"]["full_trajectory_gate_current_bound_a"])
            self.assertIsNone(r["guaranteed_powerlimit_at_selected_values_w"])

    def test_five_second_and_extra_input_budget_are_honest(self):
        p19 = self.analysis["rail_scenarios"]["P19"]
        p12 = self.analysis["rail_scenarios"]["P12"]
        self.assertGreater(p19["ramp"]["output_only_ramp_s"][1], 12)
        self.assertFalse(p19["ramp"]["five_second_output_only_scenario_pass"])
        self.assertGreater(p19["input_overhead_excess_over_old_controller_reserve_a"], 0.001)
        self.assertGreater(p12["input_overhead_excess_over_old_controller_reserve_a"], 0.001)
        faster = p19["unimplemented_faster_comparison_only"]
        self.assertLess(faster["output_only_ramp_s"][1], 5)
        self.assertGreater(faster["downstream_bulk_plus_live_peak_a"], 0.05)
        self.assertFalse(self.analysis["five_second_wholeunit_pass"])
        self.assertIsNone(self.analysis["complete_startup_bound_s"])

    def test_live_load_energy_is_not_omitted(self):
        r = ramp(20, 0.002, 0.03, 4.7e-6)
        self.assertAlmostEqual(r["capacitor_pass_energy_j"], 0.4)
        self.assertAlmostEqual(
            r["constant_live_load_pass_energy_at_slowest_j"], 0.5 * 0.03 * 20 * r["output_only_ramp_s"][1]
        )
        self.assertGreater(r["constant_live_load_pass_energy_at_slowest_j"], r["capacitor_pass_energy_j"])

    def test_native_draft_warns_unresolved_parts_and_cannot_release(self):
        r = self.receipt
        self.assertTrue(r["native_draft_contract_accepted"])
        self.assertEqual(r["native_erc_errors"], 0)
        self.assertEqual(r["native_erc_warnings"], 6)
        self.assertEqual(set(r["unresolved_footprint_warnings"]), {"C1", "C2", "U2", "C101", "C102", "U102"})
        for k in [
            "build_ready",
            "fabrication_released",
            "startup_qualified",
            "soa_qualified",
            "pcb_implemented",
            "reverse_current_qualified",
        ]:
            self.assertFalse(r[k])
        self.assertEqual(r["physical_tests_performed"], 0)

    def test_sources_and_actual_native_evidence_are_sealed(self):
        for group in ["source_sha256", "evidence_sha256"]:
            for path, expected in self.receipt[group].items():
                self.assertEqual(sha(REPO / path), expected, path)
        for path, expected in self.analysis["source_sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)
        for r in self.analysis["rail_scenarios"].values():
            self.assertTrue(math.isfinite(r["source_total_during_fastest_local_ramp_a"]))


if __name__ == "__main__":
    unittest.main()
