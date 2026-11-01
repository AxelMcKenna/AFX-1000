"""Portable source/geometry/continuous-pair mutations for the connector draft."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from .local_fanout import certify
from .study import ROOT, contact_screen, library_contract, phd_pin_xy, sha, wire_fit


class ConnectorStudy(unittest.TestCase):
    def test_captured_inputs(self):
        c = json.loads((ROOT / "capture.json").read_text())
        self.assertTrue(all(sha(ROOT / n) == h for n, h in c["copied_sha256"].items()))
        a = json.loads((ROOT / "generated/analysis.json").read_text())
        self.assertEqual(a["captured_NF05S_parts"], 249)
        self.assertEqual(len(a["NF05S_pincontract"]["J1"]), 30)
        self.assertFalse(a["canonical_PCB_edited"])
        self.assertFalse(a["physical_qualified"])

    def test_actual_PHD30_library(self):
        result = library_contract(
            ROOT / "sources/repository/KiCad/JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod"
        )
        self.assertEqual(len(result["circuits"]), 30)
        self.assertEqual(phd_pin_xy(30), [28, 2])

    def test_pin_mirror_mutation(self):
        source = (
            ROOT / "sources/repository/KiCad/JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod"
        ).read_text()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.kicad_mod"
            p.write_text(source.replace("(at 0 2)", "(at 0 -2)", 1))
            with self.assertRaises(AssertionError):
                library_contract(p)

    def test_missing_physical_pad_mutation(self):
        source = (
            ROOT / "sources/repository/KiCad/JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod"
        ).read_text()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.kicad_mod"
            p.write_text(source.replace('(pad "30"', '(pad "29"', 1))
            with self.assertRaises(AssertionError):
                library_contract(p)

    def test_3051_OD_rejected(self):
        self.assertFalse(wire_fit(0.062, 0.002, 1, 1.5, 10)["OD_inside_contact_window"])
        self.assertTrue(wire_fit(0.051, 0.002, 0.9, 1.5, 10)["OD_inside_contact_window"])

    def test_real_bend_requirement(self):
        self.assertAlmostEqual(
            wire_fit(0.051, 0.002, 0.9, 1.5, 10)["minimum_centerline_bend_radius_mm"], 13.462
        )

    def test_force_contacts_initial_and_after_test(self):
        self.assertFalse(contact_screen(0.01)["within_allocation"])
        self.assertFalse(contact_screen(0.02)["within_allocation"])
        self.assertTrue(contact_screen(0.002)["within_allocation"])
        self.assertFalse(contact_screen(0.004)["within_allocation"])

    def test_force_allocation_cannot_be_zero(self):
        with self.assertRaises(ValueError):
            contact_screen(0.01, allocation=0)

    def test_435_continuous_pair_coverage(self):
        d = json.loads((ROOT / "generated/local-PHD30-fanout.json").read_text())
        self.assertEqual(len(d["certificates"]), 435)
        self.assertTrue(all(v["certified"] for v in d["certificates"].values()))
        self.assertGreater(d["true_minimum_radius_mm"], d["source_required_radius_mm"])
        self.assertFalse(d["sampled_minimum_used"])
        # Actual row pair requires the deliberate stagger, not sample spacing.
        self.assertTrue(
            certify(d["routes"][0], d["routes"][1], d["required_centerline_separation_mm"])["certified"]
        )

    def test_identical_row_arcs_rejected(self):
        d = json.loads((ROOT / "generated/local-PHD30-fanout.json").read_text())
        a, b = copy.deepcopy(d["routes"][:2])
        a["straight_mm"] = 0
        self.assertFalse(certify(a, b, d["required_centerline_separation_mm"])["certified"])

    def test_wire_loss_not_hidden_in_contact_budget(self):
        from .force_pigtail import complete_path_wire

        d = complete_path_wire(0.15)
        self.assertGreater(d["wire_hot_scenario_ohm"], 0.005)
        self.assertFalse(d["wire_hot_qualified_upper_bound"])

    def test_point_path_must_match_certified_curve(self):
        from .audit import fanout_errors

        d = json.loads((ROOT / "generated/local-PHD30-fanout.json").read_text())
        a = json.loads((ROOT / "generated/analysis.json").read_text())
        self.assertEqual(fanout_errors(d, a), [])
        d["routes"][0]["native_points"][3][0] += 0.1
        self.assertIn("point-path-not-certified-curve", fanout_errors(d, a))


if __name__ == "__main__":
    unittest.main()
