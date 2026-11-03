"""Reject weakened comparator-input routing and changed retained circuitry."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_named_routes as audit


class NamedRouteMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.board = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.captured = json.loads((audit.OUT / "native-inputs.json").read_text())

    def verify(self, board=None, record=None):
        return audit.verify_routes(self.parent, self.board if board is None else board,
                                   self.record if record is None else record, self.captured)

    def test_native_reviewed_routes(self):
        self.assertGreaterEqual(self.verify(), .16)

    def test_reject_changed_existing_supply(self):
        board = copy.deepcopy(self.board)
        n = next(n for n in children(board[:len(self.parent)], "segment") if float(first(n, "width")[1]) == .6)
        first(n, "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "Existing geometry"):
            self.verify(board=board)

    def test_reject_narrowed_new_trace_even_when_declared(self):
        board, record = copy.deepcopy(self.board), copy.deepcopy(self.record)
        n = next(n for n in board[len(self.parent):] if n[0] == "segment")
        first(n, "width")[1] = .16
        record["added_segments"][0]["width_mm"] = .16
        with self.assertRaisesRegex(AssertionError, "Monitor width"):
            self.verify(board=board, record=record)

    def test_reject_larger_drill_even_when_declared(self):
        board, record = copy.deepcopy(self.board), copy.deepcopy(self.record)
        n = next(n for n in board[len(self.parent):] if n[0] == "via")
        first(n, "drill")[1] = .4
        record["added_vias"][0]["drill_mm"] = .4
        with self.assertRaisesRegex(AssertionError, "Monitor drill"):
            self.verify(board=board, record=record)

    def test_reject_weakened_noisy_net_gap(self):
        record = copy.deepcopy(self.record)
        record["noisy_net_centreline_to_copper_mm"] = .31
        with self.assertRaises(AssertionError):
            self.verify(record=record)

    def test_reject_relaxed_route_budget(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["maximum_planar_length_mm"] = 180
        with self.assertRaises(AssertionError):
            self.verify(record=record)

    def test_reject_false_source_island_merge(self):
        record = copy.deepcopy(self.record)
        r = record["routes"][0]
        r["source_groups"][1] = r["source_groups"][0]
        with self.assertRaisesRegex(AssertionError, "False named-net"):
            self.verify(record=record)


if __name__ == "__main__":
    unittest.main()
