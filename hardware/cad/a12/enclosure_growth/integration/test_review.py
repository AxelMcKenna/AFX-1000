import copy
import json
import unittest

from .review import errors
from .stage import OUT, REPO


class IntegratedTrial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((OUT / "verification.json").read_text())
        cls.scene = json.loads((OUT / "scene.json").read_text())

    def test_saved_rejected_trial_is_valid_evidence(self):
        self.assertEqual(errors(), [])

    def test_exact_three_failures_remain_false(self):
        self.assertEqual(
            {n for n, r in self.report["cases"].items() if not r["clear"]},
            {
                "case_electronics_collision",
                "power_electronics_collision",
                "trill_other_electronics_collision",
            },
        )
        self.assertFalse(self.report["all_requested_native_geometry_checks_clear"])

    def test_forged_empty_row_with_actual_collision_mesh_rejected(self):
        r = copy.deepcopy(self.report)
        v = r["cases"]["power_electronics_collision"]
        v["clear"] = True
        v["empty"] = True
        v["returncode"] = 1
        v["statistics"] = None
        self.assertTrue(errors(r))

    def test_missing_required_receiver_solid_rejected(self):
        name = str((OUT / "receiver_PCB_geometry.stl").relative_to(REPO))
        self.assertTrue(errors(overrides={name: None}))

    def test_clean_positive_mesh_without_NoError_rejected(self):
        p = OUT / "receiver_PCB_geometry.log"
        name = str(p.relative_to(REPO))
        data = p.read_bytes().replace(b"NoError", b"Unknown")
        self.assertTrue(any("missing native NoError" in e for e in errors(overrides={name: data})))

    def test_dropped_terminal_bore_rejected(self):
        s = copy.deepcopy(self.scene)
        holes = s["native_boards"][0]["all_actual_drilled_pad_bores"]
        holes.pop()
        self.assertTrue(any("actual bores" in e for e in errors(scene=s)))

    def test_receiver_bore_enlargement_rejected(self):
        s = copy.deepcopy(self.scene)
        s["receiver_holes"][0][2] = 9
        self.assertTrue(any("receiver bores" in e for e in errors(scene=s)))

    def test_status_row_forgery_rejected(self):
        r = copy.deepcopy(self.report)
        r["cases"]["whole_geometry"]["native_boolean_status_no_error"] = False
        self.assertTrue(errors(r))

    def test_overall_and_physical_pass_forgery_rejected(self):
        r = copy.deepcopy(self.report)
        r["all_requested_native_geometry_checks_clear"] = True
        r["physical_qualified"] = True
        self.assertTrue(errors(r))

    def test_private_TC_modules_cannot_shadow_aperture(self):
        s = (OUT / "trill-derived.scad").read_text()
        self.assertIn("module tc_aperture()", s)
        self.assertNotIn("module aperture()", s)
        for token in ["saddle", "board", "components", "tails", "hardware", "corners"]:
            self.assertIn("module tc_" + token + "(", s)

    def test_all_native_drilled_material_coverage(self):
        self.assertEqual(
            [len(b["all_actual_drilled_pad_bores"]) for b in self.scene["native_boards"]], [40, 45]
        )
        self.assertEqual(len(self.scene["receiver_holes"]), 142)

    def test_all_controls_use_real_nonzero_boolean_mesh(self):
        rows = [r for r in self.report["cases"].values() if r["role"] == "control"]
        self.assertEqual(len(rows), 7)
        self.assertTrue(
            all(
                r["native_boolean_status_no_error"] and r["statistics"]["volume_mm3"] > 0.007999 for r in rows
            )
        )


if __name__ == "__main__":
    unittest.main()
