import time
import unittest
from unittest.mock import patch
from shapely.geometry import LineString
from hardware.fabrication.digital_continuous_net_route_v2 import route
from tests.tooling import test_digital_continuous_net_route as original_tests

class UpdatedContinuousRouteTests(original_tests.ContinuousNetRouteTests):
    def setUp(self):
        replacement=patch('tests.tooling.test_digital_continuous_net_route.route',route)
        replacement.start();self.addCleanup(replacement.stop)

class ExistingCrossingRouteTests(unittest.TestCase):
    def strict_screen(self):
        s=original_tests.screen({'F.Cu':[],'B.Cu':[]})
        base=s.legal
        s.legal=lambda net,face,points: len(points)>1 and LineString(points).length>=1e-6 and base(net,face,points)
        return s
    def test_existing_start_via_skips_zero_length_front_segment(self):
        s=self.strict_screen();point=(.5,1.5)
        r=route(s,'n','F.Cu',point,{('B.Cu',(3.5,1.5))},time.monotonic()+5,existing_crossings=[(point,['F.Cu','B.Cu'])])
        self.assertIsNotNone(r);self.assertFalse(r['vias']);self.assertEqual([f for f,p in r['runs']],['B.Cu'])
        self.assertTrue(all(s.legal('n',f,p) for f,p in r['runs']))
    def test_existing_target_via_skips_zero_length_back_segment(self):
        s=self.strict_screen();point=(3.5,1.5)
        r=route(s,'n','F.Cu',(.5,1.5),{('B.Cu',point)},time.monotonic()+5,existing_crossings=[(point,['F.Cu','B.Cu'])])
        self.assertIsNotNone(r);self.assertFalse(r['vias']);self.assertEqual([f for f,p in r['runs']],['F.Cu'])
        self.assertTrue(all(s.legal('n',f,p) for f,p in r['runs']))

if __name__=='__main__':unittest.main()
