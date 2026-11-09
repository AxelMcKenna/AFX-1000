import time
import unittest
from types import SimpleNamespace

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from hardware.fabrication.digital_continuous_net_route import route


def screen(obstacles, portals=()):
    area = box(0, 0, 4, 3)
    vias = unary_union(list(portals)) if portals else Polygon()
    free = {f: area.difference(unary_union(gs)) for f,gs in obstacles.items()}
    return SimpleNamespace(outline=area, via_outline=vias,
        geometry={f:[('other',g,0) for g in gs] for f,gs in obstacles.items()},
        added=[], new_vias=[], obstacles=lambda net: Polygon(),
        legal=lambda net,f,ps: free[f].covers(LineString(ps)),
        via_legal=lambda net,p: vias.covers(Point(p)))


class ContinuousNetRouteTests(unittest.TestCase):
    def test_same_face_detour_avoids_obstacle(self):
        s = screen({'F.Cu':[box(1,1,3,2)]})
        r = route(s,'n','F.Cu',(.5,1.5),{('F.Cu',(3.5,1.5))},time.monotonic()+5)
        self.assertIsNotNone(r)
        self.assertFalse(r['vias'])
        self.assertTrue(all(s.legal('n',f,p) for f,p in r['runs']))

    def test_disconnected_endpoint_rejected(self):
        s = screen({'F.Cu':[box(1,0,2,3)]})
        self.assertIsNone(route(s,'n','F.Cu',(.5,1.5),{('F.Cu',(3.5,1.5))},time.monotonic()+5))

    def test_two_vias_bridge_a_severed_layer(self):
        s = screen({'F.Cu':[box(1,0,2,3)],'B.Cu':[]},[box(.3,.3,.7,.7),box(2.3,.3,2.7,.7)])
        r = route(s,'n','F.Cu',(.5,1.5),{('F.Cu',(3.5,1.5))},time.monotonic()+5)
        self.assertIsNotNone(r)
        self.assertEqual(len(r['vias']),2)
        self.assertTrue(all(s.via_legal('n',p) for p in r['vias']))
        self.assertTrue(all(s.legal('n',f,p) for f,p in r['runs']))

    def test_existing_crossing_does_not_duplicate_via(self):
        s = screen({'F.Cu':[],'B.Cu':[]})
        r = route(s,'n','F.Cu',(.5,1.5),{('B.Cu',(3.5,1.5))},time.monotonic()+5,
                  existing_crossings=[((.5,1.5),['F.Cu','B.Cu'])])
        self.assertIsNotNone(r)
        self.assertFalse(r['vias'])
        self.assertEqual(r['runs'][0][0],'B.Cu')


if __name__ == '__main__':
    unittest.main()
