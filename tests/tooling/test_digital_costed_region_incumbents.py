import time
import unittest
from unittest.mock import patch
from shapely.geometry import box, GeometryCollection
from hardware.fabrication.digital_costed_region_route_v2 import route


class EmptyScreen:
    def __init__(self):
        self.outline = self.via_outline = box(0, 0, 20, 20)
        self.geometry = {'F.Cu': []}
        self.added, self.new_vias = [], []
    def obstacles(self, net):
        return GeometryCollection()
    def legal(self, net, face, points):
        return True
    def via_legal(self, net, point):
        return True


class IncumbentTests(unittest.TestCase):
    def test_completed_route_survives_refinement_budget(self):
        result = route(EmptyScreen(), 'N', [('F.Cu',(2,2))], [('F.Cu',(12,2))], time.monotonic()+5, max_refinements=1)
        self.assertIsNotNone(result['route'])
        self.assertEqual(result['complete_incumbents'][0]['planar_length_mm'], 10)
        self.assertFalse(result['terminated_on_fully_measured_shortest_sampled_path'])

    def test_failed_planar_edge_cannot_become_incumbent(self):
        with patch('hardware.fabrication.digital_costed_region_route_v2.polygon_route', return_value=None):
            result = route(EmptyScreen(), 'N', [('F.Cu',(2,2))], [('F.Cu',(12,2))], time.monotonic()+5, max_refinements=1)
        self.assertIsNone(result['route'])
        self.assertEqual(result['complete_incumbents'], [])

    def test_disconnected_regions_cannot_be_joined_by_cost_bound(self):
        screen = EmptyScreen()
        screen.geometry['F.Cu'] = [('foreign', box(9,-1,11,21), .3)]
        result = route(screen, 'N', [('F.Cu',(2,2))], [('F.Cu',(18,2))], time.monotonic()+5, max_refinements=1)
        self.assertIsNone(result['route'])


if __name__ == '__main__':
    unittest.main()
