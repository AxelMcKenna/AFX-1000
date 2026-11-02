"""Exercise a narrow legal exit missed by a coarser routing grid."""
import unittest
from shapely.geometry import box,LineString
from tests.tooling.test_nf_pin_escape_routes import Screen
from hardware.fabrication.nf_connected_fanout_routes import local_grid_path

class FineLocalEscape(unittest.TestCase):
    def test_off_coarse_grid_corridor(self):
        screen=Screen([('other',box(3,-1,5,3.72)),('other',box(3,4.38,5,9))])
        path=local_grid_path(screen,'signal','In2.Cu',(1,4.05),(7,4.05),budget=5000)
        self.assertIsNotNone(path)
        self.assertTrue(screen.legal('signal','In2.Cu',path))
        self.assertAlmostEqual(LineString(path).length,6)
    def test_insufficient_clearance_is_rejected(self):
        screen=Screen([('other',box(3,-1,5,3.8)),('other',box(3,4.3,5,9))])
        self.assertIsNone(local_grid_path(screen,'signal','In2.Cu',(1,4.05),(7,4.05),budget=5000))

if __name__=='__main__':unittest.main()
