import unittest
from shapely.geometry import box,Polygon
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface


class ScreenBranchTests(unittest.TestCase):
    def setUp(self):
        self.settings=surface.WIDTH,surface.MARGIN,surface.SIGNAL_LAYERS
        surface.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=('F.Cu','B.Cu')
        self.capture=dict(objects=[],zones=[],outline=[dict(outer=list(box(0,0,20,20).exterior.coords),holes=[])],copper_layers=['F.Cu','B.Cu'])
        self.screen=CloseMarginViaScreen(self.capture,signal_layers=surface.SIGNAL_LAYERS)

    def tearDown(self):surface.WIDTH,surface.MARGIN,surface.SIGNAL_LAYERS=self.settings

    def test_new_reservations_do_not_leak_to_parent_or_sibling(self):
        left=branch(self.screen);right=branch(self.screen)
        add(left,'a',dict(runs=[('F.Cu',[(2,2),(4,2)])],vias=[(4,2)]))
        self.assertFalse(left.legal('b','F.Cu',[(3,1),(3,3)]))
        self.assertTrue(right.legal('b','F.Cu',[(3,1),(3,3)]))
        self.assertFalse(left.via_legal('b',(4.4,2)))
        self.assertTrue(right.via_legal('b',(4.4,2)))
        self.assertEqual(self.screen.added,[]);self.assertEqual(self.screen.new_vias,[])

    def test_existing_reservations_are_preserved(self):
        add(self.screen,'a',dict(runs=[('B.Cu',[(2,2),(4,2)])],vias=[(4,2)]))
        copy=branch(self.screen)
        self.assertFalse(copy.legal('b','B.Cu',[(3,1),(3,3)]))
        self.assertFalse(copy.via_legal('b',(4.4,2)))
        copy.added.clear();copy.new_vias.clear()
        self.assertEqual(len(self.screen.added),1);self.assertEqual(len(self.screen.new_vias),1)

    def test_native_cache_dictionary_is_independent(self):
        self.screen.obstacles('a');copy=branch(self.screen)
        copy._obstacle_cache['b']=Polygon()
        self.assertNotIn('b',self.screen._obstacle_cache)
        self.assertTrue(copy.obstacles('a').equals(self.screen.obstacles('a')))

    def test_branch_agrees_with_fresh_screen_after_same_reservations(self):
        self.screen.obstacles('a');copy=branch(self.screen)
        fresh=CloseMarginViaScreen(self.capture,signal_layers=surface.SIGNAL_LAYERS)
        for s in (copy,fresh):add(s,'a',dict(runs=[('F.Cu',[(2,2),(4,2)])],vias=[(4,2)]))
        for p in [(4.4,2),(5,2),(0,0),(10,10)]:self.assertEqual(copy.via_legal('b',p),fresh.via_legal('b',p))
        for p in [[(3,1),(3,3)],[(8,8),(9,9)]]:self.assertEqual(copy.legal('b','F.Cu',p),fresh.legal('b','F.Cu',p))


if __name__=='__main__':unittest.main()
