"""Verify drill/copper distinctions at dense via-spacing boundaries."""
import unittest
import json
import tempfile
from pathlib import Path
import numpy as np
from shapely.geometry import Point, box
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen, via_mask
from hardware.fabrication.audit_candidate import sha


def polygons(g):
    return [dict(outer=list(g.exterior.coords), holes=[])]


class DigitalViaSpacingTests(unittest.TestCase):
    def screen(self, diameter=.6, kind='PCB_VIA', drill=.3):
        obj = dict(uuid='test', net='A', kind=kind, position_mm=[5., 5.],
                   drill_mm=[drill, drill],
                   layers={'F.Cu': polygons(Point(5, 5).buffer(diameter/2, quad_segs=32))})
        return DigitalViaScreen(dict(objects=[obj], zones=[],
            outline=polygons(box(0, 0, 10, 10)), copper_layers=['F.Cu', 'In3.Cu', 'B.Cu']))

    def test_same_net_uses_drills_and_foreign_net_uses_copper(self):
        s = self.screen()
        self.assertFalse(s.via_legal('A', (5.55, 5)))
        self.assertTrue(s.via_legal('A', (5.57, 5)))
        self.assertFalse(s.via_legal('B', (5.80, 5)))
        self.assertTrue(s.via_legal('B', (5.82, 5)))

    def test_actual_larger_via_diameter_is_respected(self):
        s = self.screen(diameter=.65)
        self.assertFalse(s.via_legal('B', (5.83, 5)))
        self.assertTrue(s.via_legal('B', (5.85, 5)))

    def test_same_net_smd_land_keeps_drill_edge_gap(self):
        s = self.screen(kind='PAD', drill=0)
        self.assertFalse(s.via_legal('A', (5.60, 5)))
        self.assertTrue(s.via_legal('A', (5.62, 5)))

    def test_new_vias_follow_same_distinction(self):
        s = self.screen()
        s.new_vias.append(('A', (7., 5.)))
        self.assertFalse(s.via_legal('A', (7.55, 5)))
        self.assertTrue(s.via_legal('A', (7.57, 5)))
        self.assertFalse(s.via_legal('B', (7.80, 5)))
        self.assertTrue(s.via_legal('B', (7.82, 5)))

    def test_raster_matches_point_screen_away_from_reused_via(self):
        s = self.screen()
        xs = np.array([5.55, 5.57, 5.80, 5.82])
        for net in ('A', 'B'):
            result = via_mask(s, net, xs, np.array([5.]))
            self.assertEqual(result[0].tolist(), [s.via_legal(net, (x, 5.)) for x in xs])
        self.assertTrue(s.via_legal('A', (5, 5)))
        self.assertFalse(s.via_legal('B', (5, 5)))

    def test_native_capture_omits_via_drill_so_paired_pcb_supplies_it(self):
        with tempfile.TemporaryDirectory() as directory:
            pcb = Path(directory)/'native.kicad_pcb'
            pcb.write_text('(kicad_pcb (via (at 5 5) (size 0.6) (drill 0.3) (uuid test)))')
            obj = dict(uuid='test', net='A', kind='PCB_VIA', position_mm=[5., 5.],
                       layers={'F.Cu': polygons(Point(5, 5).buffer(.3, quad_segs=32))})
            capture = dict(objects=[obj], zones=[], outline=polygons(box(0, 0, 10, 10)),
                           copper_layers=['F.Cu', 'In3.Cu', 'B.Cu'], source_sha256={str(pcb): sha(pcb)})
            s = DigitalViaScreen(capture)
            self.assertFalse(s.via_legal('A', (5.55, 5)))
            self.assertTrue(s.via_legal('A', (5.57, 5)))
            pcb.write_text(pcb.read_text().replace('(drill 0.3)', '(drill 0.4)'))
            with self.assertRaises(AssertionError):
                DigitalViaScreen(capture)


if __name__ == '__main__':
    unittest.main()
