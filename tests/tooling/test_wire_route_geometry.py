"""Physical geometry checks for proposed continuous wire paths."""

import math
import unittest

from hardware.cad.a12.harness.route_geometry import Route


class WireCurveGeometry(unittest.TestCase):
    def test_vertical_quarter_circle_has_true_radius_and_expected_horizontal_tangent(self):
        r = Route([0, 0, 0], [0, 0, 1], 9.6393)
        r.arc(10, [0, 1, 0], math.pi / 2)
        points, bound = r.samples(0.05)
        for x, y, z in points:
            self.assertAlmostEqual((x - 10) ** 2 + z * z, 100)
            self.assertEqual(y, 0)
        self.assertLess(math.dist(r.point, [10, 0, 10]), 1e-12)
        self.assertLess(math.dist(r.tangent, [1, 0, 0]), 1e-12)
        self.assertAlmostEqual(bound["exact_centerline_length_mm"], 5 * math.pi)
        self.assertLessEqual(max(math.dist(a, b) for a, b in zip(points, points[1:])), 0.05)
        self.assertLess(bound["maximum_native_chord_error_bound_mm"], 0.005)

    def test_s_lift_restores_tangent_and_has_the_analytic_rise(self):
        r = Route([0, 0, 0], [-1, 0, 0], 9.6393)
        r.lift(7.2, 10)
        self.assertAlmostEqual(r.point[2], 7.2)
        self.assertAlmostEqual(r.point[0], -2 * math.sqrt(10 * 7.2 - 7.2**2 / 4))
        self.assertLess(math.dist(r.tangent, [-1, 0, 0]), 1e-12)
        self.assertEqual(len(r.pieces), 2)
        self.assertTrue(all(p["radius_mm"] == 10 for p in r.pieces))

    def test_tight_or_nonperpendicular_bend_is_rejected_before_mutating_route(self):
        r = Route([0, 0, 0], [0, 0, 1], 9.6393)
        with self.assertRaises(AssertionError):
            r.arc(9.5, [0, 1, 0], math.pi / 2)
        with self.assertRaises(AssertionError):
            r.arc(10, [0, 0, 1], math.pi / 2)
        self.assertEqual(r.pieces, [])
        self.assertEqual(r.point, [0, 0, 0])

    def test_straight_route_has_no_fictitious_arc_radius(self):
        r = Route([0, 0, 0], [1, 0, 0], 9.6393)
        r.line(10)
        points, bound = r.samples(0.1)
        self.assertEqual(points[-1], [10, 0, 0])
        self.assertIsNone(bound["minimum_arc_radius_mm"])
        self.assertEqual(bound["exact_centerline_length_mm"], 10)


if __name__ == "__main__":
    unittest.main()
