"""Fault checks for local endpoint completion and declared receiving changes."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_repack as audit


class AudioMainRepack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved=read_sexpr((audit.OUT/"audio_core.kicad_pcb").read_text())
        cls.construction=json.loads((audit.OUT/"construction.json").read_text())
        cls.pads=json.loads((audit.OUT/"native-pad-capture.json").read_text())

    def setUp(self):
        self.board=copy.deepcopy(self.saved)
        self.record=copy.deepcopy(self.construction)

    def verify(self):
        return audit.verify_delta(self.board,self.record,self.pads)

    def test_source_bound_receipt_replays(self):
        self.assertEqual(audit.check(),json.loads((audit.OUT/"routing-handoff.json").read_text()))

    def test_unreviewed_amplifier_move_fails(self):
        first(audit.fps(self.board)["U102"],"at")[1]=45.1
        with self.assertRaisesRegex(AssertionError,"critical pose"):
            self.verify()

    def test_compensation_track_removal_fails(self):
        self.board.remove(children(self.board,"segment")[0])
        with self.assertRaises(AssertionError):
            self.verify()

    def test_original_route_budget_cannot_be_relaxed(self):
        row=next(r for r in self.record["added_routes"] if r["ref"]=="C127")
        row["route_length_limit_mm"]=6.4
        with self.assertRaises(AssertionError):
            self.verify()

    def test_escape_drill_increase_fails(self):
        ident=self.record["added_routes"][0]["via_uuids"][0]
        via=next(v for v in children(self.board,"via") if first(v,"uuid")[1]==ident)
        first(via,"drill")[1]=.4
        with self.assertRaises(AssertionError):
            self.verify()


if __name__=="__main__":
    unittest.main()
