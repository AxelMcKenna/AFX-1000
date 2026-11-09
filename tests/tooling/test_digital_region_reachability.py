"""Polygon connectivity distinguishes blocked regions from missed grid corridors."""
import unittest
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from hardware.fabrication.digital_region_reachability import reachability


class Screen:
    def __init__(self, geometry, via_area=None):
        self.outline = box(0, 0, 2, 2)
        self.via_outline = Polygon() if via_area is None else via_area
        self.geometry = {face: [('foreign', g, 0.) for g in walls] for face, walls in geometry.items()}
        self.added = []; self.new_vias = []

    def obstacles(self, net):
        return Polygon()

    def via_legal(self, net, xy):
        return self.via_outline.covers(Point(xy))


class RegionReachabilityTests(unittest.TestCase):
    def check(self, screen, start=(.1, 1.), end=(1.8, 1.)):
        return reachability(screen, 'signal', [('F.Cu', start)], [('F.Cu', end)], tuple(screen.geometry))

    def test_narrow_continuous_corridor_is_connected(self):
        screen = Screen({'F.Cu': [box(.7, 0, 1.3, .53), box(.7, .57, 1.3, 2)]})
        self.assertTrue(self.check(screen, (.1, .55), (1.8, .55))['connected'])

    def test_full_wall_is_disconnected(self):
        self.assertFalse(self.check(Screen({'F.Cu': [box(.9, 0, 1.1, 2)]}))['connected'])

    def test_another_layer_requires_real_via_access(self):
        screen = Screen({'F.Cu': [box(.9, 0, 1.1, 2)], 'In5.Cu': []})
        self.assertFalse(self.check(screen)['connected'])

    def test_two_via_regions_allow_a_real_layer_detour(self):
        vias = unary_union([box(.4, .4, .6, .6), box(1.4, .4, 1.6, .6)])
        screen = Screen({'F.Cu': [box(.9, 0, 1.1, 2)], 'In5.Cu': []}, vias)
        result = self.check(screen)
        self.assertTrue(result['connected'])
        self.assertEqual(len(result['component_witness']), 2)

    def test_track_only_restriction_splits_a_via_area(self):
        screen = Screen({'F.Cu': [box(.9, 0, 1.1, 2)], 'In5.Cu': []}, box(.1, .1, 1.9, 1.9))
        result = self.check(screen)
        self.assertTrue(result['connected'])
        self.assertEqual(len(result['conventional_via_pair_regions']), 2)
        self.assertTrue(result['all_via_areas_proven_inside_surface_components'])


if __name__ == '__main__':
    unittest.main()
