"""Adverse energy/flow checks for AP01; these are not physical fan tests."""

import math
import unittest

from hardware.cad.a12.thermal.air_path_budget.analyze import (
    compute,
    fan_pressure,
    guard_holes,
    orifice_drop,
    required_flow,
)


class AirBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compute()

    def test_independent_energy_recovery(self):
        # Recover the input heat using mass flow and sensible enthalpy rise.
        q = required_flow(42, 40, 58)
        rho = 101325 / (287.05 * 313.15)
        self.assertAlmostEqual(q / 3600 * rho * 1000 * 18, 42, places=12)

    def test_less_pressure_requires_more_volume(self):
        a = required_flow(42, 40, 58, 101325)
        b = required_flow(42, 40, 58, 80000)
        self.assertAlmostEqual(b / a, 101325 / 80000)
        self.assertGreater(b, a)

    def test_fan_allocation_is_not_second_heat_load(self):
        r = self.result["digital_reserve_partition"]
        self.assertAlmostEqual(
            r["original_w"], r["fan_motor_power_allocation_w"] + r["unassigned_remaining_w"]
        )
        self.assertEqual(r["extra_heat_added_w"], 0)
        self.assertEqual(r["motor_heat_export_credit_w"], 0)

    def test_every_heat_split_conserves_complete_source(self):
        for r in self.result["scenarios"]:
            self.assertAlmostEqual(
                r["internal_air_heat_w"] + r["base_branch_heat_w"],
                self.result["total_source_heat_screen_w"] * r["heat_multiplier"],
            )

    def test_current_pot_with_local_reserve_exceeds_even_nominal_free_air(self):
        rows = [
            r
            for r in self.result["scenarios"]
            if r["pressure_pa"] == 101325
            and r["heat_multiplier"] == 1.2
            and r["assumed_heat_to_base_w"] == 0
            and r["interior_air_ceiling_c"] == 48
        ]
        self.assertEqual(len(rows), 1)
        self.assertGreater(rows[0]["total_minimum_m3h"], 16.4)

    def test_candidate_flow_without_assuming_land_credit(self):
        r = self.result["candidate_air_path"]
        for row in self.result["scenarios"]:
            if (
                row["pressure_pa"] == 101325
                and row["heat_multiplier"] == 1.2
                and row["interior_air_ceiling_c"] == 58
            ):
                self.assertGreaterEqual(r["interior_m3h"], row["internal_air_minimum_m3h"])
                self.assertGreaterEqual(r["base_m3h"], row["base_branch_minimum_m3h"])

    def test_actual_guard_hole_count_and_no_overlap(self):
        points, area = guard_holes()
        self.assertEqual(len(points), 37)
        for i, a in enumerate(points):
            for b in points[i + 1 :]:
                self.assertGreater(math.dist(a, b), 4.2)
        self.assertLess(area, 37 * math.pi * 2.1**2)
        self.assertGreater(area, 510)

    def test_pressure_scales_with_flow_squared_and_area_inverse_squared(self):
        p = orifice_drop(4, 500, 0.75)
        self.assertAlmostEqual(orifice_drop(8, 500, 0.75), 4 * p)
        self.assertAlmostEqual(orifice_drop(4, 1000, 0.75), p / 4)

    def test_restrictive_old_guard_exhausts_selected_pressure_budget(self):
        rows = [
            r
            for r in self.result["pressure_budget_sensitivities"]
            if r["guard"] == "existing_perforated" and r["curve_scale_sensitivity"] == 0.9
        ]
        self.assertEqual(len(rows), 3)
        self.assertTrue(
            all(r["remaining_for_channels_baffles_filters_and_other_losses_pa"] < 0 for r in rows)
        )

    def test_no_extrapolated_fan_pressure_past_free_air(self):
        self.assertIsNone(fan_pressure(15, curve_scale=0.9))
        self.assertAlmostEqual(fan_pressure(14.76, curve_scale=0.9), 0)

    def test_invalid_inputs_rejected(self):
        for args in [(-1, 40, 58), (1, 40, 40), (1, 40, 30), (1, 40, 58, 0)]:
            with self.assertRaises(ValueError):
                required_flow(*args)
        for args in [(1, 0, 0.75), (-1, 500, 0.75), (1, 500, 0), (1, 500, 1.1)]:
            with self.assertRaises(ValueError):
                orifice_drop(*args)

    def test_no_unsupported_qualification(self):
        for key in [
            "installed_airflow_verified",
            "component_temperatures_verified",
            "revised_ports_or_guards_implemented",
            "fabrication_released",
        ]:
            self.assertIs(self.result[key], False)


if __name__ == "__main__":
    unittest.main()
