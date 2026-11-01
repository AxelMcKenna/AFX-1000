"""E12 design qualification cannot be inferred from a clean connectivity report."""

import copy
import json
import unittest

from hardware.electronics.adc_driver.qualification.audit import (
    PARENT,
    REPO,
    ROOT,
    SENSITIVE_PINS,
    analyze,
    bias_health_headroom,
    path_witness,
    plane_coverage,
    sha,
    supply_screen,
    surface_leakage,
)
from hardware.electronics.adc_driver.qualification.native import relief_areas
from hardware.electronics.adc_driver.qualification.spice import deck, source_circuit
from hardware.electronics.common.sexpr import first, read_sexpr


class ADCQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = read_sexpr((PARENT / "pcb/adc_driver.kicad_pcb").read_text())
        cls.filled = read_sexpr((PARENT / "pcb/generated/filled.kicad_pcb").read_text())
        cls.review = analyze()

    def test_continuous_plane_at_sensitive_pins_is_detected_as_failure(self):
        coverage = plane_coverage(self.filled)
        self.assertEqual(len(coverage), 8)
        self.assertTrue(all(all(planes.values()) for planes in coverage.values()))
        self.assertFalse(self.review["manufacturer_plane_opening_requirement_satisfied"])
        self.assertEqual(self.review["findings"][0]["state"], "failed")

    def test_missing_fill_cannot_be_mistaken_for_successful_plane_relief(self):
        tree = copy.deepcopy(self.filled)
        tree[:] = [n for n in tree if not isinstance(n, list) or not n or n[0] != "zone"]
        with self.assertRaises(AssertionError):
            plane_coverage(tree)

    def test_relief_trial_changes_only_eight_explicit_rule_areas(self):
        baseline = copy.deepcopy(self.tree)
        areas = relief_areas(self.tree)
        self.assertEqual(self.tree, baseline)
        self.assertEqual(len(areas), len(SENSITIVE_PINS))
        for zone in areas:
            self.assertEqual(first(zone, "layers")[1:], ["In1.Cu", "In4.Cu"])
            self.assertEqual(first(first(zone, "keepout"), "copperpour")[1], "not_allowed")
            self.assertEqual(first(first(zone, "keepout"), "tracks")[1], "allowed")
            self.assertEqual(first(first(zone, "keepout"), "vias")[1], "allowed")

    def test_supply_range_uses_both_rails_and_rejects_total_overvoltage(self):
        normal = supply_screen()
        self.assertTrue(normal["fda_dc_supply_screen_passes"])
        # A positive supply alone can appear acceptable while the total exceeds 5.4 V.
        bad = supply_screen(v5=(4.9, 5.2), nbias=(-0.27, -0.16))
        self.assertTrue(bad["pump_positive_dc_screen_passes"])
        self.assertFalse(bad["fda_dc_supply_screen_passes"])

    def test_route_witness_uses_connected_multilayer_copper(self):
        result = path_witness(self.tree, "V5_REG", ("U1", "3"), ("C13", "1"))
        self.assertEqual(result["vias"], 2)
        self.assertGreater(result["conservative_segment_sum_mm"], result["pad_center_distance_mm"])
        self.assertIn("In2.Cu", result["layers"])

    def test_deleted_power_copper_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        tree[:] = [n for n in tree if not isinstance(n, list) or not n or n[0] not in ("segment", "via")]
        with self.assertRaises(AssertionError):
            path_witness(tree, "V5_REG", ("U1", "3"), ("C13", "1"))

    def test_leakage_sensitivity_is_a_calculation_not_an_invented_acceptance_limit(self):
        result = surface_leakage(0.0001)
        self.assertAlmostEqual(result["maximum_added_leakage_a"], 0.2e-9)
        self.assertAlmostEqual(result["minimum_isolation_to_aggressor_ohm"], 51.75e9)
        self.assertFalse(result["qualification_acceptance_limit"])
        with self.assertRaises(AssertionError):
            surface_leakage(0)

    def test_no_stage_noise_or_typical_scale_is_promoted_to_full_unit_pass(self):
        self.assertFalse(self.review["stage_noise_screen_is_complete_weighted_snr"])
        self.assertFalse(self.review["fda_model_review"]["manufacturer_loop_model_executed"])
        self.assertFalse(self.review["build_ready"])
        self.assertFalse(self.review["fabrication_released"])
        self.assertEqual(self.review["physical_tests_performed"], 0)

    def test_unknown_physical_acceptance_limits_remain_explicitly_blocked(self):
        cases = json.loads((ROOT / "measurements.json").read_text())
        for row in cases:
            if row["limits"] is None:
                self.assertEqual(row["state"], "blocked")
        self.assertTrue(any(row["id"] == "ADC-LEAKAGE" and row["limits"] is None for row in cases))

    def test_bias_health_window_cannot_certify_a_larger_headroom_reserve(self):
        allocation = self.review["existing_allocated_screen"]
        old = bias_health_headroom(allocation)
        self.assertFalse(old["existing_window_guarantees_its_own_headroom_allocation"])
        self.assertAlmostEqual(old["headroom_at_existing_window_upper_v"], 0.2938795540624857)
        self.assertAlmostEqual(old["required_upper_bias_for_this_screen_v"], -0.1661204459375143)
        narrower = bias_health_headroom(allocation, upper_health_v=-0.18)
        self.assertTrue(narrower["existing_window_guarantees_its_own_headroom_allocation"])
        self.assertFalse(narrower["actual_clipping_or_thd_verified"])
        self.assertFalse(narrower["threshold_tolerances_and_dynamic_margin_included"])

    def test_vendor_deck_uses_native_force_sense_and_actual_capacitors(self):
        parts, pins = source_circuit()
        lines = deck(parts, pins, "/external/ths4551.lib")
        self.assertIn("R3 ADC_LN FB_P_L 1210", lines)
        self.assertIn("C1 DRV_LN FB_P_L 1e-12", lines)
        self.assertIn("XFDA FB_P_L FB_N_L DRV_LP DRV_LN VOCM_L V5_REG NBIAS_L THS4551", lines)
        swapped = copy.deepcopy(pins)
        swapped["U1"]["4"], swapped["U1"]["5"] = swapped["U1"]["5"], swapped["U1"]["4"]
        with self.assertRaises(AssertionError):
            deck(parts, swapped, "/external/ths4551.lib")
        moved = copy.deepcopy(pins)
        moved["R3"]["1"] = "DRV_LN"
        with self.assertRaises(AssertionError):
            deck(parts, moved, "/external/ths4551.lib")

    def test_model_scenarios_are_explicit_and_invalid_sweeps_rejected(self):
        parts, pins = source_circuit()
        lines = deck(
            parts,
            pins,
            "/external/ths4551.lib",
            analysis="dc",
            load="differential",
            extra_input_pf=0.5,
            extra_output_pf=22,
            dc_start=0,
            dc_stop=-6,
            dc_step=-0.25,
        )
        self.assertIn(".dc VIN 0 -6 -0.25", lines)
        self.assertIn("RLD ADC_LP ADC_LN 260", lines)
        self.assertIn("CPARIN0 FB_P_L 0 5e-13", lines)
        self.assertIn("CPAROUT0 ADC_LP 0 2.2e-11", lines)
        for invalid in ({"dc_start": 0, "dc_stop": -6}, {"extra_input_pf": -1}, {"positive_v": 5.3}):
            with self.assertRaises(AssertionError):
                deck(parts, pins, "/external/ths4551.lib", **invalid)

    def test_saved_vendor_receipt_binds_evidence_and_rejects_dc_claims(self):
        folder = ROOT / "generated/vendor-spice"
        result = json.loads((folder / "verification.json").read_text())
        for name, digest in result["evidence_sha256"].items():
            self.assertEqual(sha(folder / name), digest, name)
        for name, digest in result["source_sha256"].items():
            self.assertEqual(sha(REPO / name), digest, name)
        self.assertEqual(result["physical_tests_performed"], 0)
        self.assertFalse(result["build_ready"])
        self.assertFalse(result["phase_margin_verified"])
        self.assertFalse(result["dc_common_mode_load_discrepancy_resolved"])
        self.assertEqual(set(result["rejected_solver_cases"]), {"dc_nominal", "dc_low_supply"})
        for case in result["cases"]:
            self.assertEqual(sha(folder / (case["id"] + ".cir")), case["netlist_sha256"])
            self.assertEqual(case["solver_comparison_eligible"], not case["solver_warnings"])
            if case["analysis"] == "dc":
                self.assertFalse(case["dc_hardware_headroom_interpretation_accepted"])


if __name__ == "__main__":
    unittest.main()
