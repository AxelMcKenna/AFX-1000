"""R2 checks bind real native evidence while refusing to certify missing physical work."""

import copy
import json
import unittest

from hardware.electronics.adc_driver.qualification.audit import REPO, sha
from hardware.electronics.adc_driver.revision2.design import COMPONENTS, ROOT, thresholds
from hardware.electronics.adc_driver.revision2.generate import STACKUP
from hardware.electronics.adc_driver.revision2.verify import (
    bias_window_truth,
    check_circuit,
    leakage_screen,
    pd_levels,
)
from hardware.electronics.common.netlists import netlist


class ADCRevision2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.pins = netlist(ROOT / "generated/native/netlist.xml")
        cls.receipt = json.loads((ROOT / "generated/native/verification.json").read_text())

    def test_fresh_native_repaired_board_is_connected_and_parity_clean(self):
        self.assertEqual(self.receipt["counts"], dict(erc=0, drc=0, opens=0, parity=0))
        self.assertTrue(check_circuit(self.parts, self.pins))
        self.assertTrue(
            self.receipt["actual_r2_linear_headroom_screen"]["conditional_headroom_allocation_satisfied"]
        )
        self.assertFalse(
            self.receipt["actual_r2_linear_headroom_screen"]["physical_headroom_or_thd_verified"]
        )
        self.assertTrue(self.receipt["all_sensitive_pad_centres_free_of_plane_fill"])

    def test_reversing_a_real_comparator_input_pair_is_rejected(self):
        pins = copy.deepcopy(self.pins)
        pins["U7"]["4"], pins["U7"]["5"] = pins["U7"]["5"], pins["U7"]["4"]
        with self.assertRaises(AssertionError):
            check_circuit(self.parts, pins)
        for left, right in [(-0.1, -0.23), (-0.4, -0.23), (-0.23, -0.1), (-0.23, -0.4)]:
            self.assertFalse(bias_window_truth(left, right))
        self.assertTrue(bias_window_truth(-0.23, -0.23))

    def test_both_windows_have_tolerance_margin_to_headroom_and_pump_range(self):
        corners = thresholds()
        self.assertLess(corners["upper_trip_v"][1], -0.1661204459375143)
        self.assertGreater(corners["upper_trip_v"][0], -0.20198)
        self.assertLess(corners["lower_trip_v"][1], -0.256)
        self.assertLess(5.025 - corners["lower_trip_v"][0], 5.4)
        # Ordinary1% divider substitutions break this protection allocation.
        with self.assertRaises(AssertionError):
            thresholds(resistor_error=0.01)
        self.assertFalse(corners["physical_thresholds_measured"])

    def test_guaranteed_reset_low_is_scaled_relative_to_negative_supply(self):
        levels = pd_levels()
        self.assertEqual(levels["guaranteed_reset_low_v"], 0.4)
        self.assertTrue(levels["static_levels_pass"])
        self.assertGreater(0.4 + 0.286, 0.55)  # direct ground-referenced reset would fail.
        self.assertFalse(pd_levels(reset_max=0.8)["static_levels_pass"])
        self.assertEqual(self.pins["R15"]["2"], "NBIAS_L")
        self.assertEqual(self.pins["R31"]["2"], "NBIAS_R")
        self.assertFalse(levels["delay_or_partial_power_verified"])

    def test_force_and_sense_are_separate_actual_connector_terminals(self):
        self.assertEqual(self.pins["J2"]["1"], "ADC_LP")
        self.assertEqual(self.pins["J2"]["2"], "SENSE_LP")
        self.assertEqual(self.pins["R4"]["1"], "SENSE_LP")
        self.assertEqual(self.pins["R5"]["2"], "ADC_LP")
        pins = copy.deepcopy(self.pins)
        pins["R4"]["1"] = "ADC_LP"
        with self.assertRaises(AssertionError):
            check_circuit(self.parts, pins)
        self.assertIsNone(self.receipt["approved_cable_length_mm"])
        self.assertFalse(self.receipt["final_converter_pin_feedback_verified"])

    def test_bypass_witnesses_are_actual_shorter_routes_with_one_via(self):
        witnesses = self.receipt["actual_route_witnesses"]
        for name, row in witnesses.items():
            self.assertNotIn("failed", row, name)
            self.assertEqual(row["vias"], 1, name)
            self.assertLess(row["conservative_segment_sum_mm"], 4, name)
            self.assertFalse(row["rf_impedance_extracted"])

    def test_stackup_and_passive_selection_have_real_declared_geometry(self):
        self.assertAlmostEqual(sum(t for _, t in STACKUP), 1.6)
        parts = {c["ref"]: c for c in COMPONENTS}
        self.assertTrue(all(c.get("mpn") for c in COMPONENTS if c["ref"].startswith(("R", "C"))))
        self.assertIn("C_1206", parts["C33"]["footprint"])
        self.assertIn("X7S", parts["C9"]["part"])
        self.assertIn("X7S", parts["C10"]["part"])
        self.assertFalse(self.receipt["physical_stackup_fabricator_approved"])

    def test_lower_leakage_sensitivity_does_not_claim_zero_error(self):
        result = leakage_screen()
        self.assertEqual(result["reference_thevenin_ohm"], 50000)
        self.assertAlmostEqual(result["added_0p2na_leakage_shift_v"], 10e-6)
        self.assertEqual(result["finite_servo_dc_gain"], 2000)
        self.assertFalse(result["physical_leakage_or_reference_loading_verified"])

    def test_saved_native_and_model_receipts_match_current_sources_and_evidence(self):
        for relative in ["native", "model-review", "spice"]:
            folder = ROOT / "generated" / relative
            receipt = json.loads((folder / "verification.json").read_text())
            for name, digest in receipt["source_sha256"].items():
                self.assertEqual(sha(REPO / name), digest, name)
            for name, digest in receipt["evidence_sha256"].items():
                self.assertEqual(sha(folder / name), digest, name)
            self.assertEqual(receipt["physical_tests_performed"], 0)
            self.assertFalse(receipt["fabrication_released"])
            self.assertFalse(receipt["build_ready"])


if __name__ == "__main__":
    unittest.main()
