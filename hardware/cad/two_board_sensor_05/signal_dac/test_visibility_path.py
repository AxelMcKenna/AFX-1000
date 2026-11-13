import unittest
from shapely.geometry import box, LineString
from hardware.cad.two_board_sensor_05.signal_dac.visibility_path import visibility_path

class VisibilityPathTests(unittest.TestCase):
    def test_narrow_off_grid_bend_keeps_exact_domain(self):
        domain = box(0, .041, 2, .059).union(box(1.981, .041, 2, 2))
        route = visibility_path(domain, [.1, .05], [1.99, 1.9])
        self.assertIsNotNone(route)
        self.assertTrue(domain.covers(LineString(route)))
        self.assertGreater(len(route), 2)

    def test_full_barrier_rejects(self):
        domain = box(0, 0, 2, 2).difference(box(.9, -.1, 1.1, 2.1))
        self.assertIsNone(visibility_path(domain, [.2, 1], [1.8, 1]))

    def test_node_budget_fails_closed(self):
        with self.assertRaises(AssertionError):
            visibility_path(box(0, 0, 2, 2), [.2, 1], [1.8, 1], max_nodes=2)

if __name__ == '__main__':
    unittest.main()
