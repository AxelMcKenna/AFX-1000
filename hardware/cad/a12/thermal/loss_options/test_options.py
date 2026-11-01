"""Portable comparison-boundary mutations; actual solver replay remains optional."""

import copy
import os
import unittest

from . import analyze, validate


class LossOptions(unittest.TestCase):
    def setUp(self):
        self.a = analyze.read(analyze.OUT / "analysis.json")

    def test_actual_saved_energy_and_source_closure(self):
        self.assertEqual(validate.packet_errors(), [])
        self.assertEqual(validate.seal_errors(), [])

    def test_lossless_control_is_not_actual_minimum_or_implementation(self):
        rows = [r for r in self.a["counterfactual_references"] if r["variant"] == "endpoint_only"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["result"]["plate_max_c"] > 65 for r in rows))
        self.assertTrue(all(abs(r["result"]["total_w"] - 18.233863094) < 1e-6 for r in rows))
        bad = copy.deepcopy(self.a)
        bad["counterfactual_references"][0]["is_actual_minimum_heat_bound"] = True
        self.assertTrue(validate.errors(bad))

    def test_guard_is_inside_complete_feed_and_remainder_unproved(self):
        rows = self.a["complete_feed_partition"]
        self.assertAlmostEqual(sum(r["resistance_ohm"] for r in rows), 0.36)
        remainder = next(r for r in rows if r["id"] == "unproved_fuse_P03_copper_remainder")
        self.assertAlmostEqual(remainder["heat_at4A_w"], 1.8072)
        bad = copy.deepcopy(self.a)
        bad["complete_feed_partition"].append(copy.deepcopy(rows[4]))
        self.assertTrue(validate.errors(bad))

    def test_AUX_source_dependency_and_efficiency_not_promoted(self):
        row = self.a["AUX_preregulator_option"]
        self.assertIn("upstream ofU101", row["input_node_required"])
        self.assertAlmostEqual(row["efficiency_comparisons"][0]["conditional_saving_w"], 0.65932)
        bad = copy.deepcopy(self.a)
        bad["AUX_preregulator_option"]["efficiency_comparisons"][0]["efficiency_is_guaranteed"] = True
        self.assertTrue(validate.errors(bad))

    def test_primary_component_catalog_limits_do_not_approve_system(self):
        self.assertFalse(self.a["XLR_inlet_comparison"]["hot_aged_mated_resistance_bound_established"])
        self.assertTrue(
            self.a["Q101_hot_resistance_review"]["room_temperature12mohm_not_promoted_to_hot4A_bound"]
        )
        self.assertGreater(self.a["analog_pre_5v7_option"]["conditional_dropout_margin_v"], 0.13)
        self.assertFalse(self.a["analog_pre_5v7_option"]["PSRR_noise_loadstep_startup_qualified"])

    def test_load_or_heat_target_change_rejected(self):
        bad = copy.deepcopy(self.a)
        bad["retained_baseline_heat_target_w"] -= 1
        self.assertIn("Existing load/heat target changed", validate.errors(bad))
        bad = copy.deepcopy(self.a)
        bad["actual_loss_saving_guaranteed_w"] = 0.7
        self.assertTrue(validate.errors(bad))

    @unittest.skipUnless(
        os.environ.get("AFX_LOSS_OPTIONS_SOLVER_TEST") == "1", "Optional actual SciPy reference replay"
    )
    def test_optional_endpoint_solver_control(self):
        from hardware.cad.a12.thermal.whole_unit.plate import plate_scenario

        wu = analyze.read(analyze.WU / "generated/analysis.json")
        ledger = analyze.read(analyze.WU / "generated/ledger.json")
        categories = {r["id"]: r["category"] for r in ledger["leaf_heat_rows"]}
        rows = copy.deepcopy(wu["source_placements"]["unplaced_uniform"])
        for r in rows:
            if categories[r["id"]] != "delivered_endpoint":
                r["watts"] = 0
        d = analyze.read(analyze.WU / "sources/hardware/cad/a12/thermal/design.json")
        r = plate_scenario(d, rows, 3, 0.8)
        self.assertAlmostEqual(r["plate_max_c"], 66.9446989262, places=6)


if __name__ == "__main__":
    unittest.main()
