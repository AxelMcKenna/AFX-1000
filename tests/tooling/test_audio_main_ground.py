"""Ground-plane failures that a zero short/clearance count cannot establish."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_ground as audit


class AudioMainGround(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved=read_sexpr((audit.OUT/"audio_core.kicad_pcb").read_text())
        cls.escapes=json.loads((audit.OUT/"escape-construction.json").read_text())
        cls.pads=json.loads((audit.OUT/"native-pad-capture.json").read_text())
        cls.ground=json.loads((audit.OUT/"ground-connectivity-review.json").read_text())

    def setUp(self):
        self.board=copy.deepcopy(self.saved)
        self.record=copy.deepcopy(self.escapes)

    def verify(self):
        return audit.verify_board(self.board,self.record,self.pads)

    def test_source_bound_receipt_replays(self):
        self.assertEqual(audit.check(),json.loads((audit.OUT/"routing-handoff.json").read_text()))

    def test_plane_requires_legacy_net_name(self):
        plane=next(z for z in children(self.board,"zone") if not children(z,"keepout"))
        first(plane,"net_name")[1]=""
        with self.assertRaisesRegex(AssertionError,"Unassigned ground plane"):
            self.verify()

    def test_missing_sensitive_node_plane_opening_fails(self):
        zone=next(z for z in children(self.board,"zone") if children(z,"layers") and
                  set(first(z,"layers")[1:])=={"In1.Cu","In2.Cu"})
        self.board.remove(zone)
        with self.assertRaisesRegex(AssertionError,"exclusions"):
            self.verify()

    def test_parent_compensation_copper_cannot_be_deleted(self):
        self.board.remove(children(self.board,"segment")[0])
        with self.assertRaisesRegex(AssertionError,"critical copper"):
            self.verify()

    def test_unreviewed_component_move_fails(self):
        first(audit.fps(self.board)["C310"],"at")[1]=95
        with self.assertRaisesRegex(AssertionError,"receiving"):
            self.verify()

    def test_ground_report_must_cover_every_real_terminal(self):
        report=copy.deepcopy(self.ground)
        report["ground_pads"].pop()
        with self.assertRaises(AssertionError):
            audit.verify_ground_witness(report,self.pads)

    def test_disconnected_ground_cannot_be_hidden_by_total_count(self):
        report=copy.deepcopy(self.ground)
        report["ground_pads"][0]["native_connected_to_input_ground"]=False
        with self.assertRaisesRegex(AssertionError,"Unconnected ground"):
            audit.verify_ground_witness(report,self.pads)


if __name__=="__main__":
    unittest.main()
