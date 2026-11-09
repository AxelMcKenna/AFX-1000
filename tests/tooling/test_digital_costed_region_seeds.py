import time
import unittest
from shapely.geometry import box
from hardware.fabrication.digital_costed_region_route_v3 import route
from tests.tooling.test_digital_costed_region_incumbents import EmptyScreen


class SeedTests(unittest.TestCase):
    def test_seed_inside_via_obstacle_is_rejected(self):
        screen=EmptyScreen()
        screen.obstacles=lambda net: box(4,4,6,6)
        result=route(screen,'N',[('F.Cu',(2,2))],[('F.Cu',(12,2))],time.monotonic()+5,max_refinements=1,via_candidates=[(5,5)])
        self.assertEqual(result['screened_input_via_positions'],[])
        self.assertEqual(result['route']['vias'],[])

    def test_legal_seed_is_available_but_not_installed_unnecessarily(self):
        result=route(EmptyScreen(),'N',[('F.Cu',(2,2))],[('F.Cu',(12,2))],time.monotonic()+5,max_refinements=1,via_candidates=[(5,5)])
        self.assertEqual(result['screened_input_via_positions'],[(5.,5.)])
        self.assertEqual(result['route']['vias'],[])


if __name__=='__main__':
    unittest.main()
