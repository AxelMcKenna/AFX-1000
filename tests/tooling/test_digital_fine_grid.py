"""A finer grid may recover a real corridor, but cannot cross its obstacles."""
import math
import time
import unittest
from unittest.mock import patch

from shapely.geometry import LineString, Polygon, box
from hardware.fabrication import digital_native_spacing_search_v4 as search
from hardware.fabrication import nf_pin_escape_routes as raster


class CorridorScreen:
    def __init__(self, blocked=False):
        self.outline = box(0, 0, 2, 2)
        self.via_outline = Polygon()
        walls = [box(.7, 0, 1.3, .53), box(.7, .57, 1.3, 2)]
        if blocked:
            walls.append(box(.7, .53, 1.3, .57))
        self.geometry = {'F.Cu': [('foreign', wall, 0.) for wall in walls]}
        self.added = []; self.new_vias = []

    def obstacles(self, net):
        return Polygon()

    def via_legal(self, net, point):
        return False

    def legal(self, net, face, points):
        line = LineString(points)
        return self.outline.covers(line) and all(not line.intersects(g) for _, g, _ in self.geometry[face])


class FineGridTests(unittest.TestCase):
    def route(self, screen, step):
        def portal(point):
            return dict(point=point, layers=['F.Cu'], runs=[], vias=[], cost=0., group=str(point))
        with patch.object(search, 'LAYERS', ('F.Cu',)), patch.object(search, 'STEP', step), \
             patch.object(raster, 'STEP', step), patch.object(raster, 'RASTER_MARGIN', math.sqrt(2)*step/2+.002):
            return search.route_multi(screen, 'signal', [portal((.1, .55))],
                                      {'F.Cu': [portal((1.8, .55))]}, time.monotonic()+10)

    def test_recovers_corridor_without_changing_obstacles(self):
        screen = CorridorScreen()
        self.assertIsNone(self.route(screen, .1))
        result = self.route(screen, .05)
        self.assertIsNotNone(result)
        self.assertEqual(result['vias'], [])
        self.assertTrue(all(screen.legal('signal', face, points) for face, points in result['runs']))

    def test_finer_grid_still_rejects_a_blocked_corridor(self):
        self.assertIsNone(self.route(CorridorScreen(blocked=True), .05))


if __name__ == '__main__':
    unittest.main()
