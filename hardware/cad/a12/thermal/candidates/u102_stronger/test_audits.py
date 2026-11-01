"""Portable necessary-condition/source-integrity checks, not analog-stability tests."""

import json
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

from .layout_failure import ROOT, facts


class AssumptionAudit(unittest.TestCase):
    def test_exact_historical_plate_reproduction_and_no_upper_claim(self):
        a = json.loads((ROOT / "generated/base-model-audit.json").read_text())
        self.assertEqual(len(a["reproduced_historical_cases"]), 5)
        self.assertTrue(all(r["plate_max_change_c"] == 0 for r in a["reproduced_historical_cases"]))
        self.assertIsNone(a["actual_base_upper_c"])
        self.assertIsNone(a["downstream_scope"]["whole_unit_heat_upper_w"])
        self.assertFalse(a["whole_base_qualified"])

    def test_60_65_are_not_proven_even_under_supply_only_heat(self):
        a = json.loads((ROOT / "generated/base-model-audit.json").read_text())
        rows = {r["h_assumed_w_per_m2k"]: r for r in a["cases"] if r["emissivity_assumed"] == 0.8}
        self.assertGreater(
            rows[1]["local_3x3mm_source_projections"]["U102"]["local_peak_in_3x3mm_projection_c"], 65
        )
        self.assertGreater(rows[2]["plate_max_c"], 60)
        self.assertLess(rows[3]["plate_max_c"], 60)
        self.assertTrue(all(not r["installed_h_is_bounded"] for r in a["conditional_h_thresholds"]))

    def test_source_scope_distinguishes_delivered_power_from_heat(self):
        a = json.loads((ROOT / "generated/base-model-audit.json").read_text())
        self.assertAlmostEqual(a["supply_loss_provision_w"], 10.557756677906315)
        self.assertEqual(a["downstream_scope"]["nominal_digital_delivered_w"], 12)
        self.assertFalse(a["downstream_scope"]["delivered_power_is_measured_internal_heat"])
        self.assertIsNone(a["downstream_scope"]["fraction_into_metal_base"])

    def test_actual_c95_capacitors_fail_same_face_requirements(self):
        a = facts(ROOT / "closed/power_p03.kicad_pcb", ROOT / "closed/components.json")
        self.assertEqual(a["regulator_face"], "F.Cu")
        self.assertEqual(a["actual_input_node"], "VIN_IC")
        self.assertEqual(a["nominal_front_input_total_uf"], 0)
        self.assertEqual(a["actual_input_caps"][0]["ref"], "C102")
        self.assertEqual(a["actual_input_caps"][0]["face"], "B.Cu")
        self.assertFalse(a["intended_bulk_same_face"])
        self.assertAlmostEqual(a["C107_front_nominal_uf"], 0.1)
        self.assertFalse(a["C107_by_itself_can_meet_minimum_even_before_derating"])

    def test_wrong_input_net_cannot_masquerade_as_local_cap(self):
        parts = json.loads((ROOT / "closed/components.json").read_text())
        c = next(p for p in parts if p["ref"] == "C104")
        next(p for p in c["pins"] if p["net"] == "VIN_PROTECTED")["net"] = "VIN_IC"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "parts.json"
            p.write_text(json.dumps(parts))
            with self.assertRaisesRegex(AssertionError, "node disagreement"):
                facts(ROOT / "closed/power_p03.kicad_pcb", p)

    def test_face_change_alone_never_qualifies_stability(self):
        tree = read_sexpr((ROOT / "closed/power_p03.kicad_pcb").read_text())
        for f in children(tree, "footprint"):
            if any(p[1:3] == ["Reference", "C102"] for p in children(f, "property")):
                first(f, "layer")[1] = "F.Cu"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "hypothesis.kicad_pcb"
            p.write_text(sexpr(tree))
            a = facts(p, ROOT / "closed/components.json")
            self.assertGreater(a["nominal_front_input_total_uf"], 0.1)
            self.assertFalse(a["locality_and_ground_path_qualified"])
            self.assertFalse(a["regulator_stability_qualified"])

    def test_saved_audit_input_bytes_stay_bound(self):
        for name in ["base-model-audit.json", "regulator-layout-failure.json"]:
            a = json.loads((ROOT / "generated" / name).read_text())
            for p, expected in a["source_sha256"].items():
                self.assertEqual(sha(REPO / p), expected, p)


if __name__ == "__main__":
    unittest.main()
