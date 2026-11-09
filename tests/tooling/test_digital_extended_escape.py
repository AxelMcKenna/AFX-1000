"""A wider search must recover distant vias without crossing blocked copper regions."""
import unittest
from shapely.geometry import Point,LineString,Polygon,box
from hardware.fabrication.digital_continuous_escape_options_v5 import escape_options

class Screen:
    def __init__(self,split=False,blocked=False):
        self.outline=box(0,0,20,10);self.via_outline=box(13.997,3.997,14.003,4.003)
        self.geometry={'F.Cu':[('foreign',box(6,0,7,10),0)] if split else []}
        self.added=[];self.new_vias=[];self.blocked=blocked
    def obstacles(self,net):return self.via_outline if self.blocked else Polygon()
    def via_legal(self,net,p):return not self.blocked and self.via_outline.covers(Point(p))
    def legal(self,net,face,path):
        line=LineString(path)
        return face=='F.Cu' and self.outline.covers(line) and all(line.distance(g)>.0005 for _,g,_ in self.geometry[face])

class ExtendedEscapeTests(unittest.TestCase):
    def find(self,screen,radius=8):
        return escape_options(screen,'signal',{('F.Cu',(2.,4.))},'pad',float('inf'),radius_mm=radius)
    def test_expansion_recovers_distant_real_via(self):
        screen=Screen();self.assertEqual(self.find(screen),[])
        rows=self.find(screen,16);self.assertTrue(rows)
        for row in rows:
            self.assertEqual(len(row['vias']),1)
            self.assertTrue(screen.via_legal('signal',row['vias'][0]))
            self.assertTrue(all(screen.legal('signal',f,p) for f,p in row['runs']))
    def test_expansion_does_not_cross_disconnected_copper_regions(self):
        self.assertEqual(self.find(Screen(split=True),16),[])
    def test_expansion_does_not_ignore_drill_obstacles(self):
        self.assertEqual(self.find(Screen(blocked=True),16),[])

if __name__=='__main__':unittest.main()
