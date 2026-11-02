"""Boundary and installed-leakage checks for the E13 selection proposal."""

import json
import unittest
from pathlib import Path

from hardware.fabrication.rail_monitor_resistors import (
    build,
    combined_error,
    four_digit,
    ordinary_logic_screen,
    precision_candidate,
    shunted_minimum,
)


class ResistorSelection(unittest.TestCase):
    def test_low_value_tolerance_restriction_does_not_create_invalid_PLT_codes(self):
        self.assertEqual(precision_candidate(127), ("CRT", "CRT0805-PT-1270ELF", 2))
        self.assertEqual(precision_candidate(250)[0], "CRT")
        self.assertEqual(precision_candidate(270), ("PLT", "PLT0805Z2700LSTS", 5))
        self.assertEqual(precision_candidate(91000), ("PLT", "PLT0805Z9102LSTS", 5))
        with self.assertRaises(ValueError):
            precision_candidate(260001)

    def test_order_code_cannot_round_a_resistance(self):
        self.assertEqual(four_digit(105000), "1053")
        with self.assertRaises(ValueError):
            four_digit("127.1")

    def test_parallel_leakage_is_combined_with_worst_intrinsic_error(self):
        self.assertGreaterEqual(shunted_minimum(20e6, 0.04, 2e9), 19e6)
        self.assertLess(shunted_minimum(20e6, 0.04, 1e9), 19e6)
        self.assertAlmostEqual(shunted_minimum(20e6, 0.04, 2e9), 19_017_432.64659271)
        for args in [(0, 0.04, 2e9), (20e6, -0.01, 2e9), (20e6, 1, 2e9), (20e6, 0.04, 0)]:
            with self.assertRaises(ValueError):
                shunted_minimum(*args)

    def test_drift_products_are_not_discarded_from_the_error_budget(self):
        self.assertGreater(combined_error("0.0002", "0.0002", "0.0005"), combined_error("0.0009"))
        self.assertGreater(combined_error("0.0001", "0.0002", "0.0005", "0.0005"), combined_error("0.001"))
        with self.assertRaises(ValueError):
            combined_error("-0.0001")

    def test_ordinary_drift_keeps_the_original_logic_enclosure(self):
        result = ordinary_logic_screen()
        self.assertTrue(result["inside_existing_DC_enclosure"])
        self.assertGreater(result["comparator_high_min_v"], 3.04)
        self.assertLess(result["comparator_high_max_v"], 3.55)
        self.assertLess(result["final_output_load_a"], 100e-6)
        self.assertFalse(ordinary_logic_screen(0.5)["inside_existing_DC_enclosure"])

    def test_saved_inventory_matches_current_actual_board_and_retains_holds(self):
        report, table = build()
        root = Path(__file__).resolve().parents[2] / "hardware/fabrication/parts/rail-monitor-resistors-01"
        self.assertEqual(report, json.loads((root / "candidates.json").read_text()))
        self.assertEqual(table, (root / "candidates.csv").read_text())
        self.assertEqual(report["counts"], {"precision": 79, "feedback": 16, "ordinary": 19})
        self.assertFalse(report["fabrication_approved"])
        self.assertFalse(report["conditional_budget_screens"]["R83_unscreened_bound_fits"])
        self.assertFalse(report["R83_land_comparison"]["existing_land_matches_manufacturer_recommendation"])


if __name__ == "__main__":
    unittest.main()
