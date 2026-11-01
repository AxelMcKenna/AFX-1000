"""Meaningful portable power-flow mutations and optional independent solver replay."""

import copy
import math
import os
import unittest

from . import ledger, validate


class WholeUnitHeat(unittest.TestCase):
    def setUp(self):
        self.ledger = ledger.read(ledger.OUT / "ledger.json")
        self.analysis = ledger.read(ledger.OUT / "analysis.json")

    def test_energy_source_tree_and_actual_saved_evidence(self):
        self.assertEqual(validate.packet_errors(), [])
        self.assertEqual(self.ledger, {**ledger.build(), "source_sha256": self.ledger["source_sha256"]})
        self.assertAlmostEqual(self.ledger["total_internal_heat_screen_w"], 35.43154587633119)

    def test_duplicate_endpoint_or_return_heat_cannot_pass(self):
        a = copy.deepcopy(self.ledger)
        a["leaf_heat_rows"].append(copy.deepcopy(a["leaf_heat_rows"][0]))
        self.assertIn("Duplicate counted power leaf", validate.energy_errors(a))
        a = copy.deepcopy(self.ledger)
        a["ground_current_diagnostic_excluded"]["added_w"] = 0.1
        self.assertTrue(validate.energy_errors(a))

    def test_missing_converter_loss_cannot_be_hidden_by_endpoint_sum(self):
        a = copy.deepcopy(self.ledger)
        r = next(r for r in a["leaf_heat_rows"] if r["id"] == "DIG_converter_loss")
        a["leaf_heat_rows"].remove(r)
        a["total_internal_heat_screen_w"] -= r["watts"]
        self.assertTrue(validate.energy_errors(a))

    def test_guard_subtracted_from_complete_feed_and_3v3_is_nested(self):
        a = self.ledger
        self.assertAlmostEqual(a["blocks"]["complete_input_feed_heat_w"], 4**2 * 0.36)
        row = next(r for r in a["leaf_heat_rows"] if r["id"] == "inlet_wire_fuse_and_contacts")
        self.assertAlmostEqual(row["watts"], 4**2 * (0.36 - 0.040 - 0.053))
        self.assertEqual(a["nested_3v3_diagnostics"]["separately_added_to_heat_w"], 0)
        self.assertAlmostEqual(a["nested_3v3_diagnostics"]["nominal_child_output_power_w"], 0.2475)
        bad = copy.deepcopy(a)
        bad["nested_3v3_diagnostics"]["separately_added_to_heat_w"] += 0.2475
        self.assertTrue(validate.energy_errors(bad))

    def test_negative_rails_never_cancel_positive_heat(self):
        a = self.ledger
        neg = [r for r in a["leaf_heat_rows"] if r.get("source_domain", "").startswith("N")]
        pos = [r for r in a["leaf_heat_rows"] if r.get("source_domain", "").startswith("P")]
        self.assertEqual(len(neg), 6)
        self.assertEqual(len(pos), 6)
        self.assertGreater(math.fsum(r["watts"] for r in neg), 2)
        bad = copy.deepcopy(a)
        next(r for r in bad["leaf_heat_rows"] if r["id"] == neg[0]["id"])["watts"] *= -1
        self.assertTrue(validate.energy_errors(bad))

    def test_complete_N22_need_and_partial_E28_inventory_are_explicit(self):
        a = self.ledger
        row = a["retained_raw_current_envelopes"]["RAW_N22"]
        self.assertGreater(row["complete_required_a"], row["old_allocation_a"])
        self.assertAlmostEqual(row["retained_allocation_a"], row["complete_required_a"])
        self.assertFalse(a["E28_partial_native_inventory"]["all_currents_covered"])
        self.assertTrue(
            a["E28_partial_native_inventory"][
                "five_volt_known_resistors_assigned_inside_existing_DIG416mA_ANA8mA_reserves"
            ]
        )

    def test_h_sensitivity_and_actual_source_positions(self):
        a = self.analysis
        self.assertEqual(validate.analysis_errors(a, self.ledger), [])
        self.assertGreater(a["cases"][2]["result"]["plate_max_c"], 95)
        for sources in a["source_placements"].values():
            processor = next(r for r in sources if r["id"] == "seed_local")
            self.assertEqual(processor["rect_housing_mm"], [30, 42, 150, 65])
        bad = copy.deepcopy(a)
        bad["cases"][2]["result"]["converged"] = False
        self.assertTrue(validate.analysis_errors(bad, self.ledger))

    def test_historical_equations_replay_exactly(self):
        rows = self.analysis["historical_equation_controls"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(abs(r["delta_c"]) < 1e-7 for r in rows))
        bad = copy.deepcopy(self.analysis)
        bad["historical_equation_controls"][0]["delta_c"] = 0.1
        self.assertIn(
            "Historical equation control failed/missing", validate.analysis_errors(bad, self.ledger)
        )

    def test_source_consistent_electrical_heat_equals_plug_power(self):
        for row in self.analysis["steady_source_consistent_diagnostic"]["points"]:
            self.assertAlmostEqual(
                row["total_input_heat_w"], row["plug_voltage_v"] * row["common_feed_current_a"]
            )
            self.assertGreater(row["total_input_heat_w"], 31)
            self.assertFalse(row["qualifications"])

    def test_unproved_external_export_or_bounds_are_rejected(self):
        a = copy.deepcopy(self.ledger)
        a["export_credit_w"] = 1
        self.assertTrue(validate.energy_errors(a))
        a = copy.deepcopy(self.analysis)
        a["actual_whole_unit_heat_upper_w"] = 35.5
        self.assertTrue(validate.analysis_errors(a, self.ledger))
        self.assertFalse(
            self.analysis["omit_unknown_external_feed_heat_diagnostic"]["export_credit_is_adopted"]
        )
        self.assertGreater(
            self.analysis["omit_unknown_external_feed_heat_diagnostic"]["result"]["plate_max_c"], 88
        )

    def test_seal_and_stale_input_mutation(self):
        a = ledger.read(ledger.ROOT / "handoff.json")
        self.assertEqual(validate.seal_errors(a), [])
        a["sha256"][next(iter(a["sha256"]))] = "0" * 64
        self.assertTrue(validate.seal_errors(a))

    @unittest.skipUnless(
        os.environ.get("AFX_WHOLE_UNIT_SOLVER_TEST") == "1", "Optional NumPy/SciPy source-bound replay"
    )
    def test_optional_actual_solver_replay(self):
        from .plate import plate_scenario

        design = ledger.read(ledger.SOURCES / "hardware/cad/a12/thermal/design.json")
        result = plate_scenario(design, self.analysis["source_placements"]["unplaced_uniform"], 3, 0.8)
        self.assertAlmostEqual(result["plate_max_c"], 95.36308973971175, places=6)
        self.assertLess(abs(result["energy_balance_residual_w"]), 1e-6)


if __name__ == "__main__":
    unittest.main()
