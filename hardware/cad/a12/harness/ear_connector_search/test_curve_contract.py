"""Portable independent model/native mutation checks; optional denseSDF replay."""

import copy
import math
import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from . import review
from .bezier import certificate


class CurveContract(unittest.TestCase):
    def setUp(self):
        self.data = review.read(review.OUT / "selected-paths.json")

    def test_frozen_source_model_and_all21_actual_native_artifacts(self):
        self.assertEqual(review.packet_errors(), [])
        self.assertEqual(review.seal_errors(), [])

    def test_exact_endpoints_and_source_stub_boundaries(self):
        self.assertEqual(review.model_errors(self.data), [])
        for route in self.data["routes"]:
            points = route["native_points_mm"]
            idx = route["native_boundary_indices"]
            self.assertEqual(points[0], route["source_face_mm"])
            self.assertTrue(
                review.close(
                    points[idx["source_initial_straight_end"]], route["source_initial_straight_end_mm"]
                )
            )
            self.assertTrue(
                review.close(points[idx["destination_stub_start"]], route["destination_stub"]["start"])
            )
            self.assertTrue(review.close(points[-1], route["destination_stub"]["finish"]))
            self.assertEqual(route["destination_stub"]["remaining_straight_insulated_length_mm"], 3.9)

    def test_bernstein_intervals_cover_continuum_and_positive_speed(self):
        route = self.data["routes"][1]
        proof = route["continuous_radius_certificate"]
        leaves = sorted(proof["leaves"], key=lambda r: Decimal(r["t0"]))
        end = Decimal(0)
        for row in leaves:
            self.assertEqual(Decimal(row["t0"]), end)
            end = Decimal(row["t1"])
            self.assertGreater(row["speed_lower_local_parameter"], 0)
            self.assertLess(row["kappa_upper_per_mm"], 1 / 9.6393)
        self.assertEqual(end, Decimal(1))
        self.assertGreater(proof["radius_lower_mm"], 9.6393)
        self.assertEqual(certificate(route["connector_model"]["control_points_mm"], 9.6393), proof)

    def test_independent_derivative_crosscheck_is_below_interval_bound(self):
        # A sample crosscheck catches coefficient/exponent mistakes; interval proof remains mandatory.
        route = self.data["routes"][1]
        p = route["connector_model"]["control_points_mm"]
        upper = route["continuous_radius_certificate"]["curvature_upper_per_mm"]
        for i in range(1001):
            t = i / 1000
            u = 1 - t
            v = [
                3
                * (
                    u * u * (p[1][j] - p[0][j])
                    + 2 * u * t * (p[2][j] - p[1][j])
                    + t * t * (p[3][j] - p[2][j])
                )
                for j in range(3)
            ]
            a = [
                6 * (u * (p[2][j] - 2 * p[1][j] + p[0][j]) + t * (p[3][j] - 2 * p[2][j] + p[1][j]))
                for j in range(3)
            ]
            cross = [v[1] * a[2] - v[2] * a[1], v[2] * a[0] - v[0] * a[2], v[0] * a[1] - v[1] * a[0]]
            k = math.sqrt(sum(x * x for x in cross)) / math.sqrt(sum(x * x for x in v)) ** 3
            self.assertLessEqual(k, upper + 1e-12)

    def test_degenerate_or_tight_cubic_is_not_certified(self):
        self.assertFalse(certificate([[0, 0, 0]] * 4, 9.6393, max_depth=2)["certified"])
        self.assertFalse(
            certificate([[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 1, -0.1]], 9.6393, max_depth=2)["certified"]
        )

    def test_changed_controls_or_native_path_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["routes"][1]["connector_model"]["control_points_mm"][2][0] += 0.005
        self.assertTrue(review.model_errors(data))
        data = copy.deepcopy(self.data)
        data["routes"][0]["native_points_mm"][150][0] += 0.1
        self.assertTrue(review.model_errors(data))

    def test_hard_radius_strip_length_and_clearance_cannot_be_weakened(self):
        for key, value in [
            ("minimum_required_true_centerline_radius_mm", 9.5),
            ("independent_position_allocation_each_wire_mm", 0.3),
            ("separate_required_clearance_mm", 0.1),
        ]:
            data = copy.deepcopy(self.data)
            data[key] = value
            self.assertTrue(review.model_errors(data))
        data = copy.deepcopy(self.data)
        data["routes"][0]["destination_stub"]["bare_length_above_face_mm"] = 2
        self.assertTrue(review.model_errors(data))

    def test_length_chord_height_and_physical_mutations_rejected(self):
        data = copy.deepcopy(self.data)
        data["routes"][0]["wire_length_upper_mm_including_prefix_stub_boardtails"] -= 1
        self.assertTrue(review.model_errors(data))
        data = copy.deepcopy(self.data)
        data["routes"][1]["sample_contract"]["native"]["whole_chord_error_bound_mm"] = 0
        self.assertTrue(review.model_errors(data))
        data = copy.deepcopy(self.data)
        data["central_height_proof"]["minimum_height_margin_mm"] += 1
        self.assertTrue(review.model_errors(data))
        data = copy.deepcopy(self.data)
        data["H9_vertical_tool_access_clear"] = True
        self.assertTrue(review.model_errors(data))

    def test_forged_empty_collision_with_actual_STL_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            name = "full_pair_collision"
            shutil.copy2(review.EVIDENCE / "full_middle_positive_control.stl", folder / (name + ".stl"))
            (folder / (name + ".log")).write_text("Current top level object is empty.\n")
            self.assertTrue(review.case_errors(name, {"clear": True, "empty": True}, folder))

    def test_missing_required_mesh_failed_control_or_collision_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            name = "full_geometry"
            (folder / (name + ".log")).write_text("Current top level object is empty.\n")
            self.assertTrue(review.case_errors(name, {"clear": True, "empty": True}, folder))
            name = "full_middle_positive_control"
            shutil.copy2(review.EVIDENCE / (name + ".stl"), folder / (name + ".stl"))
            shutil.copy2(review.EVIDENCE / (name + ".log"), folder / (name + ".log"))
            row = review.read(review.EVIDENCE / "verification.json")["cases"][name].copy()
            row["volume_mm3"] = 0
            self.assertTrue(review.case_errors(name, row, folder))
            self.assertTrue(review.case_errors(name, {"clear": False}, folder))

    @unittest.skipUnless(
        os.environ.get("AFX_EAR_CURVE_REPLAY") == "1", "Optional NumPy/VTK/SciPy dense clearance replay"
    )
    def test_actual_dense_curve_pair_and_obstacle_replay(self):
        from . import search

        data = copy.deepcopy(self.data)
        obs = search.obstacles()
        source = {r["pin"]: r["source_prefix_profile"] for r in data["routes"]}
        a, b = [r["connector_model"] for r in data["routes"]]
        for row in [a, b]:
            checked = search.individual([row], obs, 0.02)[0]
            self.assertTrue(checked["sample_cover_clear"])
        margin, _ = search.pair(a, b, source, 0.02)
        self.assertAlmostEqual(margin, data["dense_pair_clearance_lower_estimate_mm"], places=9)


if __name__ == "__main__":
    unittest.main()
