"""Off-grid layer changes require a real legal via and legal surface leads."""
import time
import unittest
from unittest.mock import patch
from shapely.geometry import Point, LineString, Polygon, box
from hardware.fabrication import digital_native_spacing_search_v4 as search


class Screen:
    def __init__(self, blocked=False, split=False):
        self.outline = box(0, 0, 2, 2)
        self.via_outline = box(.547, .547, .553, .553)
        self.geometry = {'F.Cu': [('foreign', box(.3, 0, .4, 2), 0)] if split else [], 'In5.Cu': []}
        self.added = []; self.new_vias = []; self.blocked = blocked

    def obstacles(self, net):
        return self.via_outline if self.blocked else Polygon()

    def via_legal(self, net, point):
        return not self.blocked and self.via_outline.covers(Point(point))

    def legal(self, net, face, points):
        line = LineString(points)
        return self.outline.covers(line) and all(not line.intersects(g) for _, g, _ in self.geometry[face])


class BridgeTests(unittest.TestCase):
    def route(self, screen, end_face='In5.Cu'):
        def portal(point, face):
            return dict(point=point, layers=[face], runs=[], vias=[], cost=0., group=face)
        with patch.object(search, 'LAYERS', ('F.Cu', 'In5.Cu')), patch.object(search, 'WIDTH', .2):
            return search.route_multi(screen, 'signal', [portal((.1, .1), 'F.Cu')],
                                      {end_face: [portal((1.8, 1.8), end_face)]}, time.monotonic()+10)

    def test_uses_actual_off_grid_via(self):
        screen = Screen(); result = self.route(screen)
        self.assertIsNotNone(result)
        self.assertEqual(result['vias'], [(.55, .55)])
        self.assertTrue(all(screen.legal('signal', face, points) for face, points in result['runs']))
        self.assertEqual({face for face, _ in result['runs']}, {'F.Cu', 'In5.Cu'})
        for _, points in result['runs']:
            self.assertIn((.55, .55), points)

    def test_blocked_via_cannot_change_layers(self):
        self.assertIsNone(self.route(Screen(blocked=True)))

    def test_disconnected_face_cannot_reach_via(self):
        self.assertIsNone(self.route(Screen(split=True)))

    def test_same_face_does_not_require_a_via(self):
        result = self.route(Screen(blocked=True), 'F.Cu')
        self.assertIsNotNone(result)
        self.assertEqual(result['vias'], [])


if __name__ == '__main__':
    unittest.main()
