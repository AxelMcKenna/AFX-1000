"""Actual coverage, not mere candidate existence, defines an admissible return."""
import unittest
from shapely.geometry import Point,LineString,box
from hardware.fabrication.route_nf_surface import candidate_paths
from hardware.cad.two_board_sensor_05.signal_dac.return_paths import v_paths

class ReturnPaths(unittest.TestCase):
    def test_supported_bend_after_simple_family_fails(self):
        start,end=[120.6125,79],[122.4375,79]
        field=LineString([start,end]).buffer(.7).difference(Point(121.6,78.7125).buffer(.6))
        hole=Point(start).buffer(.515)
        def valid(path):
            line=LineString(path)
            return line.length<=2.5 and line.buffer(.1).difference(hole).difference(field).area<1e-6
        self.assertFalse(any(valid(p)for p in candidate_paths(start,end)))
        self.assertTrue(any(valid(p)for p in v_paths(start,end)))
    def test_no_coverage_is_not_accepted(self):
        start,end=[0,0],[1.825,0]
        field=box(-1,-1,3,1).difference(box(.7,-2,1.1,2))
        self.assertFalse(any(LineString(p).buffer(.1).difference(Point(start).buffer(.515)).difference(field).area<1e-6 for p in v_paths(start,end)))

if __name__=='__main__':unittest.main()
