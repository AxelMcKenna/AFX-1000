"""Control additions must preserve real terminals, analog space and drill rules."""

import copy
import json
import unittest

from shapely.geometry import LineString

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_global_controls as audit
from hardware.fabrication.audio_main_global_controls import LAYERS, SignalScreen


def rectangle(left, top, right, bottom):
    return [dict(outer=[[left, top], [right, top], [right, bottom], [left, bottom]], holes=[])]


def empty_capture():
    return dict(outline=rectangle(0, 0, 20, 20), objects=[], zones=[dict(
        net="AGND", layer="In1.Cu", keepout=False, polygons=rectangle(0, 0, 20, 20))])


class ControlObstacleSafety(unittest.TestCase):
    def test_analog_opening_protects_every_signal_face_and_new_drills(self):
        captured = empty_capture()
        captured["zones"].append(dict(net="", layer="In1.Cu", keepout=True,
                                      prohibit_tracks=False, prohibit_vias=False, polygons=rectangle(9, 9, 11, 11)))
        screen = SignalScreen(captured)
        for layer in LAYERS:
            self.assertFalse(screen.legal("CONTROL", layer, [(8, 10), (12, 10)]))
            self.assertTrue(screen.legal("CONTROL", layer, [(8, 12), (12, 12)]))
        self.assertFalse(screen.via_legal("CONTROL", (10, 10)))

    def test_later_routes_invalidate_cached_obstacle_index(self):
        screen = SignalScreen(empty_capture())
        path = [(10, 2), (10, 18)]
        self.assertTrue(screen.legal("CONTROL", "F.Cu", path))
        screen.added.append(("OTHER", "F.Cu", LineString([(2, 10), (18, 10)])))
        self.assertFalse(screen.legal("CONTROL", "F.Cu", path))
        self.assertTrue(screen.legal("CONTROL", "B.Cu", path))

    def test_later_vias_invalidate_cache_on_all_faces(self):
        screen = SignalScreen(empty_capture())
        path = [(2, 10), (18, 10)]
        self.assertTrue(screen.legal("CONTROL", "F.Cu", path))
        screen.new_vias.append(("OTHER", (10, 10)))
        for layer in LAYERS:
            self.assertFalse(screen.legal("CONTROL", layer, path))

    def test_same_net_via_centre_can_connect_but_side_swipe_is_rejected(self):
        screen = SignalScreen(empty_capture())
        screen.new_vias.append(("CONTROL", (10, 10)))
        self.assertTrue(screen.legal("CONTROL", "F.Cu", [(2, 10), (18, 10)]))
        self.assertFalse(screen.legal("CONTROL", "F.Cu", [(2, 10.2), (18, 10.2)]))

    def test_new_drill_requires_intact_existing_reference(self):
        captured = empty_capture()
        captured["zones"][0]["polygons"][0]["holes"] = [rectangle(9, 9, 11, 11)[0]["outer"]]
        screen = SignalScreen(captured)
        self.assertFalse(screen.via_legal("CONTROL", (11.4, 10)))
        self.assertTrue(screen.via_legal("CONTROL", (12, 10)))


class AudioMainGlobalControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.capture = json.loads((audit.OUT / "native-inputs.json").read_text())
        cls.witness = json.loads((audit.OUT / "terminal-connectivity-review.json").read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.construction = copy.deepcopy(self.record)

    def verify(self):
        return audit.verify_copper(self.board, self.construction, self.capture)

    def test_source_bound_handoff_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "routing-handoff.json").read_text()))

    def test_existing_analog_track_cannot_be_removed(self):
        self.board.remove(children(self.board, "segment")[0])
        with self.assertRaisesRegex(AssertionError, "Parent analog/power"):
            self.verify()

    def test_new_control_width_cannot_be_reduced(self):
        ident = self.construction["added_segments"][0]["uuid"]
        node = next(n for n in children(self.board, "segment") if first(n, "uuid")[1] == ident)
        first(node, "width")[1] = .16
        self.construction["added_segments"][0]["width_mm"] = .16
        with self.assertRaisesRegex(AssertionError, "Control width changed"):
            self.verify()

    def test_new_drill_cannot_be_enlarged_in_board_and_receipt(self):
        ident = self.construction["added_vias"][0]["uuid"]
        node = next(n for n in children(self.board, "via") if first(n, "uuid")[1] == ident)
        first(node, "drill")[1] = .4
        self.construction["added_vias"][0]["drill_mm"] = .4
        with self.assertRaisesRegex(AssertionError, "Control drill changed"):
            self.verify()

    def test_route_cannot_claim_to_merge_an_island_with_itself(self):
        row = self.construction["routes"][0]
        row["source_groups"][1] = row["source_groups"][0]
        with self.assertRaisesRegex(AssertionError, "False control island merge"):
            self.verify()

    def test_native_route_witness_cannot_omit_a_real_pad(self):
        report = copy.deepcopy(self.witness)
        report["new_route_witnesses"][0]["contacts"].pop()
        with self.assertRaisesRegex(AssertionError, "complete native pad witnesses"):
            audit.verify_terminals(report, self.record, self.capture)

    def test_native_route_witness_cannot_report_a_disconnected_pad(self):
        report = copy.deepcopy(self.witness)
        report["new_route_witnesses"][0]["contacts"][0]["native_connected"] = False
        with self.assertRaisesRegex(AssertionError, "complete native pad witnesses"):
            audit.verify_terminals(report, self.record, self.capture)

    def test_previously_connected_ground_cannot_disappear(self):
        report = copy.deepcopy(self.witness)
        report["ground_pads"][0]["native_connected_to_input_ground"] = False
        with self.assertRaisesRegex(AssertionError, "Ground terminal lost"):
            audit.verify_terminals(report, self.record, self.capture)


if __name__ == "__main__":
    unittest.main()
