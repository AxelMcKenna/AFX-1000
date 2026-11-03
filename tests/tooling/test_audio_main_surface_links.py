"""Negative controls for preserving copper and the short analogue-loop scope."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_surface_links as audit


class SurfaceDeltaMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.board = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.captured = json.loads((audit.OUT / "native-inputs.json").read_text())

    def verify(self, board=None, record=None):
        return audit.verify_delta(self.parent, self.board if board is None else board,
                                  self.record if record is None else record, self.captured)

    def test_actual_native_reviewed_delta(self):
        self.assertEqual(self.verify(), 21)

    def test_reject_existing_power_width_change(self):
        board = copy.deepcopy(self.board)
        track = next(n for n in children(board[:len(self.parent)], "segment")
                     if float(first(n, "width")[1]) == .6)
        first(track, "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "Existing board changed"):
            self.verify(board=board)

    def test_reject_moved_existing_pad(self):
        board = copy.deepcopy(self.board)
        pad = children(children(board, "footprint")[0], "pad")[0]
        first(pad, "at")[1] = float(first(pad, "at")[1]) + .05
        with self.assertRaisesRegex(AssertionError, "Existing board changed"):
            self.verify(board=board)

    def test_reject_narrower_new_track_even_when_declared(self):
        board, record = copy.deepcopy(self.board), copy.deepcopy(self.record)
        track = board[len(self.parent)]
        first(track, "width")[1] = .16
        record["added_segments"][0]["width_mm"] = .16
        with self.assertRaisesRegex(AssertionError, "New trace width changed"):
            self.verify(board=board, record=record)

    def test_reject_inner_layer_even_when_declared(self):
        board, record = copy.deepcopy(self.board), copy.deepcopy(self.record)
        first(board[len(self.parent)], "layer")[1] = "In3.Cu"
        record["added_segments"][0]["layer"] = "In3.Cu"
        with self.assertRaises(AssertionError):
            self.verify(board=board, record=record)

    def test_reject_relaxed_feedback_budget(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["maximum_planar_length_mm"] = 25
        with self.assertRaises(AssertionError):
            self.verify(record=record)

    def test_reject_false_island_merge(self):
        record = copy.deepcopy(self.record)
        r = record["routes"][0]
        r["source_groups"][1] = r["source_groups"][0]
        with self.assertRaisesRegex(AssertionError, "False island merge"):
            self.verify(record=record)


if __name__ == "__main__":
    unittest.main()
