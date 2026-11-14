"""Analytical current-flow and conservation checks for regional sheet probes."""
import unittest

from shapely.affinity import rotate
from shapely.geometry import Point, box
from hardware.fabrication.sheet_resistance import solve_sheet as original_solver
from hardware.fabrication.sheet_resistance_with_probes import solve_sheet


class SheetProbeTests(unittest.TestCase):
    def test_uniform_strip_current_and_power(self):
        copper = box(0, 0, 20, 4)
        source, sink = {'s': box(0, 0, .2, 4)}, {'t': box(19.8, 0, 20, 4)}
        result = solve_sheet(copper, source, sink, .1,
                             probe_regions={'middle': box(8, 0, 12, 4), 'all': copper})
        # There are 38 retained parallel rows; each carries 1/38 A through
        # a 0.1 mm cell face, independent of the strip's length.
        p = result['probes']['middle']
        self.assertAlmostEqual(p['maximum_horizontal_A_per_mm_per_terminal_A'], 1/3.8, places=9)
        self.assertLess(p['maximum_vertical_A_per_mm_per_terminal_A'], 1e-10)
        self.assertAlmostEqual(result['resistance_squares'], 197/38, places=8)
        self.assertAlmostEqual(result['probes']['all']['regional_dissipation_squares_at_terminal_A1'],
                               result['resistance_squares'], places=8)
        self.assertEqual(result['resistance_squares'], original_solver(copper, source, sink, .1)['resistance_squares'])

    def test_hole_increases_resistance_and_local_crowding(self):
        copper, probe = box(0, 0, 12, 4), Point(6, 2).buffer(1.5)
        source, sink = {'s': box(0, 0, .3, 4)}, {'t': box(11.7, 0, 12, 4)}
        before = solve_sheet(copper, source, sink, .1, probe_regions={'local': probe})
        after = solve_sheet(copper.difference(Point(6, 2).buffer(.5)), source, sink, .1,
                            probe_regions={'local': probe})
        self.assertGreater(after['resistance_squares'], before['resistance_squares'])
        metric = 'maximum_edge_normal_A_per_mm_per_terminal_A'
        self.assertGreater(after['probes']['local'][metric], before['probes']['local'][metric])
        rotated = solve_sheet(rotate(copper.difference(Point(6, 2).buffer(.5)), 90, origin=(0, 0)),
                              {'s': rotate(source['s'], 90, origin=(0, 0))},
                              {'t': rotate(sink['t'], 90, origin=(0, 0))}, .1,
                              probe_regions={'local': rotate(probe, 90, origin=(0, 0))})
        self.assertAlmostEqual(rotated['resistance_squares'], after['resistance_squares'], places=8)
        self.assertAlmostEqual(rotated['probes']['local'][metric], after['probes']['local'][metric], places=8)

    def test_empty_probe_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no conducting mesh edges'):
            solve_sheet(box(0, 0, 4, 2), {'s': box(0, 0, .3, 2)}, {'t': box(3.7, 0, 4, 2)}, .1,
                        probe_regions={'outside': box(10, 10, 11, 11)})


if __name__ == '__main__':
    unittest.main()
