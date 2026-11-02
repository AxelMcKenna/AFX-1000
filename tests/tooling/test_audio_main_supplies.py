"""Reject supply progress that damages audio copper or loses real terminals."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_supplies as audit


class AudioMainSupplies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.construction = json.loads((audit.OUT / "distribution-construction.json").read_text())
        cls.capture = json.loads((audit.OUT / "native-inputs.json").read_text())
        cls.witness = json.loads((audit.OUT / "supply-connectivity-review.json").read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.record = copy.deepcopy(self.construction)

    def verify(self):
        return audit.verify_board(self.board, self.record, self.capture)

    def test_source_bound_native_refill_and_receipt_replay(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "routing-handoff.json").read_text()))

    def test_parent_analog_copper_cannot_be_removed(self):
        self.board.remove(children(self.board, "segment")[0])
        with self.assertRaisesRegex(AssertionError, "Parent analog copper"):
            self.verify()

    def test_authored_sensitive_node_openings_remain_exact(self):
        zone = next(z for z in children(self.board, "zone") if children(z, "layers") and
                    set(first(z, "layers")[1:]) == {"In1.Cu", "In2.Cu"})
        self.board.remove(zone)
        with self.assertRaisesRegex(AssertionError, "authored zone"):
            self.verify()

    def test_actual_distribution_width_is_checked(self):
        row = next(r for r in self.record["added_segments"] if r["layer"] == "In2.Cu")
        node = next(n for n in children(self.board, "segment") if first(n, "uuid")[1] == row["uuid"])
        first(node, "width")[1] = .4
        row["width_mm"] = .4
        with self.assertRaisesRegex(AssertionError, "Distribution width"):
            self.verify()

    def test_drill_changes_cannot_hide_behind_correct_counts(self):
        ident = self.record["added_vias"][0]["uuid"]
        node = next(n for n in children(self.board, "via") if first(n, "uuid")[1] == ident)
        first(node, "drill")[1] = .4
        with self.assertRaisesRegex(AssertionError, "drill geometry"):
            self.verify()

    def test_one_missing_ground_terminal_is_rejected(self):
        witness = copy.deepcopy(self.witness)
        witness["ground_pads"].pop()
        with self.assertRaisesRegex(AssertionError, "ground terminal"):
            audit.verify_witnesses(witness, self.capture, self.record)

    def test_planned_island_must_reach_its_real_source(self):
        witness = copy.deepcopy(self.witness)
        selected = self.record["selected_rails"][0]
        ids = self.capture["groups"][selected["branches"][0]["group"]]
        pad = next(o for o in self.capture["objects"] if o["uuid"] in ids and o["kind"] == "PAD" and o["pin"])
        row = next(r for r in witness["supply_pads"] if (r["ref"], r["pin"]) == (pad["ref"], pad["pin"]))
        row["native_connected_to_source"] = False
        witness["connected_supply_pads"] -= 1
        with self.assertRaisesRegex(AssertionError, "island not native connected"):
            audit.verify_witnesses(witness, self.capture, self.record)


if __name__ == "__main__":
    unittest.main()
