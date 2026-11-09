import unittest

from shapely.geometry import LineString, Point, box
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
import hardware.fabrication.route_nf_surface as surface


def polygons(g):
    return [dict(outer=list(g.exterior.coords), holes=[])]


class CloseMarginTests(unittest.TestCase):
    def setUp(self):
        self.old = surface.WIDTH, surface.CLEARANCE, surface.MARGIN
        surface.WIDTH, surface.CLEARANCE, surface.MARGIN = .2, .2, .001

    def tearDown(self):
        surface.WIDTH, surface.CLEARANCE, surface.MARGIN = self.old

    def screen(self, diameter=.6, kind='PCB_VIA', drill=.3):
        obj = dict(uuid='test', net='A', kind=kind, position_mm=[5.,5.], drill_mm=[drill,drill],
                   layers={'F.Cu':polygons(Point(5,5).buffer(diameter/2,quad_segs=32))})
        return CloseMarginViaScreen(dict(objects=[obj],zones=[],outline=polygons(box(0,0,10,10)),
                                         copper_layers=['F.Cu','In3.Cu','In5.Cu','B.Cu']))

    def test_foreign_copper_still_requires_point_two_clearance(self):
        screen = self.screen()
        self.assertFalse(screen.via_legal('B',(5.8,5)))
        self.assertFalse(screen.via_legal('B',(5.8005,5)))
        self.assertTrue(screen.via_legal('B',(5.802,5)))

    def test_larger_existing_via_uses_actual_copper(self):
        screen = self.screen(diameter=.65)
        self.assertFalse(screen.via_legal('B',(5.825,5)))
        self.assertTrue(screen.via_legal('B',(5.827,5)))

    def test_same_net_hole_and_land_guards_are_retained(self):
        screen = self.screen()
        self.assertFalse(screen.via_legal('A',(5.562,5)))
        self.assertTrue(screen.via_legal('A',(5.564,5)))
        screen = self.screen(kind='PAD',drill=0)
        self.assertFalse(screen.via_legal('A',(5.612,5)))
        self.assertTrue(screen.via_legal('A',(5.614,5)))

    def test_new_via_copper_is_protected_on_other_layers(self):
        screen = self.screen()
        screen.new_vias.append(('A',(7.,5.)))
        self.assertFalse(screen.legal('B','In3.Cu',[(6.5,5.6),(7.5,5.6)]))
        self.assertTrue(screen.legal('B','In3.Cu',[(6.5,5.602),(7.5,5.602)]))
        self.assertFalse(screen.via_legal('B',(7.8,5)))
        self.assertTrue(screen.via_legal('B',(7.802,5)))

    def test_new_track_and_board_edge_guards(self):
        screen = self.screen()
        screen.added.append(('A','F.Cu',LineString([(1,2),(4,2)])))
        self.assertFalse(screen.via_legal('B',(2,2.6)))
        self.assertTrue(screen.via_legal('B',(2,2.602)))
        self.assertFalse(screen.legal('B','F.Cu',[(.609,1),(.609,2)]))


if __name__ == '__main__':
    unittest.main()
