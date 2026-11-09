"""Clearance verification must use copper edges and respect actual layers/nets."""
import unittest
from hardware.fabrication.digital_copper_clearance import verify_added_track_clearance


def rectangle(x0, y0, x1, y1):
    return [{'outer': [[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]], 'holes': []}]


class CopperClearanceTests(unittest.TestCase):
    def capture(self, gap, net='other', layer='F.Cu'):
        return {'objects': [
            dict(uuid='new', kind='PCB_TRACK', net='signal', layers={'F.Cu': rectangle(0,0,1,.2)}),
            dict(uuid='foreign', kind='PAD', net=net, layers={layer: rectangle(.4,.2+gap,.6,.5+gap)})]}

    def test_actual_edge_gap_is_measured(self):
        result = verify_added_track_clearance(self.capture(.201), {'new'})
        self.assertAlmostEqual(result['closest_pair_within_search_radius']['gap_mm'], .201)

    def test_under_clearance_copper_is_rejected(self):
        with self.assertRaises(AssertionError):
            verify_added_track_clearance(self.capture(.199), {'new'})

    def test_same_net_overlap_is_allowed(self):
        result = verify_added_track_clearance(self.capture(-.1, net='signal'), {'new'})
        self.assertIsNone(result['closest_pair_within_search_radius'])

    def test_other_layer_copper_is_not_a_surface_collision(self):
        result = verify_added_track_clearance(self.capture(-.1, layer='B.Cu'), {'new'})
        self.assertIsNone(result['closest_pair_within_search_radius'])


if __name__ == '__main__':
    unittest.main()
