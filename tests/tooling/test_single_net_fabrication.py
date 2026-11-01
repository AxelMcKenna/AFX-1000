"""Reject copper substitutions outside the reviewed net or authored geometry."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import first, read_sexpr
from hardware.fabrication.audit_candidate import native_evidence_errors
from hardware.fabrication.audit_single_net import open_counts, unchanged_except_net


class SingleNetBoundary(unittest.TestCase):
    def setUp(self):
        self.old = read_sexpr('''(kicad_pcb (version 20260101)
          (footprint "PART" (at 1 2) (pad "1" smd rect (net "/SENSE")))
          (segment (start 1 2) (end 3 4) (net "/LOGIC"))
          (segment (start 5 6) (end 7 8) (net "/SENSE"))
          (zone (net "/AGND") (polygon (pts (xy 0 0) (xy 10 0) (xy 10 10)))
            (filled_polygon (pts (xy 1 1) (xy 9 1) (xy 9 9)))))''')

    def test_only_target_copper_and_generated_fill_can_change(self):
        new = copy.deepcopy(self.old)
        first(first(new,"segment"),"end")[1] = 6
        first(first(first(new,"zone"),"filled_polygon"),"pts")[1][1] = 2
        self.assertTrue(unchanged_except_net(self.old,new,"/LOGIC"))
        first(first(first(new,"zone"),"polygon"),"pts")[1][1] = 2
        self.assertFalse(unchanged_except_net(self.old,new,"/LOGIC"))

    def test_pad_or_non_target_copper_changes_are_rejected(self):
        for tag in ("footprint","segment"):
            with self.subTest(tag=tag):
                new = copy.deepcopy(self.old)
                if tag == "footprint":
                    first(first(new,tag),"at")[1] = 1.01
                else:
                    first(new,tag).append(read_sexpr('(width .1)'))
                    first(first(new,tag),"net")[1] = "/SENSE"
                self.assertFalse(unchanged_except_net(self.old,new,"/LOGIC"))

    def test_ambiguous_native_net_pair_cannot_claim_progress(self):
        row = dict(unconnected_items=[dict(items=[dict(description="Pad [/LOGIC]"),dict(description="Track [/LOGIC]")])])
        self.assertEqual(open_counts(row),{"/LOGIC":1})
        row["unconnected_items"][0]["items"][1]["description"] = "Track [/SENSE]"
        with self.assertRaises(AssertionError):
            open_counts(row)

    def test_changed_role_selections_retain_current_strict_native_evidence(self):
        repo = Path(__file__).resolve().parents[2]
        scope = json.loads((repo/"hardware/fabrication/scope.json").read_text())
        for row in scope["roles"]:
            if row["role"] in ("negative_startup_protection","rail_monitor"):
                with self.subTest(role=row["role"]):
                    report = json.loads((repo/row["native_review"]).read_text())
                    self.assertEqual(native_evidence_errors(repo/row["source"],report),[])
                    self.assertEqual(report["status"]["counts"]["violations"],0)
                    self.assertEqual(report["status"]["counts"]["schematic_parity"],0)
        self.assertFalse(scope["fabrication_released"])


if __name__ == "__main__":
    unittest.main()
