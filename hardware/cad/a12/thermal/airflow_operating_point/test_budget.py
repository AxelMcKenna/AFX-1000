"""Conservation, parallel topology and rejected restriction regressions."""

import math
import unittest

from .analyze import branches, compute, drop, flow_for_heat, read


class OperatingPoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compute()
        cls.curve = read("sf01-analysis.json")["parts"]["V1"]["curve_points_cfm_inH2O"]

    def test_rejected_small_meter_remains_failure(self):
        row = branches(self.curve, 5300, 0.6, 2563.12, 2557.14, 868.2, 125)
        self.assertFalse(row["requested_split_passes_known_loss_comparison"])
        self.assertLess(row["base_unknown_loss_allowance_pa"], -6)
        self.assertGreater(row["interior_unknown_loss_allowance_pa"], 0)

    def test_parallel_branches_are_not_summed_as_serial(self):
        row = branches(self.curve, 5300, 0.6, 2563.12, 2557.14, 868.2, 250)
        correct = row["common_guard_loss_pa"] + max(row["interior_port_losses_pa"], row["base_meter_loss_pa"])
        wrong = row["common_guard_loss_pa"] + row["interior_port_losses_pa"] + row["base_meter_loss_pa"]
        self.assertAlmostEqual(row["minimum_known_pressure_for_requested_split_pa"], correct)
        self.assertGreater(wrong, correct)

    def test_ideal_branch_split_conserves_flow_and_pressure(self):
        for row in self.result["pressure_comparisons"]:
            split = row["ideal_zero_other_loss_split_at_total10"]
            self.assertAlmostEqual(sum(split.values()), 10)
            pi = row["interior_port_losses_pa"] * (split["interior_m3h"] / 8.8)**2
            pb = row["base_meter_loss_pa"] * (split["base_m3h"] / 1.2)**2
            self.assertAlmostEqual(pi, pb)

    def test_orifice_energy_scaling_and_opening(self):
        self.assertAlmostEqual(drop(2, 200, 0.6), 4 * drop(1, 200, 0.6))
        self.assertAlmostEqual(drop(1, 200, 0.6), 4 * drop(1, 400, 0.6))
        for invalid in [(1, 0, .6), (-1, 200, .6), (1, 200, 0)]:
            with self.assertRaises(ValueError):
                drop(*invalid)

    def test_new_heat_is_enclosing_capacity_without_second_fan_load(self):
        r = self.result
        self.assertAlmostEqual(r["heat_capacity_requirement_w"], 37.405705857925085)
        self.assertEqual(r["proposed_DIG_capacity_a"], 2.42)
        self.assertFalse(r["new_source_current_voltage_connector_guard_startup_PDN_qualified"])
        self.assertEqual(r["fan_motor_or_controller_extra_heat_added_w"], 0)
        self.assertTrue(r["digital_loads_are_suballocations_of_existing_capacity"])
        q = flow_for_heat(r["heat_capacity_requirement_w"] * 1.2, 58, 101325)
        heat_recovered = q / 3600 * (101325 / (287.05 * 313.15)) * 1000 * 18
        self.assertTrue(math.isclose(heat_recovered, r["heat_capacity_requirement_w"] * 1.2))

    def test_sea_level_energy_pass_does_not_hide_altitude_failure(self):
        for r in self.result["energy_comparisons"]:
            self.assertEqual(r["target_covers_necessary_energy_flow"], r["pressure_pa"] == 101325)

    def test_marginal_200_does_not_equal_generous_300(self):
        small = branches(self.curve, 5300, .6, 2563.12, 2557.14, 868.2, 200)
        large = branches(self.curve, 5300, .6, 2563.12, 2557.14, 868.2, 300)
        self.assertLess(small["base_unknown_loss_allowance_pa"], .7)
        self.assertGreater(large["base_unknown_loss_allowance_pa"], 3)

    def test_no_physical_release_inferred_from_comparison(self):
        for key in ["installed_flow_verified", "thermal_qualified", "fabrication_released"]:
            self.assertFalse(self.result[key])
        rpm = self.result["conditional_rpm_floor"]
        self.assertGreater(rpm["derived_minimum_rpm"], rpm["chosen_pressure_model_floor_rpm"])
        self.assertFalse(rpm["timing_and_speed_to_pressure_model_verified"])

    def test_slow_catalogue_voltage_sensitivity_fan_is_not_excluded_by_guard(self):
        rpm = self.result["conditional_rpm_floor"]
        worst_measured_period = 60 * 125000 * 1.001 / (2 * 5712) + rpm["complete_period_measurement_error_requirement_ticks"]
        self.assertLess(worst_measured_period, rpm["measured_period_max_ticks"])

    def test_coupled_solution_conserves_flow_and_matches_fan_pressure(self):
        for row in self.result["coupled_operating_point_comparisons"]:
            self.assertAlmostEqual(row["total_m3h"], row["interior_m3h"] + row["base_m3h"])
            self.assertAlmostEqual(row["branch_pressure_pa"], row["interior_pressure_coefficient"] * row["interior_m3h"]**2)
            self.assertAlmostEqual(row["branch_pressure_pa"], row["base_pressure_coefficient"] * row["base_m3h"]**2)
            self.assertAlmostEqual(row["fan_pressure_pa"], row["branch_pressure_pa"] + row["common_guard_pressure_pa"])
            self.assertFalse(row["actual_K_values_bounded"])
            self.assertFalse(row["installed_flow_verified"])

    def test_unbounded_channel_losses_do_not_all_become_cooling_passes(self):
        rows = self.result["coupled_operating_point_comparisons"]
        passes = [r["necessary_energy_comparisons"][0]["covers_necessary_energy_transport"] for r in rows]
        self.assertTrue(any(passes))
        self.assertFalse(all(passes))


if __name__ == "__main__":
    unittest.main()
