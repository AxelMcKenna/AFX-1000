"""Reject origin, unit, count and profile mistakes in the E13 export reader."""

import unittest

from hardware.fabrication.inspect_rail_monitor_outputs import match_holes, parse_drills, profile_edges

DRILL = "M48\n; FORMAT={-:-/ absolute / metric / decimal}\nFMAT,2\nMETRIC\nT1C0.300\n%\nG90\nG05\nT1\nX1.0Y-2.0\nT0\nM30\n"
PROFILE = "%FSLAX46Y46*%\n%MOMM*%\nG01*\nX0Y0D02*\nX80000000Y0D01*\nX80000000Y-70000000D01*\nX0Y-70000000D01*\nX0Y0D01*\nM02*\n"


class ManufacturingCoordinates(unittest.TestCase):
    def test_decimal_mm_drill_and_explicit_source_axis_convention(self):
        actual = parse_drills(DRILL)
        self.assertEqual(actual, [(0.3, 1.0, -2.0)])
        self.assertEqual(match_holes(actual, [(0.3, 1.0, -2.0)]), 0)
        with self.assertRaises(ValueError):
            match_holes(actual, [(0.3, 1.0, 2.0)])

    def test_coordinate_rounding_is_bounded_and_does_not_hide_origin_errors(self):
        self.assertAlmostEqual(match_holes([(0.3, 1.0, -2.0)], [(0.3, 1.0005, -1.9995)]), 0.0005)
        with self.assertRaises(ValueError):
            match_holes([(0.3, 1.0, -2.0)], [(0.3, 1.0006, -2.0)])

    def test_wrong_drill_size_or_missing_duplicate_holes_fail(self):
        for actual, expected in [([(0.4, 1, -2)], [(0.3, 1, -2)]),
                                 ([], [(0.3, 1, -2)]),
                                 ([(0.3, 1, -2)]*2, [(0.3, 1, -2)])]:
            with self.assertRaises(ValueError):
                match_holes(actual, expected)

    def test_units_incremental_moves_and_slots_are_never_silently_accepted(self):
        for text in [DRILL.replace("METRIC", "INCH"), DRILL.replace("G90", "G91"),
                     DRILL.replace("G05", "G00X1Y2"), DRILL.replace("X1.0Y-2.0", "X1.0G85X2.0Y2.0")]:
            with self.assertRaises(ValueError):
                parse_drills(text)

    def test_profile_preserves_80_by_70_mm_centerline_and_rejects_unit_changes(self):
        edges = profile_edges(PROFILE)
        points = {point for segment in edges for point in segment}
        self.assertEqual(points, {(0, 0), (80, 0), (80, 70), (0, 70)})
        self.assertEqual(sum(edges.values()), 4)
        with self.assertRaises(ValueError):
            profile_edges(PROFILE.replace("MOMM", "MOIN"))


if __name__ == "__main__":
    unittest.main()
