"""Reject unrelated edits, false PD entries and relaxed legacy route budgets."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_pd_pin_repack as audit


class PDPinRepackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.prepared = read_sexpr((audit.OUT / "prepared-input.kicad_pcb").read_text())
        cls.parent = read_sexpr((audit.OUT / "prepared-refilled.kicad_pcb").read_text())
        cls.board = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.preparation = audit.read("preparation-record.json")
        cls.record = audit.read("distribution-construction.json")
        cls.captured = audit.read("prepared-native-inputs.json")
        cls.recipe = json.loads(audit.PLAN.read_text())

    def test_native_PD_completion_and_retained_circuit(self):
        result = audit.check()
        self.assertEqual(result["uncapped_open_connections"], 162)
        self.assertEqual(result["remaining_PD_control_gaps"], 0)
        self.assertEqual(result["control_legacy_path"]["physical_transition_vias"], 4)
        self.assertEqual(result["exhaustive_noise_geometry"]["violations"], [])

    def test_reject_unrelated_power_change(self):
        board = copy.deepcopy(self.prepared)
        node = next(n for n in children(board, "segment") if float(first(n, "width")[1]) == .6)
        first(node, "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "Undeclared source geometry"):
            audit.verify_preparation(self.source, board, self.preparation, self.recipe)

    def test_reject_unrelated_amplifier_move(self):
        board = copy.deepcopy(self.prepared)
        node = next(n for n in children(board, "footprint") if any(p[1:3] == ["Reference", "U101"] for p in children(n, "property")))
        first(node, "at")[1] = float(first(node, "at")[1])+.1
        with self.assertRaisesRegex(AssertionError, "Undeclared source geometry"):
            audit.verify_preparation(self.source, board, self.preparation, self.recipe)

    def test_entry_permission_is_specific_to_owner_net_and_front_layer(self):
        path = self.recipe["FDA_entry_paths"]["/ADC/PD_L"]
        screen = audit.PDEntryScreen(self.captured, "/ADC/PD_L", path)
        self.assertTrue(screen.legal("/ADC/PD_L", "F.Cu", path))
        self.assertFalse(screen.legal("/ADC/PD_GATED", "F.Cu", path))
        self.assertFalse(screen.legal("/ADC/PD_L", "In3.Cu", path))
        self.assertFalse(audit.QuietTraceScreen(self.captured, audit.NETS).legal("/ADC/PD_L", "F.Cu", path))

    def test_reject_entry_starting_at_another_pin(self):
        path = copy.deepcopy(self.recipe["FDA_entry_paths"]["/ADC/PD_L"])
        path[0][1] += .65
        with self.assertRaises(AssertionError):
            audit.PDEntryScreen(self.captured, "/ADC/PD_L", path)

    def test_reject_relaxed_complete_control_budget(self):
        record = copy.deepcopy(self.record)
        record["routes"][4]["complete_legacy_maximum_mm"] += 1
        with self.assertRaises(AssertionError):
            audit.verify_routes(self.parent, self.board, record, self.captured, self.recipe)

    def test_reject_undeclared_shared_segment(self):
        record = copy.deepcopy(self.record)
        record["routes"][3]["reused_previous_F_segment_mm"][0][0] += .1
        with self.assertRaises(AssertionError):
            audit.verify_routes(self.parent, self.board, record, self.captured, self.recipe)

    def test_reject_larger_actual_drill(self):
        board = copy.deepcopy(self.board)
        uid = self.record["added_vias"][0]["uuid"]
        node = next(n for n in children(board, "via") if str(first(n, "uuid")[1]) == uid)
        first(node, "drill")[1] = .4
        with self.assertRaisesRegex(AssertionError, "geometry differs"):
            audit.verify_routes(self.parent, board, self.record, self.captured, self.recipe)

    def test_reject_false_source_island(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["source_groups"][1] = record["routes"][0]["source_groups"][0]
        with self.assertRaisesRegex(AssertionError, "False source island"):
            audit.verify_routes(self.parent, self.board, record, self.captured, self.recipe)


if __name__ == "__main__":
    unittest.main()
