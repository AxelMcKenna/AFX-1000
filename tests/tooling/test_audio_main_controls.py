"""Control routing must preserve audio copper and real terminal continuity."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_controls as audit


class AudioMainControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.construction = json.loads((audit.OUT / "construction.json").read_text())
        cls.capture = json.loads((audit.OUT / "native-inputs.json").read_text())
        cls.witness = json.loads((audit.OUT / "control-connectivity-review.json").read_text())

    def setUp(self):
        self.board = copy.deepcopy(self.saved)
        self.record = copy.deepcopy(self.construction)

    def verify(self):
        return audit.verify_board(self.board, self.record, self.capture)

    def test_current_source_bound_receipt_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "routing-handoff.json").read_text()))

    def test_existing_analog_copper_cannot_be_removed(self):
        self.board.remove(children(self.board, "segment")[0])
        with self.assertRaisesRegex(AssertionError, "parent analog copper"):
            self.verify()

    def test_inner_reference_plane_cannot_be_changed(self):
        plane = next(z for z in children(self.board, "zone") if not children(z, "keepout"))
        first(plane, "net_name")[1] = "V3V3_IO"
        with self.assertRaisesRegex(AssertionError, "reference plane"):
            self.verify()

    def test_control_trace_width_is_checked_on_actual_copper(self):
        ident = self.record["routes"][0]["segment_uuids"][0]
        node = next(n for n in children(self.board, "segment") if first(n, "uuid")[1] == ident)
        first(node, "width")[1] = .1
        with self.assertRaisesRegex(AssertionError, "width"):
            self.verify()

    def test_analog_reference_net_cannot_be_routed_as_control(self):
        self.record["routes"][0]["net"] = "REF_ADC1"
        with self.assertRaisesRegex(AssertionError, "Undeclared control net"):
            self.verify()

    def test_one_lost_ground_cannot_be_hidden_by_200_row_total(self):
        witness = copy.deepcopy(self.witness)
        witness["ground_pads"][0]["native_connected_to_input_ground"] = False
        with self.assertRaisesRegex(AssertionError, "Ground connection lost"):
            audit.verify_witnesses(witness, self.record)

    def test_control_connectivity_requires_exact_endpoint_witnesses(self):
        witness = copy.deepcopy(self.witness)
        witness["new_control_pairs"][0]["native_connected"] = False
        with self.assertRaisesRegex(AssertionError, "not all native connected"):
            audit.verify_witnesses(witness, self.record)


if __name__ == "__main__":
    unittest.main()
