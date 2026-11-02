"""Check conservative global route planning around copper and via barriers."""
import time
import unittest
from shapely.geometry import box,LineString,Point
from hardware.fabrication.nf_pin_escape_routes import route_layer
import hardware.fabrication.route_nf_surface as surface

class Screen:
    def __init__(self,obstacles):
        self.outline=box(0,0,8,8)
        self.geometry={'In2.Cu':[(net,shape,.281) for net,shape in obstacles]}
        self.added=[];self.new_vias=[]
    def legal(self,net,layer,points):
        line=LineString(points)
        return self.outline.covers(line) and all(n==net or line.distance(g)>.281 for n,g,d in self.geometry[layer]) and all(n==net or line.distance(Point(p))>.591 for n,p in self.new_vias)

def endpoint(point,group):return dict(point=point,cost=0,runs=[],vias=[],group=group)

class RasterBoundary(unittest.TestCase):
    def setUp(self):self.old=surface.WIDTH;surface.WIDTH=.16
    def tearDown(self):surface.WIDTH=self.old
    def route(self,screen):return route_layer(screen,'signal','In2.Cu',[endpoint((1,4),'left')],[endpoint((7,4),'right')],time.monotonic()+5)
    def test_detours_around_foreign_copper(self):
        screen=Screen([('other',box(3,2,5,6))]);result=self.route(screen)
        self.assertIsNotNone(result)
        for l,p in result['runs']:self.assertTrue(screen.legal('signal',l,p))
        self.assertGreater(LineString(result['runs'][0][1]).length,6)
    def test_full_barrier_does_not_get_crossed(self):
        self.assertIsNone(self.route(Screen([('other',box(3,-1,5,9))])))
    def test_same_net_copper_can_be_joined(self):
        result=self.route(Screen([('signal',box(3,-1,5,9))]));self.assertIsNotNone(result)
        self.assertAlmostEqual(LineString(result['runs'][0][1]).length,6)
    def test_new_through_via_is_obstacle_on_inner_layer(self):
        screen=Screen([]);screen.new_vias=[('other',(4,4))];result=self.route(screen)
        self.assertIsNotNone(result)
        for l,p in result['runs']:self.assertGreater(LineString(p).distance(Point(4,4)),.591)

if __name__=='__main__':unittest.main()
