"""Check the noise-policy correction and reject changes to retained circuitry."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_gain_clearance as audit
from hardware.fabrication.audio_main_noise_audit import measure


class GainClearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.prepared = read_sexpr((audit.OUT / "prepared-input.kicad_pcb").read_text())
        cls.refilled = read_sexpr((audit.OUT / "prepared-refilled.kicad_pcb").read_text())
        cls.board = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.preparation = json.loads((audit.OUT / "preparation-record.json").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.captured = json.loads((audit.OUT / "prepared-native-inputs.json").read_text())

    def test_saved_branch_preparation(self):
        audit.verify_preparation(self.source, self.prepared, self.preparation)

    def test_reject_unrelated_power_width_change(self):
        board = copy.deepcopy(self.prepared)
        track = next(n for n in children(board, "segment") if float(first(n, "width")[1]) == .6)
        first(track, "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "Undeclared source geometry"):
            audit.verify_preparation(self.source, board, self.preparation)

    def test_saved_repair_and_surface_bridge(self):
        self.assertGreaterEqual(audit.verify_added(self.refilled, self.board, self.record, self.captured), .16)

    def test_reject_larger_drill_even_when_declared(self):
        board, record = copy.deepcopy(self.board), copy.deepcopy(self.record)
        node = next(n for n in board[len(self.refilled):] if n[0] == "via")
        first(node, "drill")[1] = .4
        record["added_vias"][0]["drill_mm"] = .4
        with self.assertRaises(AssertionError):
            audit.verify_added(self.refilled, board, record, self.captured)

    def test_reject_changed_control_length_limit(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["maximum_planar_length_mm"] = 180
        with self.assertRaises(AssertionError):
            audit.verify_added(self.refilled, self.board, record, self.captured)

    def test_reject_false_source_island(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["source_groups"][1] = record["routes"][0]["source_groups"][0]
        with self.assertRaises(AssertionError):
            audit.verify_added(self.refilled, self.board, record, self.captured)

    def test_exhaustive_check_reproduces_four_legacy_failures(self):
        result = audit.legacy_measurement()["measurement"]
        self.assertEqual(len(result["violations"]), 4)
        self.assertLess(min(r["centreline_to_copper_mm"] for r in result["violations"]), .55)

    def test_exhaustive_native_final_measurement_has_no_failures(self):
        final = json.loads((audit.OUT / "final-native-inputs.json").read_text())
        result = measure(final, audit.NETS, audit.NOISY)
        self.assertEqual(result["trace_count"], 41)
        self.assertEqual(result["same_layer_pairs_measured"], 14303)
        self.assertEqual(result["violations"], [])
        self.assertTrue(all(d > .71 for d in result["minimum_by_net_mm"].values()))


if __name__ == "__main__":
    unittest.main()
