import copy
import json
import unittest

from .review import errors
from .stage import OUT, REPO


class RepairedScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((OUT / "verification.json").read_text())
        cls.s = json.loads((OUT / "scene.json").read_text())

    def test_source_and_actual_mesh_evidence(self):
        self.assertEqual(errors(), [])

    def test_all_mandatory_cases_present(self):
        self.assertTrue(self.r["complete_required_case_set"])
        self.assertEqual(len(self.r["cases"]), 45)

    def test_missing_required_solid_rejected(self):
        name = str((OUT / "whole_geometry.stl").relative_to(REPO))
        self.assertTrue(errors(overrides={name: None}))

    def test_forged_nonempty_as_empty_rejected(self):
        r = copy.deepcopy(self.r)
        a = r["cases"]["whole_geometry"]
        a["empty"] = True
        a["returncode"] = 1
        a["statistics"] = None
        self.assertTrue(errors(report=r))

    def test_actual_bores_must_match_native(self):
        s = copy.deepcopy(self.s)
        s["native_boards"][0]["all_actual_drilled_pad_bores"].pop()
        self.assertTrue(errors(scene=s))

    def test_new_receiver_bores_must_match_native(self):
        s = copy.deepcopy(self.s)
        s["receiver_holes"][0][2] = 5
        self.assertTrue(errors(scene=s))

    def test_j29_cannot_use_rounded_pre_serialization_box(self):
        s = copy.deepcopy(self.s)
        b = next(b for b in s["inherited_envelopes"] if b[0] == "e19_J29")
        b[1] += 0.005
        self.assertTrue(any("J29 body" in e for e in errors(scene=s)))

    def test_rear_row_cannot_be_silently_reverted(self):
        s = copy.deepcopy(self.s)
        s["rear_ports"][0][3] -= 0.8
        self.assertTrue(any("rear interface" in e for e in errors(scene=s)))

    def test_NoError_required_for_actual_Boolean(self):
        path = OUT / "whole_geometry.log"
        name = str(path.relative_to(REPO))
        data = path.read_bytes().replace(b"NoError", b"Unknown")
        self.assertTrue(any("missing native NoError" in e for e in errors(overrides={name: data})))

    def test_clearance_controls_are_outside_nominal(self):
        r = self.r["cases"]
        b = next(b for b in self.s["native_boxes"] if b[0] == "E28_U18")
        self.assertLess(r["native_component_clearance_positive_control"]["statistics"]["max_mm"][0], b[1])
        self.assertTrue(r["native_nominal_strip_negative_control_collision"]["empty"])
        self.assertTrue(r["native_cylinder_nominal_negative_control_collision"]["empty"])

    def test_no_mfg_or_thermal_pass(self):
        r = copy.deepcopy(self.r)
        r["physical_qualified"] = True
        r["thermal_qualified"] = True
        self.assertTrue(errors(report=r))


if __name__ == "__main__":
    unittest.main()
