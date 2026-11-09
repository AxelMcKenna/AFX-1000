import time
import unittest

from shapely.geometry import LineString, box
from shapely.ops import unary_union
from hardware.fabrication.digital_polygon_path import route


class Screen:
    def __init__(self, free):
        self.free = free

    def legal(self, net, face, points):
        return self.free.covers(LineString(points))


class PolygonPathTests(unittest.TestCase):
    def test_narrow_bent_corridor_avoids_grid_dependence(self):
        free = unary_union([box(0, .53, 1.1, .57), box(1.06, .53, 1.1, 1.57), box(1.06, 1.53, 2, 1.57)])
        path = route(Screen(free), 'n', 'F.Cu', (.1, .55), (1.9, 1.55), free, time.monotonic()+5)
        self.assertIsNotNone(path)
        self.assertTrue(free.covers(LineString(path)))

    def test_hole_is_not_crossed(self):
        free = box(0, 0, 4, 4).difference(box(1, 1, 3, 3))
        path = route(Screen(free), 'n', 'F.Cu', (.5, 2), (3.5, 2), free, time.monotonic()+5)
        self.assertIsNotNone(path)
        self.assertTrue(free.covers(LineString(path)))

    def test_disconnected_regions_fail(self):
        free = unary_union([box(0, 0, 1, 1), box(2, 0, 3, 1)])
        self.assertIsNone(route(Screen(free), 'n', 'F.Cu', (.5, .5), (2.5, .5), free, time.monotonic()+5))

    def test_independent_screen_can_reject_polygon_path(self):
        free = box(0, 0, 3, 1)
        screen = Screen(free.difference(box(1, 0, 2, 1)))
        self.assertIsNone(route(screen, 'n', 'F.Cu', (.5, .5), (2.5, .5), free, time.monotonic()+5))


if __name__ == '__main__':
    unittest.main()
