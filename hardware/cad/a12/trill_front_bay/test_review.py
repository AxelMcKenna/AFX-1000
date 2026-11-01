import copy
import json
import unittest

from .build import OUT, REPO
from .review import errors, mesh


class FrontBay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((OUT / "analysis.json").read_text())
        cls.n = json.loads((OUT / "verification.json").read_text())

    def test_actual_saved_contract(self):
        self.assertEqual(errors(), [])

    def test_old_tight_post_pose_rejected(self):
        m = copy.deepcopy(self.m)
        m["origin_mm"][1] = 156.6
        self.assertTrue(errors(meta=m))

    def test_nominal_hole_cannot_be_promoted_to_guarantee(self):
        m = copy.deepcopy(self.m)
        m["minimum_bore_manufacturer_guaranteed"] = True
        self.assertTrue(errors(meta=m))

    def test_failed_sensitivity_cannot_be_accepted(self):
        n = copy.deepcopy(self.n)
        n["relative_0p3_sensitivity_accepted"] = True
        self.assertTrue(errors(native=n))

    def test_guide_installed_access_cannot_be_accepted(self):
        n = copy.deepcopy(self.n)
        n["panel_and_guide_installed_tool_access_clear"] = True
        self.assertTrue(errors(native=n))

    def test_missing_posts_not_accepted(self):
        key = str((OUT / "posts_geometry.stl").relative_to(REPO))
        self.assertTrue(errors(overrides={key: None}))

    def test_forged_empty_row_with_real_sensitivity_mesh(self):
        n = copy.deepcopy(self.n)
        n["cases"]["bore_relative_0p3_rejected_sensitivity"]["empty"] = True
        self.assertTrue(errors(native=n))

    def test_primitive_requires_actual_closed_bounds_volume(self):
        n = copy.deepcopy(self.n)
        n["cases"]["growth_slab_geometry"]["named_primitive_topology_and_dimensions_verified"] = False
        self.assertTrue(errors(native=n))

    def test_independent_slab_has_exact_eight_vertices(self):
        m = mesh((OUT / "growth_slab_geometry.stl").read_bytes())
        self.assertEqual(m["vertex_count"], 8)
        self.assertEqual(m["edges_not_two"], 0)
        self.assertEqual(m["collapsed"], 0)

    def test_washer_does_not_gain_unproven_engagement(self):
        self.assertEqual(self.m["nominal_engagement_without_washer_mm"], 4.4)
        self.assertFalse(self.m["washer_thickness_and_actual_engagement_approved"])

    def test_no_physical_pass(self):
        n = copy.deepcopy(self.n)
        n["physical_qualified"] = True
        self.assertTrue(errors(native=n))


if __name__ == "__main__":
    unittest.main()
