"""Power cleanup must preserve real terminals and connections on other faces."""

import copy
import unittest

from shapely.geometry import LineString, Point

from hardware.fabrication.audio_main_power_pruning import prune


def polygon(g):
    return [dict(outer=list(g.exterior.coords), holes=[])]


def track(ident, start, end, layer="F.Cu"):
    return dict(uuid=ident, net="V3V3_IO", kind="PCB_TRACK", position_mm=start, end_mm=end,
                layers={layer: polygon(LineString([start, end]).buffer(.1))})


def pad(ident, point, layer="F.Cu", net="V3V3_IO"):
    return dict(uuid=ident, net=net, kind="PAD", position_mm=point,
                layers={layer: polygon(Point(point).buffer(.2))})


def via(ident, point):
    return dict(uuid=ident, net="V3V3_IO", kind="PCB_VIA", position_mm=point,
                layers={l: polygon(Point(point).buffer(.3)) for l in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")})


class PowerLeafPruning(unittest.TestCase):
    def test_only_abandoned_twigs_are_removed(self):
        objects = [pad("source", (0, 0)), pad("load", (3, 0)), track("main-a", (0, 0), (1, 0)),
                   track("main-b", (1, 0), (3, 0)), track("twig-a", (1, 0), (1, 1)), track("twig-b", (1, 1), (1, 2))]
        captured = dict(objects=copy.deepcopy(objects))
        self.assertEqual(set(prune(captured)), {"twig-a", "twig-b"})
        self.assertEqual(captured["objects"], objects[:4])

    def test_via_preserves_real_connection_on_another_face(self):
        objects = [pad("source", (0, 0)), pad("load", (2, 0), "B.Cu"), via("transition", (1, 0)),
                   track("top", (0, 0), (1, 0)), track("bottom", (1, 0), (2, 0), "B.Cu")]
        captured = dict(objects=copy.deepcopy(objects))
        self.assertEqual(prune(captured), [])
        self.assertEqual(captured["objects"], objects)

    def test_abandoned_via_and_single_face_stub_are_removed_together(self):
        captured = dict(objects=[pad("source", (0, 0)), track("stub", (0, 0), (1, 0)), via("orphan", (1, 0))])
        self.assertEqual(set(prune(captured)), {"stub", "orphan"})
        self.assertEqual([o["uuid"] for o in captured["objects"]], ["source"])

    def test_branch_joining_middle_of_track_does_not_delete_main_feed(self):
        objects = [pad("source", (0, 0)), pad("load", (2, 0)), track("main", (0, 0), (2, 0)),
                   track("twig", (1, 0), (1, 1))]
        captured = dict(objects=copy.deepcopy(objects))
        self.assertEqual(prune(captured), ["twig"])
        self.assertEqual(captured["objects"], objects[:3])

    def test_other_net_pad_cannot_disguise_an_abandoned_power_end(self):
        captured = dict(objects=[pad("source", (0, 0)), pad("foreign", (1, 0), net="AGND"), track("stub", (0, 0), (1, 0))])
        self.assertEqual(prune(captured), ["stub"])
        self.assertEqual([o["uuid"] for o in captured["objects"]], ["source", "foreign"])

    def test_real_terminals_remain_even_if_their_group_lacks_a_source(self):
        objects = [pad("load-a", (0, 0)), pad("load-b", (2, 0)), track("real", (0, 0), (2, 0))]
        captured = dict(objects=copy.deepcopy(objects))
        self.assertEqual(prune(captured), [])
        self.assertEqual(captured["objects"], objects)


if __name__ == "__main__":
    unittest.main()
