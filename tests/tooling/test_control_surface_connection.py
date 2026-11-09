"""Find connected surface copper without introducing an unnecessary drilled transition."""
import time,unittest
from shapely.geometry import box,Point,LineString
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_control_pulldowns_repack_v5 import surface_connection
class SurfaceConnectionTests(unittest.TestCase):
 def setUp(self):
  self.old=(surface.WIDTH,layers.WIDTH,surface.MARGIN,surface.SIGNAL_LAYERS)
  surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 def tearDown(self):surface.WIDTH,layers.WIDTH,surface.MARGIN,surface.SIGNAL_LAYERS=self.old
 def screen(self,obstacle):
  poly=lambda g:[dict(outer=list(g.exterior.coords),holes=[])]
  objects=[dict(uuid='foreign',net='B',kind='PAD',position_mm=[5,5],drill_mm=[0,0],layers={'B.Cu':poly(obstacle)})]
  return DigitalViaScreen(dict(objects=objects,zones=[],outline=poly(box(0,0,10,10)),copper_layers=list(surface.SIGNAL_LAYERS)),signal_layers=surface.SIGNAL_LAYERS)
 def test_surface_detour_reaches_existing_copper(self):
  obstacle=box(4,3,6,7);s=self.screen(obstacle)
  path=surface_connection(s,'A',[2,5],[Point(8,5)],time.monotonic()+5)
  self.assertIsNotNone(path);self.assertTrue(s.legal('A','B.Cu',path));self.assertGreater(LineString(path).distance(obstacle),.31)
  self.assertEqual(s.added,[]);self.assertEqual(s.new_vias,[])
 def test_disconnected_region_is_not_a_connection(self):
  s=self.screen(box(4,0,6,10))
  self.assertIsNone(surface_connection(s,'A',[2,5],[Point(8,5)],time.monotonic()+5))
if __name__=='__main__':unittest.main()
