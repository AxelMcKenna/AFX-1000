"""Portable evidence/physical-boundary mutations; actual SciPy replay is optional."""

import copy
import os
import tempfile
import unittest
from pathlib import Path

from . import analyze, physics, validate
from .native_geometry import metadata


class FanlessFeasibility(unittest.TestCase):
    def setUp(self):
        self.a = analyze.read(analyze.OUT / "analysis.json")

    def test_saved_source_native_and_seal_integrity(self):
        self.assertEqual(validate.packet_errors(), [])
        self.assertEqual(validate.seal_errors(), [])

    def test_more_tightly_spaced_area_does_not_mean_same_h(self):
        tight = physics.downward_h(0.004, 65)["h"]
        open_gap = physics.downward_h(0.010, 65)["h"]
        self.assertLess(tight, open_gap)
        self.assertLess(tight, 1.2)
        self.assertGreater(open_gap, 1.6)
        self.assertFalse(physics.plate_fins(14, 3, 40, 65)["geometry_within_original_paper_range"])
        with self.assertRaises(ValueError):
            physics.downward_h(0.1, 65)

    def test_radiation_has_exterior_envelope_not_each_fin_full_room_view(self):
        r = physics.plate_fins(14, 3, 20, 65)
        self.assertLess(r["external_radiation_envelope_m2"], r["total_wetted_area_m2"])
        self.assertAlmostEqual(
            r["external_radiation_envelope_m2"], 0.334 * 0.157 + 2 * (0.334 + 0.157) * 0.020
        )
        self.assertLess(r["radiation_black_envelope_upper_w"], 15)
        with self.assertRaises(ValueError):
            physics.radiation(0.05, 65, emissivity=1.1)

    def test_vent_head_and_two_opening_series_loss(self):
        r = physics.stack_required_openings(35.43154587633119, 36, 25, 0.6)
        self.assertGreater(r["each_of_two_openings_cm2"], 120)
        self.assertLess(r["velocity_head_ideal_m_s"], 0.25)
        with self.assertRaises(ValueError):
            physics.stack_required_openings(5, 0, 25, 0.6)
        self.assertTrue(self.a["horizontal_channel_inlet_outlet_same_height_has_no_vertical_chimney_head"])

    def test_bottom_control_failure_and_seam_sensitivity_retained(self):
        self.assertTrue(
            all(
                r["capacity_black_aperture_plus20percent_h_control_w"] < self.a["heat_target_w"]
                for r in self.a["bottom_arrays"]
            )
        )
        rows = [r for r in self.a["metal_shell_proposals"] if r["base_prescribed_c"] == 65]
        self.assertGreater(
            rows[0]["complete_same_envelope_capacity_screen_w"],
            rows[1]["complete_same_envelope_capacity_screen_w"],
        )
        self.assertGreater(
            rows[1]["complete_same_envelope_capacity_screen_w"],
            rows[2]["complete_same_envelope_capacity_screen_w"],
        )
        self.assertLess(rows[1]["complete_same_envelope_capacity_screen_w"], self.a["heat_target_w"])
        self.assertLess(
            abs(
                self.a["lid_refinement"][-1]["heat_accepted_from_base_w"]
                - self.a["lid_refinement"][-2]["heat_accepted_from_base_w"]
            ),
            0.05,
        )

    def test_forged_guarantee_nonconvergence_and_target_reduction_rejected(self):
        bad = copy.deepcopy(self.a)
        bad["heat_target_w"] -= 1
        self.assertTrue(validate.errors(bad))
        bad = copy.deepcopy(self.a)
        bad["metal_shell_proposals"][0]["installed_guarantee"] = True
        self.assertTrue(validate.errors(bad))
        bad = copy.deepcopy(self.a)
        bad["lid_refinement"][0]["heat_accepted_from_base_w"] = float("nan")
        self.assertTrue(validate.errors(bad))
        bad = copy.deepcopy(self.a)
        bad["installed_h_lower_bound"] = 3
        self.assertTrue(validate.errors(bad))

    def test_missing_empty_required_native_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.stl"
            p.write_text("solid empty\nendsolid empty\n")
            with self.assertRaises(ValueError):
                metadata(p)
        b = self.a["native_geometry"]["parts"]["bottom"]
        self.assertGreater(b["volume_mm3"], 500000)
        self.assertEqual(b["bounds_mm"][0][2], -26.2)
        self.assertEqual(b["zero_area_faces"], 0)

    def test_removed_actual_native_face_exposes_open_boundary(self):
        import re

        source = (analyze.OUT / "lid.stl").read_text()
        removed = re.sub(r"facet normal.*?endfacet", "", source, count=1, flags=re.S)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "open.stl"
            p.write_text(removed)
            self.assertGreater(metadata(p)["nonmanifold_edges"], 0)

    @unittest.skipUnless(
        os.environ.get("AFX_FANLESS_SOLVER_TEST") == "1", "Optional actual SciPy geometry/sensitivity replay"
    )
    def test_actual_masked_lid_replay_and_finite_seam_loss(self):
        p, e = analyze.masks((67, 32))
        a, _ = physics.lid_shell(65, p, e, 1, 0.8, 167, 0, grid=(67, 32))
        b, _ = physics.lid_shell(65, p, e, 1, 0.8, 167, 0.2, grid=(67, 32))
        self.assertAlmostEqual(
            a["heat_accepted_from_base_w"], self.a["lid_refinement"][0]["heat_accepted_from_base_w"], places=6
        )
        self.assertGreater(a["heat_accepted_from_base_w"], b["heat_accepted_from_base_w"])
        self.assertTrue(a["converged"])


if __name__ == "__main__":
    unittest.main()
