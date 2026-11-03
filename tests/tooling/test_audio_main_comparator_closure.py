"""Reject circuit damage or relaxed constraints in the comparator closure."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_comparator_closure as audit


class ComparatorClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.prepared = read_sexpr((audit.OUT / "prepared-input.kicad_pcb").read_text())
        cls.parent = read_sexpr((audit.OUT / "prepared-refilled.kicad_pcb").read_text())
        cls.board = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.preparation = audit.read("preparation-record.json")
        cls.recipe = json.loads(audit.PLAN.read_text())
        cls.record = audit.read("distribution-construction.json")
        cls.captured = audit.read("prepared-native-inputs.json")
        cls.final = audit.read("final-native-inputs.json")

    def test_saved_native_comparator_closure_and_retained_circuitry(self):
        result = audit.check()
        self.assertEqual(result["uncapped_open_connections"], 171)
        self.assertEqual(result["remaining_comparator_input_gaps"], {})
        self.assertEqual(result["exhaustive_noise_geometry"]["violations"], [])

    def test_reject_unrelated_power_width_change(self):
        board = copy.deepcopy(self.prepared)
        first(next(n for n in children(board, "segment") if float(first(n, "width")[1]) == .6), "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "Undeclared source geometry"):
            audit.verify_preparation(self.source, board, self.preparation, self.recipe)

    def test_reject_additional_component_move(self):
        board = copy.deepcopy(self.prepared)
        ref = next(n for n in children(board, "footprint") if any(str(p[1]) == "Reference" and str(p[2]) == "R139" for p in children(n, "property")))
        first(ref, "at")[1] = float(first(ref, "at")[1])+.1
        with self.assertRaisesRegex(AssertionError, "Undeclared source geometry"):
            audit.verify_preparation(self.source, board, self.preparation, self.recipe)

    def test_reject_false_source_island(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["source_groups"][1] = record["routes"][0]["source_groups"][0]
        with self.assertRaises(AssertionError):
            audit.verify_routes(self.parent, self.board, record, self.captured, self.final)

    def test_reject_relaxed_complete_bias_length_cap(self):
        record = copy.deepcopy(self.record)
        record["routes"][3]["complete_legacy_maximum_mm"] += 1
        with self.assertRaises(AssertionError):
            audit.verify_routes(self.parent, self.board, record, self.captured, self.final)

    def test_reject_larger_drill(self):
        board = copy.deepcopy(self.board)
        ident = self.record["added_vias"][0]["uuid"]
        first(next(n for n in children(board, "via") if str(first(n, "uuid")[1]) == ident), "drill")[1] = .4
        with self.assertRaisesRegex(AssertionError, "geometry changed"):
            audit.verify_routes(self.parent, board, self.record, self.captured, self.final)

    def test_reject_extra_unreviewed_copper(self):
        board = copy.deepcopy(self.board)
        node = copy.deepcopy(children(board, "segment")[-1])
        first(node, "uuid")[1] = "e590703f-0d7a-4c78-8f37-c828ac626a95"
        board.append(node)
        with self.assertRaisesRegex(AssertionError, "geometry changed"):
            audit.verify_routes(self.parent, board, self.record, self.captured, self.final)


if __name__ == "__main__":
    unittest.main()
