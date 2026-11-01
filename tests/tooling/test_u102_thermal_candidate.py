"""Current-source rejected U102 trial; no native solver/download needed in CI."""

import copy
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u102.analyze import path_budget, qualified_acceptance
from hardware.cad.a12.thermal.candidates.u102.baseline import OUT, ROOT
from hardware.cad.a12.thermal.candidates.u102.network import read_construction
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.cad.a12.thermal.verify import binary_stl


class U102Candidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((OUT / "analysis.json").read_text())
        cls.native = json.loads((OUT / "verification.json").read_text())

    def test_immutable_inputs_and_analytical_driver_are_bound(self):
        for path, expected in self.report["source_sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)
        self.assertEqual(sha(OUT / "verification.json"), self.report["native_verification_sha256"])
        self.assertEqual(
            self.report["finer_grid"]["native_pcb_sha256"], sha(ROOT / "sources/power_p03.kicad_pcb")
        )
        self.assertEqual(len(self.report["primary_source"]["sha256"]), 64)

    def test_correct_real_package_and_source_spreading(self):
        row = self.report["finer_grid"]
        self.assertEqual(row["package_theta_jc_c_per_w"], 14.9)
        self.assertEqual(row["native_ep"]["size_mm"], [1.68, 1.88])
        self.assertEqual(row["source_dimensions_mm"], [1.34, 1.66])
        self.assertEqual(row["actual_via_centres_inside_ep"], 6)
        self.assertGreater(row["actual_matching_through_vias"], 6)
        self.assertEqual(row["via_wall_assumed_minimum_um"], 50)
        # Nominal land area is not a fictitious blanket-copper sink.
        self.assertLess(row["sink_area_under_matching_bottom_copper_mm2"], row["metal_contact_area_mm2"] / 4)
        self.assertGreater(row["ep_peak_to_land_network_c_per_w"], 100)

    def test_independent_power_and_energy_identity_rejects_ideal_area_shortcut(self):
        row = self.report["finer_grid"]
        energy = row["unit_heat_energy_decomposition_c_per_w"]
        self.assertAlmostEqual(
            math.fsum(
                [
                    energy["sheet_spreading_total"],
                    energy["via_barrels_all_segments"],
                    energy["tim_bulk_under_actual_bottom_copper"],
                ]
            ),
            row["ep_mean_to_land_network_c_per_w"],
            places=7,
        )
        total = math.fsum(
            [
                14.9,
                row["ep_peak_to_land_network_c_per_w"],
                row["aluminum_land_axial_c_per_w"],
                row["extra_contact_assumed_c_per_w"],
            ]
        )
        self.assertAlmostEqual(row["conditional_total_junction_to_base_c_per_w"], total)
        self.assertAlmostEqual(
            row["conditional_junction_at_60c_base_c"],
            60 + self.report["conservative_heat_allocation_w"] * total,
        )
        self.assertGreater(row["conditional_junction_at_60c_base_c"], 110)
        ideal = 1.22e-3 / (6 * row["metal_contact_area_mm2"] * 1e-6)
        self.assertGreater(energy["tim_bulk_under_actual_bottom_copper"], ideal * 5)

    def test_native_tail_collision_and_real_positive_control_remain_rejected(self):
        self.assertIn("component_collision", self.native["failed_cases"])
        actual = binary_stl(OUT / "component_collision.stl")
        self.assertGreater(actual["volume_mm3"], 2)
        self.assertEqual(
            actual["volume_mm3"], self.native["native_checks"]["component_collision"]["volume_mm3"]
        )
        self.assertFalse(self.native["accepted_native_evidence"])
        witness = binary_stl(OUT / "positive_control.stl")
        self.assertAlmostEqual(witness["volume_mm3"], 0.008, places=5)
        for path, expected in self.native["evidence_sha256"].items():
            self.assertEqual(sha(REPO / path), expected)

    def test_missing_material_and_uncertainty_inputs_cannot_pass(self):
        self.assertFalse(qualified_acceptance(1, 60, None, 0))
        self.assertFalse(qualified_acceptance(None, 60, 20, 0))
        self.assertFalse(qualified_acceptance(1, 60, 20, None))
        self.assertFalse(qualified_acceptance(1, 60, 49, 2))
        self.assertTrue(qualified_acceptance(1, 60, 48, 2))
        for power in [0, -1, float("nan"), True]:
            with self.assertRaises(ValueError):
                path_budget(power)
        self.assertAlmostEqual(
            path_budget(self.report["conservative_heat_allocation_w"]),
            self.report["required_total_path_before_uncertainty_k_per_w"],
        )
        self.assertFalse(self.report["acceptance"]["guardbanded_project_acceptance"])
        self.assertIsNone(self.report["acceptance"]["bounded_total_path_upper_k_per_w"])
        self.assertEqual(self.report["physical_tests_performed"], 0)
        self.assertFalse(self.report["base_modified"])
        self.assertFalse(self.report["pcb_modified"])

    def test_construction_mismatch_and_bad_plating_rejected(self):
        p = ROOT / "sources/construction.json"
        actual = json.loads(p.read_text())
        with self.assertRaises(ValueError):
            read_construction(p, "0" * 64)
        for invalid in [0, -50, None, True, float("nan")]:
            bad = copy.deepcopy(actual)
            bad["via_wall_minimum_required_um"] = invalid
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / "construction.json"
                f.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    read_construction(f, actual["pcb_sha256"])

    @unittest.skipUnless(os.environ.get("AFX_THERMAL_SOLVERS") == "1", "optionalSciPy solver")
    def test_real_saved_copper_responds_to_wall_and_tim_mutations(self):
        from hardware.cad.a12.thermal.candidates.u102.network import solve

        args = dict(
            contact_native=[121, 119.25, 126.7, 122.2], grid=80, pcb_path=ROOT / "sources/power_p03.kicad_pcb"
        )
        thick = solve(**args, via_wall_um=50, tim_k=6)
        thin = solve(**args, via_wall_um=25, tim_k=6)
        poor = solve(**args, via_wall_um=50, tim_k=4)
        self.assertLess(thick["ep_peak_to_land_network_c_per_w"], thin["ep_peak_to_land_network_c_per_w"])
        self.assertLess(thick["ep_peak_to_land_network_c_per_w"], poor["ep_peak_to_land_network_c_per_w"])
        self.assertEqual(thick["actual_via_centres_inside_ep"], 6)


if __name__ == "__main__":
    unittest.main()
