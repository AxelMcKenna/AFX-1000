"""CODEC_PGOOD and its isolated SENSE entry must preserve physical and native constraints."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_codec_pgood as audit


class AudioMainCodecPgood(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.capture = json.loads((audit.OUT / "prepared-native-inputs.json").read_text())
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

    def test_prior_global_join_cannot_be_lost(self):
        report = json.loads((audit.OUT / "additional-terminal-review.json").read_text())
        report["retained_global_control_witnesses"][0]["contacts"][0]["native_connected"] = False
        with self.assertRaisesRegex(AssertionError, "Earlier global control connection lost"):
            audit.verify_inherited(report)

    def test_prior_private_timing_pair_cannot_be_lost(self):
        report = json.loads((audit.OUT / "additional-terminal-review.json").read_text())
        report["retained_private_timing_connections"][0]["native_connected"] = False
        with self.assertRaisesRegex(AssertionError, "Earlier private timing connection lost"):
            audit.verify_inherited(report)

    def test_previously_connected_ground_cannot_disappear(self):
        report = copy.deepcopy(self.witness)
        report["ground_pads"][0]["native_connected_to_input_ground"] = False
        with self.assertRaisesRegex(AssertionError, "Ground terminal lost"):
            audit.verify_terminals(report, self.record, self.capture)

    def verify_sense(self, mutate=None):
        prepared = read_sexpr((audit.OUT / "prepared-input.kicad_pcb").read_text())
        record = json.loads((audit.OUT / "preparation-record.json").read_text())
        if mutate:
            mutate(prepared, record)
        return audit.verify_sense_entry(prepared, record, self.capture)

    def test_unrelated_component_pose_cannot_change(self):
        def mutate(board, record):
            fp = next(f for f in children(board, "footprint") if any(p[1:3]==["Reference", "U107"] for p in children(f, "property")))
            first(fp, "at")[1] = 1
        with self.assertRaisesRegex(AssertionError, "unretired parent geometry"):
            self.verify_sense(mutate)

    def test_sense_copper_cannot_be_narrowed_in_board_and_receipt(self):
        def mutate(board, record):
            row = next(r for r in record["additions"] if r["kind"]=="segment")
            row["width_mm"] = .16
            node = next(n for n in children(board, "segment") if first(n, "uuid")[1]==row["uuid"])
            first(node, "width")[1] = .16
        with self.assertRaisesRegex(AssertionError, "SENSE width changed"):
            self.verify_sense(mutate)

    def test_adjustable_variant_current_cannot_replace_fixed_variant_entry(self):
        def mutate(board, record):
            record["sense_branch_assessment"]["datasheet_fixed_variant_ISENSE_entry_A_at_VSENSE_5V"] = 100e-9
        with self.assertRaises(AssertionError):
            self.verify_sense(mutate)

    def test_engineering_allowance_cannot_claim_datasheet_guarantee(self):
        def mutate(board, record):
            record["sense_branch_assessment"]["current_allowance_is_not_a_datasheet_guarantee_at_3V3"] = False
        with self.assertRaises(AssertionError):
            self.verify_sense(mutate)

    def test_sense_leaf_construction_limit_cannot_expand(self):
        def mutate(board, record):
            record["sense_branch_assessment"]["maximum_leaf_length_mm"] = 20
        with self.assertRaises(AssertionError):
            self.verify_sense(mutate)

    def test_trace_drop_cannot_be_underreported(self):
        def mutate(board, record):
            record["sense_branch_assessment"]["maximum_trace_only_drop_V"] = 0
        with self.assertRaises(AssertionError):
            self.verify_sense(mutate)

    def test_sense_static_check_cannot_claim_electrical_qualification(self):
        def mutate(board, record):
            record["sense_branch_assessment"]["electrical_noise_accuracy_transients_and_installed_process_qualified"] = True
        with self.assertRaises(AssertionError):
            self.verify_sense(mutate)


if __name__ == "__main__":
    unittest.main()
