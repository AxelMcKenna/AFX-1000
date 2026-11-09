"""Geometry regressions for small via regions and blocked surface escapes."""
import math,time,unittest
from shapely.geometry import box,LineString,Point
from shapely.ops import unary_union
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options
from hardware.fabrication.digital_visibility_escape import route


def polygons(g):return [dict(outer=list(g.exterior.coords),holes=[])]


class ContinuousEscapeTests(unittest.TestCase):
    def setUp(self):
        self.old=(surface.WIDTH,layers.WIDTH,surface.MARGIN,surface.SIGNAL_LAYERS)
        surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01
        surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
    def tearDown(self):surface.WIDTH,layers.WIDTH,surface.MARGIN,surface.SIGNAL_LAYERS=self.old
    def screen(self,obstacle=None):
        objects=[] if obstacle is None else [dict(uuid='foreign',net='B',kind='PAD',position_mm=[5,5],drill_mm=[0,0],layers={'F.Cu':polygons(obstacle)})]
        return DigitalViaScreen(dict(objects=objects,zones=[],outline=polygons(box(0,0,10,10)),copper_layers=list(surface.SIGNAL_LAYERS)),signal_layers=surface.SIGNAL_LAYERS)
    def test_sub_grid_via_region_is_found_without_changing_geometry(self):
        s=self.screen();s.via_outline=box(5.10,5.10,5.16,5.16)
        self.assertFalse(any(s.via_legal('A',(3+x*.25,5+y*.25)) for x in range(20) for y in range(20)))
        options=escape_options(s,'A',{('F.Cu',(3.,5.))},'source',time.monotonic()+3)
        self.assertTrue(options)
        for option in options:
            self.assertTrue(s.via_legal('A',option['point']))
            self.assertTrue(all(s.legal('A',face,path) for face,path in option['runs']))
        self.assertEqual(s.added,[]);self.assertEqual(s.new_vias,[])
    def test_legal_via_in_separate_surface_region_is_not_an_escape(self):
        s=self.screen(box(4.5,0,5.5,10));s.via_outline=box(7,4,8,6)
        self.assertTrue(s.via_legal('A',(7.5,5)))
        self.assertEqual(escape_options(s,'A',{('F.Cu',(2.,5.))},'source',time.monotonic()+3),[])
    def test_other_layer_contact_requires_a_real_via(self):
        s=self.screen()
        options=escape_options(s,'A',{('In5.Cu',(3.,5.))},'source',time.monotonic()+3,target_layer='In3.Cu')
        self.assertTrue(options)
        self.assertTrue(all(o['layers']==['In3.Cu'] and o['vias'] for o in options))
        self.assertTrue(any(o['point']==(3.,5.) and not o['runs'] for o in options))
    def test_visibility_detour_retains_exact_copper_clearance(self):
        obstacle=box(4,3,6,7);s=self.screen(obstacle)
        free=s.outline.difference(unary_union([g.buffer(d+.0005,quad_segs=32) for n,g,d in s.geometry['F.Cu'] if n!='A']))
        self.assertFalse(s.legal('A','F.Cu',[(2,5),(8,5)]))
        result=route(s,'A','F.Cu',(2,5),(8,5),free,time.monotonic()+5)
        self.assertIsNotNone(result);self.assertTrue(s.legal('A','F.Cu',result))
        self.assertGreater(LineString(result).distance(obstacle),.31)
        self.assertGreater(LineString(result).length,6)
if __name__=='__main__':unittest.main()
