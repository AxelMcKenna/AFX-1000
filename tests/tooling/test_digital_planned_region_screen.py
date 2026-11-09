import unittest
from types import SimpleNamespace

from shapely.geometry import LineString, Point, Polygon, box
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
import hardware.fabrication.route_nf_surface as surface


class PlannedRegionScreenTests(unittest.TestCase):
    def setUp(self):
        self.old = surface.WIDTH, surface.MARGIN
        surface.WIDTH, surface.MARGIN = .2, .01
        self.screen = SimpleNamespace(outline=box(0, 0, 5, 5), via_outline=box(0, 0, 5, 5),
            geometry={'F.Cu': [], 'B.Cu': []}, added=[], new_vias=[],
            obstacles=lambda net: Point(1, 1).buffer(.813), legal=lambda *args: False)

    def tearDown(self):
        surface.WIDTH, surface.MARGIN = self.old

    def test_new_via_uses_full_copper_radius_on_both_faces(self):
        self.screen.new_vias = [('foreign', (1, 1))]
        frozen = PlannedRegionScreen(self.screen, 'signal')
        for face in ('F.Cu', 'B.Cu'):
            _, copper, distance = frozen.geometry[face][0]
            self.assertAlmostEqual(copper.bounds[2], 1.3)
            self.assertAlmostEqual(distance, .31)
            self.assertTrue(copper.buffer(distance).contains(Point(1.59, 1)))

    def test_new_track_only_occupies_its_own_layer(self):
        self.screen.added = [('foreign', 'F.Cu', LineString([(1, 1), (2, 1)]))]
        frozen = PlannedRegionScreen(self.screen, 'signal')
        self.assertEqual(len(frozen.geometry['F.Cu']), 1)
        self.assertFalse(frozen.geometry['B.Cu'])
        self.assertFalse(self.screen.geometry['F.Cu'])

    def test_via_field_keeps_mutual_spacing(self):
        frozen = PlannedRegionScreen(self.screen, 'signal')
        self.assertFalse(frozen.via_legal('signal', (1.8, 1)))
        self.assertTrue(frozen.via_legal('signal', (1.9, 1)))

    def test_original_segment_screen_can_reject(self):
        frozen = PlannedRegionScreen(self.screen, 'signal')
        self.assertFalse(frozen.legal('signal', 'F.Cu', [(1, 1), (2, 1)]))


if __name__ == '__main__':
    unittest.main()
