"""Placed rail completion must preserve copper and real per-terminal evidence."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_supply_completion as audit


class AudioMainSupplyCompletion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.capture = json.loads((audit.OUT / "native-inputs.json").read_text())
        cls.witness = json.loads((audit.OUT / "supply-connectivity-review.json").read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.construction = copy.deepcopy(self.record)

    def verify(self):
        return audit.verify_added(self.board, self.construction, self.capture)

    def test_source_bound_receipt_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "routing-handoff.json").read_text()))

    def test_original_feedback_copper_cannot_disappear(self):
        self.board.remove(children(self.board, "segment")[0])
        with self.assertRaisesRegex(AssertionError, "Parent copper"):
            self.verify()

    def test_sensitive_plane_opening_cannot_change(self):
        zone = next(z for z in children(self.board, "zone") if children(z, "layers") and
                    set(first(z, "layers")[1:]) == {"In1.Cu", "In2.Cu"})
        self.board.remove(zone)
        with self.assertRaisesRegex(AssertionError, "authored keepouts"):
            self.verify()

    def test_actual_drill_geometry_is_checked(self):
        ident = self.construction["added_vias"][0]["uuid"]
        node = next(n for n in children(self.board, "via") if first(n, "uuid")[1] == ident)
        first(node, "drill")[1] = .4
        with self.assertRaisesRegex(AssertionError, "Bridge drill changed"):
            self.verify()

    def test_short_necks_keep_their_own_budget(self):
        neck = next(r["necks"][0] for r in self.construction["routes"] if r["necks"])
        start, end = neck["path_mm"][0], neck["path_mm"][-1]
        neck["path_mm"] = [start, [start[0]+5, start[1]], end]
        with self.assertRaisesRegex(AssertionError, "Narrow neck length"):
            self.verify()

    def test_divider_feed_allowance_cannot_power_a_bulk_capacitor(self):
        row = next(r for r in self.construction["routes"] if r["divider_feed"])
        pad = next(o for o in self.capture["objects"] if o.get("ref") == "C219" and o.get("pin") == "1")
        row["endpoint_uuid"] = pad["uuid"]
        with self.assertRaisesRegex(AssertionError, "Divider exception"):
            self.verify()

    def test_source_count_cannot_hide_one_disconnected_pad(self):
        report = copy.deepcopy(self.witness)
        report["supply_pads"][0]["native_connected_to_source"] = False
        with self.assertRaisesRegex(AssertionError, "not connected to source"):
            audit.verify_witness(report, self.capture)

    def test_all_supply_and_sense_pad_keys_are_required(self):
        report = copy.deepcopy(self.witness)
        report["supply_pads"].pop()
        with self.assertRaises(AssertionError):
            audit.verify_witness(report, self.capture)


if __name__ == "__main__":
    unittest.main()
