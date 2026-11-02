"""A watchdog move must preserve analog copper and every inherited closure."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_watchdog_repack as audit


class WatchdogRepack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.capture = json.loads(audit.CAPTURE.read_text())
        cls.report = json.loads((audit.OUT / "terminal-connectivity-review.json").read_text())
        cls.extra = json.loads((audit.OUT / "additional-terminal-review.json").read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.construction = copy.deepcopy(self.record)

    def test_source_bound_handoff_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "routing-handoff.json").read_text()))

    def test_amplifier_pose_cannot_move(self):
        first(audit.fps(self.board)["U101"], "at")[1] = 46
        with self.assertRaisesRegex(AssertionError, "Unexpected analog"):
            audit.verify_delta(self.board, self.construction)

    def test_old_compensation_track_cannot_be_removed(self):
        self.board.remove(children(self.board, "segment")[0])
        with self.assertRaisesRegex(AssertionError, "Unexpected analog"):
            audit.verify_delta(self.board, self.construction)

    def test_declared_watchdog_move_cannot_be_extended(self):
        self.construction["declared_pose_changes"]["U601"]["after"][0] += 1
        with self.assertRaisesRegex(AssertionError, "rigid translation"):
            audit.verify_delta(self.board, self.construction)

    def test_real_terminal_branch_cannot_be_pruned(self):
        self.construction["pruned_abandoned_power_copper_uuids"][0] = "c3ce335a-534a-53df-866b-10fc744d7643"
        with self.assertRaisesRegex(AssertionError, "between real terminals"):
            audit.verify_pruning(self.construction, self.capture)

    def test_drill_size_cannot_be_enlarged_in_both_board_and_record(self):
        row = next(r for r in self.construction["additions"] if r["kind"] == "via")
        node = next(n for n in children(self.board, "via") if first(n, "uuid")[1] == row["uuid"])
        first(node, "drill")[1] = .4
        row["drill_mm"] = .4
        with self.assertRaisesRegex(AssertionError, "Repack drill changed"):
            audit.verify_delta(self.board, self.construction)

    def test_supply_width_cannot_be_reduced_in_both_board_and_record(self):
        row = next(r for r in self.construction["additions"] if r["purpose"] == "watchdog_wide_power_branch")
        node = next(n for n in children(self.board, "segment") if first(n, "uuid")[1] == row["uuid"])
        first(node, "width")[1] = .2
        row["width_mm"] = .2
        with self.assertRaisesRegex(AssertionError, "Repack trace width changed"):
            audit.verify_delta(self.board, self.construction)

    def test_previous_global_join_cannot_be_lost(self):
        extra = copy.deepcopy(self.extra)
        extra["retained_global_control_witnesses"][0]["contacts"][0]["native_connected"] = False
        with self.assertRaisesRegex(AssertionError, "Prior global control"):
            audit.verify_witnesses(self.report, extra, self.record, self.capture)

    def test_completed_control_join_cannot_be_faked_by_a_via_only(self):
        report = copy.deepcopy(self.report)
        report["new_route_witnesses"][0]["contacts"].pop()
        with self.assertRaisesRegex(AssertionError, "complete native pad witnesses"):
            audit.verify_witnesses(report, self.extra, self.record, self.capture)

    def test_watchdog_timing_connection_is_required(self):
        extra = copy.deepcopy(self.extra)
        extra["private_timing_connection"]["native_connected"] = False
        with self.assertRaises(AssertionError):
            audit.verify_witnesses(self.report, extra, self.record, self.capture)


if __name__ == "__main__":
    unittest.main()
