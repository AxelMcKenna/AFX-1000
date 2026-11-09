import unittest
from types import SimpleNamespace

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from hardware.fabrication.digital_region_point_access import reachability


def screen(layers, vias=None):
    area = Polygon() if vias is None else vias
    return SimpleNamespace(outline=box(0,0,3,2),via_outline=area,
                           geometry={f:[('foreign',g,0) for g in gs] for f,gs in layers.items()},
                           added=[],new_vias=[],obstacles=lambda net: Polygon(),
                           via_legal=lambda net,p: area.covers(Point(p)))


class RegionPointTests(unittest.TestCase):
    def test_does_not_stop_at_source_target_identity(self):
        s = screen({'F.Cu':[box(1,0,1.2,2)],'B.Cu':[]},box(.3,.3,.5,.5))
        r = reachability(s,'n',[('F.Cu',(.2,1))],[('F.Cu',(.2,1))],tuple(s.geometry),
                         probes=[('B.Cu',(2.5,1)),('F.Cu',(2.5,1))])
        self.assertEqual([p['connected_to_sources'] for p in r['probe_results']],[True,False])

    def test_two_vias_connect_probe_on_other_side(self):
        vias = unary_union([box(.3,.3,.5,.5),box(2.3,.3,2.5,.5)])
        s = screen({'F.Cu':[box(1,0,1.2,2)],'B.Cu':[]},vias)
        r = reachability(s,'n',[('F.Cu',(.2,1))],[('F.Cu',(.2,1))],tuple(s.geometry),
                         probes=[('F.Cu',(2.5,1))])
        self.assertTrue(r['probe_results'][0]['connected_to_sources'])

    def test_obstacle_and_outside_points_remain_unreachable(self):
        s = screen({'F.Cu':[box(1,0,1.2,2)]})
        r = reachability(s,'n',[('F.Cu',(.2,1))],[('F.Cu',(.2,1))],tuple(s.geometry),
                         probes=[('F.Cu',(1.1,1)),('F.Cu',(4,1)),('F.Cu',(.5,1))])
        self.assertEqual([p['connected_to_sources'] for p in r['probe_results']],[False,False,True])


if __name__ == '__main__':
    unittest.main()
