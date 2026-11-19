"""Regression checks for native zone boundary comparisons."""

import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec("pcbnew"), "KiCad Python bindings required")
class FilledBoundaryTests(unittest.TestCase):
    def polygon(self, points, hole=()):
        import pcbnew

        polygon = pcbnew.SHAPE_POLY_SET()
        polygon.NewOutline()
        for x, y in points:
            polygon.Append(x, y)
        if hole:
            polygon.NewHole()
            for x, y in hole:
                polygon.Append(x, y, 0, 0)
        return polygon

    def test_reordered_and_subdivided_edge(self):
        from hardware.fabrication.verify_power_surface_refill import same_filled_area

        original = self.polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
        reordered = self.polygon([(10000, 10000), (0, 10000), (0, 0), (4000, 0), (10000, 0)])
        self.assertTrue(same_filled_area(original, reordered))

    def test_one_nanometer_and_hole_changes(self):
        from hardware.fabrication.verify_power_surface_refill import same_filled_area

        square = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        original = self.polygon(square)
        clipped = self.polygon([square[0], square[1], (9999, 10000), square[3]])
        pierced = self.polygon(square, [(2000, 2000), (2000, 3000), (3000, 3000), (3000, 2000)])
        self.assertFalse(same_filled_area(original, clipped))
        self.assertFalse(same_filled_area(original, pierced))
