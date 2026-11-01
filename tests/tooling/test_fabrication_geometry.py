"""Boundary and obstacle mutations for fabrication candidate geometry screens."""

import unittest

from hardware.electronics.common.sexpr import read_sexpr
from hardware.fabrication.e28_redundant_tracks import exact_capsule_contains
from hardware.fabrication.route_nf_layers import LayerScreen
from hardware.fabrication.route_nf_surface import Screen, is_logic_net


def track(start, end, width):
    return read_sexpr(f"(segment (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (width {width}))")


def rectangle(x1, y1, x2, y2):
    return [dict(outer=[[x1, y1], [x2, y1], [x2, y2], [x1, y2]], holes=[])]


def capture():
    return dict(outline=rectangle(0, 0, 20, 20), objects=[], zones=[])


class ExactCopperContainment(unittest.TestCase):
    def test_coincident_and_reversed_tracks_are_contained(self):
        outer = track((0, 0), (10, 0), ".2")
        self.assertTrue(exact_capsule_contains(outer, track((10, 0), (0, 0), ".2")))
        self.assertTrue(exact_capsule_contains(outer, track((2, 0), (8, 0), ".2")))

    def test_one_nanometre_side_or_endpoint_loss_is_rejected(self):
        outer = track((0, 0), (10, 0), ".2")
        self.assertFalse(exact_capsule_contains(outer, track((2, ".000001"), (8, ".000001"), ".2")))
        self.assertFalse(exact_capsule_contains(outer, track((2, 0), ("10.000001", 0), ".2")))

    def test_wider_support_accepts_exact_radial_allowance_only(self):
        outer = track((0, 0), (10, 0), ".4")
        self.assertTrue(exact_capsule_contains(outer, track((2, ".1"), (8, ".1"), ".2")))
        self.assertFalse(exact_capsule_contains(outer, track((2, ".100001"), (8, ".1"), ".2")))
        self.assertFalse(exact_capsule_contains(outer, track((2, 0), (8, 0), ".400001")))

    def test_degenerate_support_and_sub_nanometre_coordinates(self):
        outer = track((0, 0), (0, 0), ".4")
        self.assertTrue(exact_capsule_contains(outer, track((0, 0), (".1", 0), ".2")))
        self.assertFalse(exact_capsule_contains(outer, track((0, 0), (".100001", 0), ".2")))
        with self.assertRaises(AssertionError):
            exact_capsule_contains(outer, track((0, 0), (".0000001", 0), ".2"))


class RoutingObstacles(unittest.TestCase):
    def test_timing_and_analog_nodes_are_excluded_despite_logic_name_fragments(self):
        for net in ("/N19_START_CT", "/N12_VIN_VALID_CT", "/N19_SAFE_SOURCE", "/N12_P03_SRC", "/AGND"):
            self.assertFalse(is_logic_net(net),net)
        for net in ("/N12_START", "/N19_READY", "/GLOBAL_VALID"):
            self.assertTrue(is_logic_net(net),net)

    def test_diagonal_crossing_is_rejected_even_with_clear_endpoints(self):
        data = capture()
        data["objects"].append(dict(net="OTHER", layers={"F.Cu": rectangle(9.8, 9.8, 10.2, 10.2)}))
        screen = Screen(data)
        self.assertTrue(screen.legal("SIGNAL", "F.Cu", [(8, 8), (8.5, 8.5)]))
        self.assertFalse(screen.legal("SIGNAL", "F.Cu", [(8, 8), (12, 12)]))

    def test_actual_other_inner_layer_copper_blocks_new_through_via(self):
        data = capture()
        data["objects"].append(dict(net="POWER", kind="PCB_TRACK", layers={"In1.Cu": rectangle(9, 9.9, 11, 10.1)}))
        self.assertFalse(LayerScreen(data).via_legal("SIGNAL", (10, 10)))

    def test_same_net_smd_land_is_not_treated_as_free_via_space(self):
        data = capture()
        data["objects"].append(dict(net="SIGNAL", kind="PAD", layers={"F.Cu": rectangle(9.8, 9.8, 10.2, 10.2)}))
        self.assertFalse(LayerScreen(data).via_legal("SIGNAL", (10, 10)))

    def test_npth_with_no_native_copper_polygon_still_blocks_drill(self):
        data = capture()
        data["objects"].append(dict(net="", kind="PAD", layers={}, npth=True, drill_mm=[2.4, 2.4], position_mm=[10, 10]))
        self.assertFalse(LayerScreen(data).via_legal("SIGNAL", (10, 10)))
        self.assertFalse(Screen(data).legal("SIGNAL", "B.Cu", [(7, 10), (13, 10)]))

    def test_plane_clearance_is_explicitly_left_for_native_refill(self):
        data = capture()
        data["zones"].append(dict(net="POWER", layer="In1.Cu", keepout=False, prohibit_tracks=False, prohibit_vias=False, polygons=rectangle(1, 1, 19, 19)))
        self.assertTrue(LayerScreen(data).via_legal("SIGNAL", (10, 10)))
        data["zones"][0].update(keepout=True, prohibit_tracks=True, prohibit_vias=True)
        self.assertFalse(LayerScreen(data).via_legal("SIGNAL", (10, 10)))

    def test_new_via_is_an_obstacle_on_every_signal_layer(self):
        screen = LayerScreen(capture())
        screen.new_vias.append(("OTHER", (10, 10)))
        self.assertFalse(screen.legal("SIGNAL", "In3.Cu", [(8, 10), (12, 10)]))
        self.assertTrue(screen.legal("SIGNAL", "In3.Cu", [(8, 11), (12, 11)]))


if __name__ == "__main__":
    unittest.main()
