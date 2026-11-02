"""Settling-cell routing must preserve analog copper, true terminals and sensing roles."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_settle_repack as audit


class SettleRepack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.capture = json.loads(audit.CAPTURE.read_text())
        cls.report = json.loads((audit.OUT / "terminal-connectivity-review.json").read_text())
        cls.extra = json.loads((audit.OUT / "additional-terminal-review.json").read_text())
        cls.pads = json.loads((audit.OUT / "current-native-pads.json").read_text())["objects"]
        cls.planning = json.loads((audit.OUT / "planning-inputs.json").read_text())

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

    def test_declared_settling_move_cannot_be_extended(self):
        self.construction["declared_pose_changes"]["U208"]["after"][0] += 1
        with self.assertRaisesRegex(AssertionError, "Declared cell pose"):
            audit.verify_delta(self.board, self.construction)

    def test_real_terminal_branch_cannot_be_pruned(self):
        self.construction["pruned_abandoned_power_copper_uuids"][0] = "ce0587ce-d5ab-5cf0-b16e-89920e6d4bea"
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
        row = next(r for r in self.construction["additions"] if r["purpose"] == "retained_supply_bridge")
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

    def test_settling_timing_connection_is_required(self):
        extra = copy.deepcopy(self.extra)
        extra["private_timing_connection"]["native_connected"] = False
        with self.assertRaises(AssertionError):
            audit.verify_witnesses(self.report, extra, self.record, self.capture)

    def test_previous_watchdog_timing_connection_is_retained(self):
        extra = copy.deepcopy(self.extra)
        extra["retained_private_timing_connections"][0]["native_connected"] = False
        with self.assertRaisesRegex(AssertionError, "Prior private timing"):
            audit.verify_witnesses(self.report, extra, self.record, self.capture)

    def test_long_narrow_exception_cannot_terminate_at_VDD(self):
        row = next(r for r in self.construction["additions"] if r["kind"] == "segment" and r["start_mm"] == [45.43, 18.1])
        row["start_mm"] = [46.43, 16.9]
        with self.assertRaisesRegex(AssertionError, "SENSE endpoint missing or redirected to VDD"):
            audit.verify_sense(self.construction, self.pads, self.planning)

    def test_sense_branch_cannot_backfeed_another_supply_load(self):
        planning = copy.deepcopy(self.planning)
        other_id = next(r["uuid"] for r in self.record["additions"] if r["kind"] == "segment" and r["purpose"] == "local_pullup_power" and r["layer"] == "B.Cu")
        sense_id = next(r["uuid"] for r in self.record["additions"] if r["kind"] == "segment" and r["purpose"] == "settle_sense_branch")
        objects = {o["uuid"]: o for o in planning["objects"]}
        objects[other_id]["layers"]["B.Cu"] = copy.deepcopy(objects[sense_id]["layers"]["B.Cu"])
        with self.assertRaisesRegex(AssertionError, "SENSE branch carries another supply load"):
            audit.verify_sense(self.record, self.pads, planning)

    def test_sense_length_limit_is_not_a_bulk_routing_allowance(self):
        points = [[44.5, 19.52], [44.5, 25], [49, 25], [49, 18.2]]
        self.construction["replacement_power_paths_mm"][0]["points_mm"] = points
        self.construction["additions"] = [r for r in self.construction["additions"] if r["purpose"] != "settle_sense_branch"]
        for i, (start, end) in enumerate(zip(points, points[1:])):
            self.construction["additions"].append(dict(kind="segment", uuid="overlong-"+str(i), net="V3V3_IO", layer="B.Cu",
                start_mm=start, end_mm=end, width_mm=.2, purpose="settle_sense_branch"))
        with self.assertRaisesRegex(AssertionError, "SENSE trace length exceeds 12"):
            audit.verify_sense(self.construction, self.pads, self.planning)


if __name__ == "__main__":
    unittest.main()
