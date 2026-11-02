"""Reject missing copper, false ground targets and unreviewed audio escapes."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_routes as audit


class AudioMainRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.construction = json.loads((audit.OUT / "construction.json").read_text())
        cls.captured = json.loads((audit.FIRST / "native-inputs.json").read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.record = copy.deepcopy(self.construction)

    def verify(self):
        return audit.verify_copper(self.board, self.record, self.captured)

    def test_source_bound_copper_receipt_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "routing-handoff.json").read_text()))

    def test_grounded_logic_input_is_not_a_bypass_ground_terminal(self):
        row = next(r for r in self.record["requests"] if r["ref"] == "C612" and r["pin"] == "2")
        row["owner_pin"] = "13"
        with self.assertRaisesRegex(AssertionError, "grounded signal input"):
            self.verify()

    def test_missing_compensation_track_cannot_pass_a_saved_witness(self):
        row = next(r for r in self.record["routes"] if r["ref"] == "C101")
        segment = next(s for s in children(self.board, "segment") if first(s, "uuid")[1] == row["segment_uuids"][0])
        self.board.remove(segment)
        with self.assertRaises(KeyError):
            self.verify()

    def test_inner_layer_signal_track_is_rejected(self):
        first(children(self.board, "segment")[0], "layer")[1] = "In1.Cu"
        with self.assertRaises(AssertionError):
            self.verify()

    def test_larger_escape_drill_is_rejected(self):
        first(children(self.board, "via")[0], "drill")[1] = .5
        with self.assertRaises(AssertionError):
            self.verify()

    def test_narrower_track_is_rejected(self):
        first(children(self.board, "segment")[0], "width")[1] = .15
        with self.assertRaises(AssertionError):
            self.verify()

    def test_unreviewed_component_move_invalidates_receiving(self):
        first(children(self.board, "footprint")[0], "at")[1] = 1
        with self.assertRaisesRegex(AssertionError, "receiving geometry"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
