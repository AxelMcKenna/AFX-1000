import unittest
from shapely.geometry import box, LineString
from hardware.cad.two_board_sensor_05.signal_dac.bounded_path import bounded_path

class BoundedPathTests(unittest.TestCase):
    def test_detour_uses_declared_bounds(self):
        area=box(0,0,4,4).difference(box(1.8,0,2.2,3.3))
        result=bounded_path(lambda p: area.covers(LineString(p)),[1,1],[3,1],area.bounds)
        self.assertEqual(result['reason'],'connected')
        self.assertTrue(area.covers(LineString(result['path'])))
        self.assertGreaterEqual(max(p[1]for p in result['path']),3.3)
    def test_budget_is_explicit_failure(self):
        result=bounded_path(lambda p:True,[0,0],[3,3],(-1,-1,4,4),max_nodes=1)
        self.assertEqual(result['reason'],'node_budget')
        self.assertIsNone(result['path'])
    def test_barrier_is_disconnected(self):
        area=box(0,0,4,4).difference(box(1.8,-1,2.2,5))
        result=bounded_path(lambda p:area.covers(LineString(p)),[1,1],[3,1],area.bounds)
        self.assertEqual(result['reason'],'disconnected_grid')
if __name__=='__main__':unittest.main()
