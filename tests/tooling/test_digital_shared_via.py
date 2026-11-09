"""Common physical via regions must survive sampling without phantom layer access."""
import unittest
from shapely.geometry import Polygon,Point,LineString,box
from hardware.fabrication.digital_latch_supply_repack import shared_via_connection
class Screen:
 def __init__(self,split=False):
  self.outline=box(0,0,10,10);self.via_outline=box(3.997,3.997,4.003,4.003)
  self.geometry={'F.Cu':[],'B.Cu':[]};self.added=[];self.new_vias=[]
  if split:self.geometry={'F.Cu':[('obstacle',box(3,0,10,10),0)],'B.Cu':[('obstacle',box(0,0,5,10),0)]}
 def obstacles(self,net):return Polygon()
 def via_legal(self,net,p):return self.via_outline.covers(Point(p))
 def legal(self,net,face,path):return self.outline.covers(LineString(path)) and all(LineString(path).distance(g)>.0005 for _,g,_ in self.geometry[face])
class SharedViaTests(unittest.TestCase):
 def args(self):return dict(net='signal',pad=dict(kind='PAD',net='signal',position_mm=[2.,4.],layers={'F.Cu':[1]}),targets=[dict(kind='PAD',net='signal',position_mm=[6.,4.],layers={'B.Cu':[1]})],deadline=float('inf'))
 def test_tiny_legal_common_region_uses_one_real_via(self):
  screen=Screen();r=shared_via_connection(screen,**self.args());self.assertIsNotNone(r);self.assertEqual(len(r['vias']),1)
  self.assertTrue(screen.via_legal('signal',r['vias'][0]));self.assertEqual({f for f,_ in r['runs']},{'F.Cu','B.Cu'})
  self.assertTrue(all(tuple(path[-1])==tuple(r['vias'][0]) for _,path in r['runs']))
 def test_disjoint_surface_regions_do_not_connect(self):self.assertIsNone(shared_via_connection(Screen(split=True),**self.args()))
if __name__=='__main__':unittest.main()
