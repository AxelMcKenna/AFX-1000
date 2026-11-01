"""Portable saved-evidence and design-contract mutations; no native rerun."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from . import audit
from .ground_route import ROOT, sha
from .verify_v6 import specs


class SavedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = ROOT / "generated/current-native"
        cls.proof = json.loads((cls.folder / "verification.json").read_text())
        cls.g = json.loads((ROOT / "generated/ground-route.json").read_text())
        cls.ret = json.loads((ROOT / "return_variant3/generated/geometry.json").read_text())
        cls.pb = json.loads((ROOT / "positive_variant27/generated/geometry.json").read_text())

    def test_current_complete_saved_artifacts(self):
        self.assertEqual(audit.errors(), [])

    def test_missing_case(self):
        d = copy.deepcopy(self.proof)
        d["cases"].pop("new_wire_pair_collision")
        self.assertIn("required-case-coverage", audit.report_errors(d, specs(), self.folder, True))

    def test_forged_empty_actual_copper(self):
        d = copy.deepcopy(self.proof)
        d["cases"]["new_ANA_return_geometry"].update(statistics=None, returncode=1, clear=True, errors=[])
        self.assertTrue(
            any("new_ANA_return_geometry" in e for e in audit.report_errors(d, specs(), self.folder, True))
        )

    def test_real_guide_clash_cannot_be_promoted(self):
        d = copy.deepcopy(self.proof)
        d["cases"][audit.BLOCKED].update(clear=True, errors=[], statistics=None, returncode=1)
        d["all_requested_clear"] = True
        self.assertIn("blocked-guide-state-not-preserved", audit.report_errors(d, specs(), self.folder, True))

    def test_forged_empty_collision_has_actual_stl(self):
        d = copy.deepcopy(self.proof)
        r = d["cases"][audit.BLOCKED]
        r.update(clear=True, errors=[], statistics=None, returncode=1)
        self.assertIn("blocked-guide-state-not-preserved", audit.report_errors(d, specs(), self.folder, True))

    def test_failed_execution_not_empty(self):
        d = copy.deepcopy(self.proof)
        d["cases"]["new_wire_pair_collision"].update(returncode=137)
        self.assertTrue(audit.report_errors(d, specs(), self.folder, True))

    def test_wrong_positive_control(self):
        d = copy.deepcopy(self.proof)
        d["cases"]["new_R1_control"]["statistics"]["volume_mm3"] = 0.009
        self.assertTrue(audit.report_errors(d, specs(), self.folder, True))

    def test_no_physical_promotion(self):
        d = copy.deepcopy(self.proof)
        d["physical_qualified"] = True
        self.assertIn(
            "unsupported-promotion:physical_qualified", audit.report_errors(d, specs(), self.folder, True)
        )

    def test_file_change_and_missing_detected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "input"
            p.write_text("captured")
            h = sha(p)
            self.assertEqual(audit.hashes_errors({str(p): h}), [])
            p.write_text("changed")
            self.assertTrue(audit.hashes_errors({str(p): h}))
            p.unlink()
            self.assertTrue(audit.hashes_errors({str(p): h}))

    def test_actual_ground_port_is_required(self):
        d = copy.deepcopy(self.g)
        d["source_face_mm"][1] = 126.5
        self.assertIn("changed-wire-contract:source_face_mm", audit.contract_errors(d, self.ret, self.pb))

    def test_radius_and_allowance_not_reduced(self):
        d = copy.deepcopy(self.g)
        d["continuous_radius_certificate"]["radius_lower_mm"] = 9.63
        d["independent_position_allowance_mm"] = 0.5
        errors = audit.contract_errors(d, self.ret, self.pb)
        self.assertIn("uncertified-continuous-radius", errors)
        self.assertIn("changed-wire-contract:independent_position_allowance_mm", errors)

    def test_return_and_positive_sections(self):
        r = copy.deepcopy(self.ret)
        p = copy.deepcopy(self.pb)
        r["bars"]["ANA"]["minimum_normal_section_mm2"] = 19.99
        p["analytical_minimum_area_mm2"][next(iter(p["analytical_minimum_area_mm2"]))] = 5.99
        errors = audit.contract_errors(self.g, r, p)
        self.assertIn("return-area:ANA", errors)
        self.assertIn("positive-area", errors)

    def test_actual_continuous_certificate_replays(self):
        from hardware.cad.a12.harness.ear_connector_search.bezier import certificate

        actual = certificate(self.g["new_cubic_controls_mm"], required_radius=9.6393, max_depth=12)
        self.assertEqual(actual, self.g["continuous_radius_certificate"])

    def test_packaging_namespace_and_full_object_coverage(self):
        import xml.etree.ElementTree as ET
        import zipfile

        with zipfile.ZipFile(ROOT / "generated/UA01-component-review.3mf") as z:
            d = ET.fromstring(z.read("[Content_Types].xml"))
        self.assertEqual(d.tag, "{http://schemas.openxmlformats.org/package/2006/content-types}Types")
        d = json.loads((ROOT / "generated/assembly-manifest-corrected.json").read_text())
        self.assertEqual(len(d["objects"]), 70)
        self.assertFalse(d["whole_as_one_manufacturable_part"])

    def test_replay_cannot_mutate_packet(self):
        from .replay import validate_destination

        with self.assertRaises(RuntimeError):
            validate_destination(ROOT / "generated/new-output")


if __name__ == "__main__":
    unittest.main()
