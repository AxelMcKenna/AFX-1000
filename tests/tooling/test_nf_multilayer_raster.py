"""Verify layer changes obey trace, hole and reserved-layer boundaries."""
import math,time,unittest
from shapely.geometry import box,LineString,Point
from hardware.fabrication.nf_multilayer_raster import LAYERS,route_multi
import hardware.fabrication.route_nf_surface as surface

class LayerBoard:
    def __init__(self,all_layers=False,via_keepout=False):
        self.outline=box(0,0,10,8);self.via_outline=self.outline.buffer(-.31)
        wall=box(4,-1,6,9)
        self.geometry={l:([('other',wall,.281)] if all_layers or l=='In2.Cu' else []) for l in LAYERS}
        self.via_geometry=[('other',wall,'PCB_TRACK')]
        if via_keepout:self.via_geometry.append((None,self.outline,'KEEPOUT'))
        self.vias=[];self.new_vias=[];self.added=[]
    def legal(self,net,layer,points):
        line=LineString(points)
        return self.outline.covers(line) and all(n==net or line.distance(g)>.281 for n,g,d in self.geometry[layer])
    def via_legal(self,net,p):
        point=Point(p)
        return self.via_outline.covers(point) and all(point.distance(g)>(.31 if k=='KEEPOUT' else .51) for n,g,k in self.via_geometry)

class LayerChanges(unittest.TestCase):
    def setUp(self):self.old=surface.WIDTH;surface.WIDTH=.16
    def tearDown(self):surface.WIDTH=self.old
    def run_route(self,board):
        a=dict(point=(1,4),runs=[],vias=[],cost=0,group='a',layers=['In2.Cu'])
        b=dict(point=(9,4),runs=[],vias=[],cost=0,group='b')
        return route_multi(board,'signal',[a],{'In2.Cu':[b]},time.monotonic()+5,max_visits=100000)
    def test_crosses_layer_barrier_using_two_legal_vias(self):
        board=LayerBoard();r=self.run_route(board);self.assertIsNotNone(r)
        self.assertEqual(r['layer_transition_count'],2);self.assertEqual(len(r['vias']),2)
        for l,p in r['runs']:self.assertIn(l,LAYERS);self.assertTrue(board.legal('signal',l,p))
        for p in r['vias']:self.assertTrue(board.via_legal('signal',p))
        self.assertGreater(math.dist(*r['vias']),.86)
    def test_all_layer_barrier_cannot_be_crossed(self):self.assertIsNone(self.run_route(LayerBoard(all_layers=True)))
    def test_via_keepout_prevents_layer_changes(self):self.assertIsNone(self.run_route(LayerBoard(via_keepout=True)))

if __name__=='__main__':unittest.main()
