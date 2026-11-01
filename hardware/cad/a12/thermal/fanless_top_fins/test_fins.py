"""Native-area/conservation/false-guarantee mutations; optional actual solver replay."""

import copy
import os
import unittest

from . import analyze, validate


class TopFins(unittest.TestCase):
    def setUp(self):
        self.a = analyze.read(analyze.OUT / "analysis.json")

    def test_actual_saved_source_and_seals(self):
        self.assertEqual(validate.packet_errors(), [])
        self.assertEqual(validate.seal_errors(), [])

    def test_native_area_transferred_without_fictitious_fin_area(self):
        x = self.a["areas"]
        self.assertAlmostEqual(x["native_vertical_area_m2"], 0.0322232295352, places=11)
        self.assertLess(abs(x["vertical_area_residual_m2"]), 1e-10)
        self.assertLess(abs(x["root_area_residual_m2"]), 1e-10)
        bad = copy.deepcopy(self.a)
        bad["areas"]["vertical_area_residual_m2"] = 0.001
        self.assertTrue(validate.errors(bad))

    def test_native_lid_single_component_and_height_envelope(self):
        g = self.a["native"]["lid_with_fins"]
        self.assertEqual(g["connected_components"], 1)
        self.assertEqual(g["bounds_mm"][1][2], 56)
        self.assertEqual(g["nonmanifold_edges"], 0)
        self.assertLess(self.a["fin_top_z"], self.a["control_top_nominal_z"])

    def test_triangle_and_line_clipping_conservation(self):
        self.assertAlmostEqual(analyze.clip_polygon([[0, 0], [2, 0], [0, 2]], [0, 0, 1, 1]), 1)
        self.assertAlmostEqual(analyze.line_fraction([0, 0], [2, 0], [0, 0, 1, 1]), 0.5)
        self.assertEqual(analyze.line_fraction([0, 2], [2, 2], [0, 0, 1, 1]), 0)

    def test_seam_and_flow_failures_not_erased_by_nominal_case(self):
        rows = [r for r in self.a["cases"] if r["base_prescribed_c"] == 65]
        self.assertGreater(rows[1]["conditional_margin_w"], 0)
        self.assertLess(rows[-2]["conditional_margin_w"], 0)
        self.assertLess(rows[-1]["total_conditional_rejection_w"], rows[-2]["total_conditional_rejection_w"])
        self.assertTrue(
            all(r["conditional_margin_w"] < 0 for r in self.a["cases"] if r["base_prescribed_c"] == 60)
        )

    def test_implausible_qualification_or_extra_radiation_rejected(self):
        bad = copy.deepcopy(self.a)
        bad["thermal_qualified"] = True
        self.assertTrue(validate.errors(bad))
        bad = copy.deepcopy(self.a)
        bad["cases"][0]["extra_fin_radiation_credit_w"] = 2
        self.assertTrue(validate.errors(bad))
        bad = copy.deepcopy(self.a)
        bad["fin_neighbor_preheat_or_installed_h_bound"] = 5
        self.assertTrue(validate.errors(bad))

    @unittest.skipUnless(
        os.environ.get("AFX_TOP_FIN_SOLVER_TEST") == "1", "Optional actual native-area/SciPy replay"
    )
    def test_actual_solver_and_native_extraction(self):
        import numpy as np

        from .physics import lid_shell

        fa, root, area = analyze.extract((134, 64))
        p, e = analyze.masks((134, 64))
        e = np.maximum(0, e.astype(float) - root)
        r, _ = lid_shell(65, p, e, 0.7, 0.8, 140, 0.2, grid=(134, 64), fin_areas=fa, fin_face_fraction=1)
        saved = next(
            x
            for x in self.a["cases"]
            if x["base_prescribed_c"] == 65
            and x["joint_r_assumed_k_per_w"] == 0.2
            and x["extra_fin_face_fraction_assumed"] == 1
        )
        self.assertAlmostEqual(r["heat_accepted_from_base_w"], saved["heat_accepted_from_base_w"], places=6)
        self.assertLess(abs(area["vertical_area_residual_m2"]), 1e-10)


if __name__ == "__main__":
    unittest.main()
