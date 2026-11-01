import json
import unittest

from .analyze import ROOT, compute, nominal


class Curve(unittest.TestCase):
    def setUp(self):
        self.points = json.loads((ROOT / "nominal-203AT-ohm.json").read_text())["points_temp_c_resistance_ohm"]

    def test_published_points_and_units(self):
        self.assertEqual(dict(self.points)[60], 4943)
        self.assertEqual(dict(self.points)[25], 20000)
        for t, resistance in self.points:
            self.assertAlmostEqual(nominal(t, self.points), resistance, places=7)

    def test_nominal_interpolation_is_monotonic_without_extrapolation(self):
        previous = nominal(-50, self.points)
        for half_degrees in range(-99, 221):
            current = nominal(half_degrees / 2, self.points)
            self.assertLess(current, previous)
            previous = current
        for t in [-50.01, 110.01]:
            with self.assertRaises(ValueError):
                nominal(t, self.points)

    def test_beta_discrepancy_is_retained(self):
        row = next(r for r in compute()["nominal_point_comparisons"] if r["temp_c"] == 60)
        self.assertLess(row["beta_relative_error_fraction"], -.016)
        self.assertGreater(row["beta_relative_error_fraction"], -.017)

    def test_sparse_table_does_not_become_a_guaranteed_shutdown(self):
        result = compute()
        self.assertFalse(result["interpolation_error_bounded"])
        self.assertFalse(result["local_manufacturing_RT_tolerance_bounded"])
        self.assertIsNone(result["guaranteed_sensor_trip_interval_c"])
        self.assertIsNone(result["assembled_shutdown_ceiling_c"])
        self.assertFalse(result["thermal_qualified"])


if __name__ == "__main__":
    unittest.main()
