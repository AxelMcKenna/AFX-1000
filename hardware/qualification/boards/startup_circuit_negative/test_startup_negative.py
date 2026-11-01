"""Portable actual-export, polarity, state and uncertainty regression checks."""

import copy
import json
import math
import unittest

from hardware.electronics.common.netlists import netlist

from .analyze import OUT, ramp, sha, shunt_corners, timer_corners
from .design import REPO
from .verify import analysis_errors, contract_errors


class NegativeStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.pins = netlist(OUT / "netlist.xml")
        cls.a = json.loads((OUT / "analysis.json").read_text())
        cls.receipt = json.loads((OUT / "verification.json").read_text())

    def test_actual_native_pin_contract(self):
        self.assertEqual(contract_errors(self.parts, self.pins), [])
        self.assertEqual(len(self.parts), 60)
        self.assertEqual(self.pins["U1"]["5"], "N19_BANK_OUT")
        self.assertEqual(self.pins["U1"]["7"], "N19_SENSE")
        self.assertEqual(self.pins["U1"]["8"], "N19_GATE_CTRL")

    def test_positive_controller_pinmap_and_reversed_fet_or_diode_fail(self):
        for ref, a, b in [
            ("U1", "1", "7"),
            ("U1", "5", "10"),
            ("Q1", "2", "3"),
            ("D1", "1", "2"),
            ("D2", "1", "2"),
            ("U2", "1", "4"),
        ]:
            p = copy.deepcopy(self.pins)
            p[ref][a], p[ref][b] = p[ref][b], p[ref][a]
            self.assertTrue(contract_errors(self.parts, p), ref)

    def test_negative_bulk_polarity_and_reference_fail_if_mirrored(self):
        for ref, pin, wrong in [
            ("C5", "1", "N19_PROTECTED"),
            ("C105", "2", "N12_BANK_OUT"),
            ("C3", "2", "AGND"),
            ("R8", "2", "AGND"),
            ("R11", "1", "V2V5_AUX"),
            ("C1", "2", "N19_SENSE"),
        ]:
            p = copy.deepcopy(self.pins)
            p[ref][pin] = wrong
            self.assertTrue(contract_errors(self.parts, p), ref)

    def test_missing_and_changed_bulk_are_rejected(self):
        parts = dict(self.parts)
        del parts["Q1"]
        self.assertTrue(contract_errors(parts, self.pins))
        parts = copy.deepcopy(self.parts)
        parts["C5"].find("value").text = "220uF"
        self.assertTrue(contract_errors(parts, self.pins))

    def test_shunt_and_negative_timer_limits_are_not_positive_rail_values(self):
        r = shunt_corners()
        self.assertAlmostEqual(r["current_limit_a"][0] * r["interval_ohm"][1], 0.044)
        self.assertAlmostEqual(r["current_limit_a"][1] * r["interval_ohm"][0], 0.056)
        self.assertGreater(r["interval_ohm"][1], 0.091 * 1.04)
        self.assertLess(r["interval_ohm"][1], 0.1)
        t = timer_corners()
        self.assertAlmostEqual(t["fault_from_zero_s"][0], 423e-9 * 3.76 / 140.1e-6)
        self.assertAlmostEqual(timer_corners(940e-9)["fault_from_zero_s"][1], 2 * t["fault_from_zero_s"][1])
        self.assertIsNone(t["initial_timer_upper_before_each_fault_v"])
        self.assertIsNone(t["guaranteed_reset_s"])
        self.assertGreater(t["latched_discharge_4p16_to_0p3_s"], 2)
        for invalid in [0.9e-6, float("nan")]:
            with self.assertRaises(ValueError):
                timer_corners(leakage=invalid)

    def test_cgs_charge_not_omitted_and_no_complete_time_claim(self):
        r = ramp(19.1, 0.0018, 0.027, 1.5e-6, 22e-6, 82)
        self.assertLess(r["output_only_scenario_s"][1], 2)
        self.assertGreater(r["external_cap_charge_time_at_30ua_s"], 9)
        self.assertFalse(r["full_cap_charge_scenario_within_5s"])
        more = ramp(19.1, 0.0018, 0.027, 1.5e-6, 44e-6, 82)
        self.assertGreater(
            more["external_cap_charge_time_at_30ua_s"], r["external_cap_charge_time_at_30ua_s"]
        )
        self.assertIsNone(r["guaranteed_fault_turnoff_s"])
        self.assertGreater(r["input_step_initial_feedback_current_if_gate_clamped_a"], 0.2)
        self.assertFalse(r["step_current_is_guaranteed"])
        self.assertIsNone(r["guaranteed_complete_startup_s"])
        self.assertFalse(r["cross_controller_network_validated"])
        self.assertAlmostEqual(
            r["ideal_constant_live_pass_energy_slowest_j"],
            0.5 * 0.027 * 19.1 * r["output_only_scenario_s"][1],
        )
        with self.assertRaises(ValueError):
            ramp(19.1, float("nan"), 0.027, 1.5e-6, 22e-6, 82)

    def test_recommended_supply_failure_and_input_current_assignment(self):
        n12 = self.a["rail_scenarios"]["N12"]
        n19 = self.a["rail_scenarios"]["N19"]
        self.assertTrue(n12["vcc"]["failure"].startswith("FAIL"))
        self.assertFalse(n12["vcc"]["recommended_2ma_established_by_comparison"])
        self.assertIsNone(n12["vcc"]["regulated_icc_scenario_a"])
        self.assertIsNone(n12["vcc"]["guaranteed_operating_supply_interval_v"])
        self.assertGreater(n19["vcc"]["regulated_icc_scenario_a"][0], 0.002)
        for row in [n12, n19]:
            self.assertAlmostEqual(row["downstream_added_scenario_a"], 0.00055)
            self.assertGreater(row["input_pg_pullup_bad_state_current_scenario_a"], 0.0001)
            self.assertFalse(row["external_anti_injection"]["catalog_clamp_25c_only_screen"])
            self.assertFalse(row["external_anti_injection"]["insertion_off_qualified"])
            self.assertIsNone(row["guaranteed_actual_selected_powerlimit_w"])

    def test_digital_interface_and_false_claim_mutations(self):
        d = self.a["digital_interface"]
        self.assertEqual(d["additional_v2v5_aux_load_a"], 0)
        self.assertGreater(d["led_min_scenario_a"], 0.002)
        self.assertLess(d["led_series_current_max_scenario_a"], 0.004)
        self.assertFalse(d["e28_j9_2p5v_direct_compatible"])
        self.assertEqual(analysis_errors(self.a), [])
        for key in [
            "five_second_wholeunit_pass",
            "guaranteed_ramp_network",
            "pcb_implemented",
            "soa_qualified",
        ]:
            changed = copy.deepcopy(self.a)
            changed[key] = True
            self.assertTrue(analysis_errors(changed), key)
        changed = copy.deepcopy(self.a)
        changed["rail_scenarios"]["N12"]["vcc"]["failure"] = None
        self.assertTrue(analysis_errors(changed))
        for key in [
            "guaranteed_complete_startup_s",
            "guaranteed_output_slew_v_per_s",
            "guaranteed_fault_turnoff_s",
        ]:
            changed = copy.deepcopy(self.a)
            changed["rail_scenarios"]["N19"]["ramp"][key] = [1, 2]
            self.assertTrue(analysis_errors(changed), key)

    def test_actual_native_draft_evidence_and_hashes(self):
        r = self.receipt
        self.assertTrue(r["native_draft_contract_accepted"])
        self.assertEqual(r["native_erc_errors"], 0)
        self.assertEqual(r["native_erc_warnings"], 8)
        self.assertEqual(
            set(r["unresolved_footprints"]), {"C1", "C2", "C3", "U2", "C101", "C102", "C103", "U102"}
        )
        for k in [
            "build_ready",
            "fabrication_released",
            "startup_qualified",
            "soa_qualified",
            "pcb_implemented",
            "reverse_current_qualified",
        ]:
            self.assertFalse(r[k])
        for group in ["source_sha256", "evidence_sha256"]:
            for path, expected in r[group].items():
                self.assertEqual(sha(REPO / path), expected, path)
        for path, expected in self.a["source_sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)
        for row in self.a["rail_scenarios"].values():
            self.assertTrue(math.isfinite(row["source_total_fast_output_sensitivity_a"]))


if __name__ == "__main__":
    unittest.main()
