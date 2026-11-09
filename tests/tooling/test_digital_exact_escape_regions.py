"""Do not discard legal via regions or invent an escape where none exists."""
import unittest
from shapely.geometry import box,Polygon,Point,LineString
from hardware.fabrication.digital_continuous_escape_options_v4 import escape_options
class Screen:
 def __init__(self,blocked=False):
  self.outline=box(0,0,10,10);self.via_outline=box(3.997,3.997,4.003,4.003)
  self.geometry={'F.Cu':[]};self.added=[];self.new_vias=[];self.blocked=blocked
 def obstacles(self,net):return self.via_outline if self.blocked else Polygon()
 def via_legal(self,net,p):return not self.blocked and self.via_outline.covers(Point(p))
 def legal(self,net,face,path):return face=='F.Cu' and self.outline.covers(LineString(path))
class ExactEscapeRegionTests(unittest.TestCase):
 def test_small_legal_region_survives_search(self):
  screen=Screen();rows=escape_options(screen,'signal',{('F.Cu',(2.,4.))},'pad',float('inf'))
  self.assertTrue(rows)
  for r in rows:
   self.assertEqual(len(r['vias']),1);self.assertTrue(screen.via_legal('signal',r['vias'][0]));self.assertEqual(r['runs'][0][0],'F.Cu')
 def test_blocked_region_does_not_produce_via(self):
  self.assertEqual(escape_options(Screen(blocked=True),'signal',{('F.Cu',(2.,4.))},'pad',float('inf')),[])
if __name__=='__main__':unittest.main()
