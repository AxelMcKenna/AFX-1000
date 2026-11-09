"""Independent analytical and topology checks for the inlet resistance model."""
import unittest

from shapely.affinity import rotate
from shapely.geometry import box
from shapely.ops import unary_union

from hardware.fabrication.sheet_resistance import solve_sheet


class SheetResistanceTests(unittest.TestCase):
    def test_uniform_rectangle_analytical_grid_and_continuum(self):
        # Conservative raster at h=.1 gives 198 x 38 nodes. With one contacted
        # column at either end, 197 resistors in series / 38 identical rows.
        result = solve_sheet(box(0, 0, 20, 4), {'s': box(0, 0, .2, 4)},
                             {'t': box(19.8, 0, 20, 4)}, .1)
        self.assertAlmostEqual(result['resistance_squares'], 197/38, places=8)
        self.assertLess(abs(result['resistance_squares']/5-1), .04)

    def test_parallel_separate_sheets_add_conductance(self):
        a, b = box(0, 0, 20, 4), box(0, 6, 20, 10)
        one = solve_sheet(a, {'s': box(0, 0, .2, 4)}, {'t': box(19.8, 0, 20, 4)}, .1)
        two = solve_sheet(unary_union([a, b]),
                          {'s1': box(0, 0, .2, 4), 's2': box(0, 6, .2, 10)},
                          {'t1': box(19.8, 0, 20, 4), 't2': box(19.8, 6, 20, 10)}, .1)
        self.assertAlmostEqual(two['resistance_squares'], one['resistance_squares']/2, places=8)
        self.assertAlmostEqual(two['ports']['s1']['fraction'], .5, places=8)

    def test_rotation_and_floating_copper(self):
        copper = box(0, 0, 12, 4).difference(box(5, 1, 7, 3))
        src, dst = box(0, 0, .3, 4), box(11.7, 0, 12, 4)
        a = solve_sheet(copper, {'s': src}, {'t': dst}, .1)
        b = solve_sheet(unary_union([rotate(copper, 90, origin=(0, 0)), box(10, 10, 12, 12)]),
                        {'s': rotate(src, 90, origin=(0, 0))},
                        {'t': rotate(dst, 90, origin=(0, 0))}, .1)
        self.assertAlmostEqual(a['resistance_squares'], b['resistance_squares'], places=8)
        self.assertGreater(b['discarded_zero_current_nodes'], 0)

    def test_open_circuit_and_overlapping_contacts_rejected(self):
        with self.assertRaisesRegex(ValueError, 'No copper path'):
            solve_sheet(unary_union([box(0, 0, 4, 4), box(6, 0, 10, 4)]),
                        {'s': box(0, 0, 1, 4)}, {'t': box(9, 0, 10, 4)}, .1)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            solve_sheet(box(0, 0, 4, 4), {'s': box(0, 0, 3, 4)}, {'t': box(2, 0, 4, 4)}, .1)


if __name__ == '__main__':
    unittest.main()
