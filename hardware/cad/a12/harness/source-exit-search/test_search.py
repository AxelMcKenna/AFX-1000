"""Read-only geometry-boundary and native-reference regression checks."""

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import vtk
from search import ROOT, Surface, pair_gap, profile


class ExitSearchTests(unittest.TestCase):
    def test_clipped_window_cannot_create_feasible_wire(self):
        self.assertLess(profile("1", 16, -90, 31, 0.1)["window_margin_mm"], 0)
        self.assertGreater(profile("1", 16, -60, 31, 0.1)["window_margin_mm"], 0)
        with self.assertRaises(AssertionError):
            profile("1", 9.63, 0, 25, 0.1)
        self.assertIsNone(profile("1", 16, 0, 18, 0.1))

    def test_pair_uses_both_independent_position_allocations(self):
        a, b = profile("1", 10, 0, 25, 0.1), profile("2", 10, 0, 25, 0.1)
        gap, _ = pair_gap(a, b)
        x = a["pieces"][1]
        y = b["pieces"][1]
        expected = 6 - x["pair_radius_mm"] - y["pair_radius_mm"] - x["cover_mm"] - y["cover_mm"]
        self.assertAlmostEqual(gap, expected, places=9)
        expected_radius = (1.7526 / 2 + 0.65 + 0.005 + 0.125) / math.cos(math.pi / 64) ** 2 + 10 * (
            math.pi / 240
        ) ** 2 / 8
        self.assertAlmostEqual(x["pair_radius_mm"], expected_radius, places=12)

    def test_open_triangle_surface_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="afx-exit-open-test-") as directory:
            plane = vtk.vtkPlaneSource()
            plane.Update()
            triangles = vtk.vtkTriangleFilter()
            triangles.SetInputData(plane.GetOutput())
            triangles.Update()
            path = Path(directory) / "open.stl"
            writer = vtk.vtkSTLWriter()
            writer.SetInputData(triangles.GetOutput())
            writer.SetFileName(str(path))
            writer.Write()
            with self.assertRaisesRegex(AssertionError, "Open STL boundary"):
                Surface(path)

    def test_known_native_failure_and_selected_metadata_are_not_qualification(self):
        reference = json.loads((ROOT / "reference-check.json").read_text())
        self.assertTrue(reference["screen_detects_known_hardware_failure"])
        self.assertTrue(reference["screen_does_not_introduce_component_or_case_failure"])
        self.assertTrue(reference["screen_pair_clear"])
        self.assertGreater(reference["known_native_hardware_hit_volume_mm3"], 28)
        report = json.loads((ROOT / "selected-refined-pairs.json").read_text())
        self.assertFalse(report["native_geometry_pass"])
        self.assertFalse(report["physical_fit_verified"])
        self.assertFalse(report["fabrication_released"])
        self.assertEqual(report["tight_arc_length_sample_step_mm"], 0.02)
        for name, digest in report["source_evidence_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        for row in report["selected_candidates"]:
            self.assertGreater(row["minimum_margin_mm"], 0)
            self.assertFalse(row["native_validation_completed"])


if __name__ == "__main__":
    unittest.main()
