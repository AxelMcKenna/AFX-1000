"""Expanded clearances must find obstacles outside the legacy search radius."""

import unittest

from shapely.geometry import LineString, box

from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen


def polygons(p):
    return [dict(outer=list(p.exterior.coords), holes=[])]


def capture():
    outline = box(0, 0, 10, 10)
    return dict(copper_layers=["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"],
                outline=polygons(outline), objects=[dict(uuid="digital", net="NOISY", kind="PCB_TRACK",
                position_mm=[2, 4.4], layers={"F.Cu": polygons(box(2, 4.3, 8, 4.5))})],
                zones=[dict(net="AGND", layer=face, keepout=False, polygons=polygons(outline)) for face in ("In1.Cu", "In4.Cu")])


class QuietScreenTests(unittest.TestCase):
    def test_obstacle_beyond_old_half_mm_search_is_rejected(self):
        screen = QuietTraceScreen(capture(), {"NOISY"})
        self.assertFalse(screen.legal("INPUT", "F.Cu", [[2, 5.1], [8, 5.1]]))

    def test_larger_gap_is_accepted(self):
        screen = QuietTraceScreen(capture(), {"NOISY"})
        self.assertTrue(screen.legal("INPUT", "F.Cu", [[2, 5.3], [8, 5.3]]))

    def test_added_centreline_also_uses_enlarged_gap(self):
        screen = QuietTraceScreen(capture(), {"NOISY"})
        screen.added.append(("NOISY", "In3.Cu", LineString([[2, 4.4], [8, 4.4]])))
        self.assertFalse(screen.legal("INPUT", "In3.Cu", [[2, 5.1], [8, 5.1]]))
        self.assertTrue(screen.legal("INPUT", "In3.Cu", [[2, 5.3], [8, 5.3]]))

    def test_another_layer_is_not_accidentally_excluded(self):
        screen = QuietTraceScreen(capture(), {"NOISY"})
        self.assertTrue(screen.legal("INPUT", "B.Cu", [[2, 5.1], [8, 5.1]]))


if __name__ == "__main__":
    unittest.main()
