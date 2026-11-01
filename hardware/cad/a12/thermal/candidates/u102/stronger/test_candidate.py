"""Portable actual-source/geometry/path checks; optional solver mutations."""

import json
import math
import os
import unittest

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .analyze import required_path
from .generate import METAL, OUT, ROOT, TIM


class StrongerU102(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = json.loads((OUT / "analysis.json").read_text())
        cls.native = json.loads((OUT / "verification.json").read_text())
        cls.geometry = json.loads((OUT / "geometry.json").read_text())
        cls.obstacles = json.loads((OUT / "obstacles.json").read_text())

    def test_immutable_candidate_and_post_refill_receipt_are_identical(self):
        p = ROOT / "sources/power_p03.kicad_pcb"
        expected = sha(p)
        self.assertEqual(expected, "bd4765eb8184a2c5fe336d68e0951ab383e2d959fa05a099e4dcaa14e82de119")
        for f, key in [("construction.json", "pcb_sha256"), ("u102-candidate.json", "candidate_pcb_sha256")]:
            self.assertEqual(json.loads((ROOT / "sources" / f).read_text())[key], expected)
        for path, h in self.analysis["source_sha256"].items():
            self.assertEqual(sha(REPO / path), h, path)
        self.assertEqual(sha(OUT / "verification.json"), self.analysis["native_verification_sha256"])
        packet = json.loads((ROOT / "handoff.json").read_text())
        for group in ["source_sha256", "evidence_sha256"]:
            for path, h in packet[group].items():
                self.assertEqual(sha(REPO / path), h, path)
        self.assertFalse(packet["guardbanded110c_accepted"])

    def test_real_nine_ep_vias_and_native_six_layer_copper_are_present(self):
        tree = read_sexpr((ROOT / "sources/power_p03.kicad_pcb").read_text())
        wanted = {(x, y) for x in [125.75, 126.25, 126.75] for y in [119.5, 120, 120.5]}
        actual = set()
        for v in children(tree, "via"):
            xy = tuple(map(float, first(v, "at")[1:3]))
            if xy not in wanted:
                continue
            self.assertEqual(str(first(v, "net")[1]).lstrip("/"), "AGND")
            self.assertEqual(float(first(v, "size")[1]), 0.7)
            self.assertEqual(float(first(v, "drill")[1]), 0.25)
            actual.add(xy)
        self.assertEqual(actual, wanted)
        r = self.analysis["nominal_scenario"]["results"][-1]
        self.assertEqual(r["actual_via_centres_inside_ep"], 9)
        self.assertEqual(len(r["included_layers"]), 6)
        self.assertGreater(r["sink_area_under_matching_bottom_copper_mm2"], 22)
        self.assertLess(r["sink_area_under_matching_bottom_copper_mm2"], r["metal_contact_area_mm2"])

    def test_actual_moved_bottom_parts_are_rebuilt_and_tail_reserves_remain(self):
        tree = read_sexpr((ROOT / "sources/power_p03.kicad_pcb").read_text())
        boxes = self.obstacles["native"]["boxes"]
        for ref in ["R110", "R130", "C109"]:
            fp = next(
                f
                for f in children(tree, "footprint")
                if next(p[2] for p in children(f, "property") if p[1] == "Reference") == ref
            )
            self.assertEqual(first(fp, "layer")[1], "B.Cu")
            b = courtyard(fp, "B.CrtYd")
            row = next(r for r in boxes if r[0] == "P03_" + ref)
            self.assertEqual(row[1:3], [b[0] + 68, b[1] + 8])
            self.assertEqual(row[4:6], [b[2] - b[0], b[3] - b[1]])
        tails = [r for r in boxes if r[0].startswith("P03_J106_tail")]
        self.assertGreater(len(tails), 1)
        tail_max = max(r[1] + r[4] for r in tails)
        self.assertAlmostEqual(TIM[0] + 68 - tail_max, 0.35, places=10)
        self.assertEqual(len(self.obstacles["native"]["component_records"]), 506)

    def test_actual_required_geometry_and_all_native_empty_cases(self):
        r = self.native
        self.assertTrue(r["accepted_native_evidence"])
        self.assertEqual(r["failed_cases"], [])
        self.assertEqual(r["changed_inputs"], [])
        self.assertEqual(r["stale_inputs"], [])
        actual = binary_stl(OUT / "geometry.stl")
        expected = (METAL[2] - METAL[0]) * (METAL[3] - METAL[1]) * 5.28 + (TIM[2] - TIM[0]) * (
            TIM[3] - TIM[1]
        ) * 1.02
        self.assertAlmostEqual(actual["volume_mm3"], expected, places=3)
        for k in ["component_collision", "link_collision", "case_collision"]:
            self.assertEqual(r["native_checks"][k]["result"], "empty")
            self.assertFalse((OUT / (k + ".stl")).exists())
        self.assertAlmostEqual(binary_stl(OUT / "positive_control.stl")["volume_mm3"], 0.008, places=5)
        for group in ["source_sha256", "evidence_sha256"]:
            for path, h in r[group].items():
                self.assertEqual(sha(REPO / path), h, path)

    def test_energy_conservation_and_whole_path_are_independently_recombined(self):
        for group in ["nominal_scenario", "illustrative_lower_conductivity_sensitivity"]:
            for r in self.analysis[group]["results"]:
                e = r["unit_heat_energy_decomposition_c_per_w"]
                energy = math.fsum(
                    [
                        e["sheet_spreading_total"],
                        e["via_barrels_all_segments"],
                        e["tim_bulk_under_actual_bottom_copper"],
                    ]
                )
                self.assertAlmostEqual(energy, r["ep_mean_to_land_network_c_per_w"], places=7)
                whole = (
                    14.9
                    + r["ep_peak_to_land_network_c_per_w"]
                    + r["aluminum_land_axial_c_per_w"]
                    + r["extra_contact_assumed_c_per_w"]
                )
                self.assertAlmostEqual(whole, r["conditional_total_junction_to_base_c_per_w"])
                self.assertAlmostEqual(
                    60 + self.analysis["source_power_allocation_w"] * whole,
                    r["conditional_junction_at_60c_base_c"],
                )
                self.assertLess(r["kcl_residual_w"], 1e-8)

    def test_sixty_and_sixtyfive_base_scenarios_are_not_a_guardbanded_pass(self):
        n = self.analysis["nominal_scenario"]["results"][-1]
        s = self.analysis["illustrative_lower_conductivity_sensitivity"]["results"][-1]
        self.assertLess(
            n["conditional_total_junction_to_base_c_per_w"], s["conditional_total_junction_to_base_c_per_w"]
        )
        self.assertLess(s["conditional_junction_at_60c_base_c"], 110)
        self.assertGreater(s["conditional_junction_at_60c_base_c"] + 5, 110)
        self.assertLess(required_path(65, 2), required_path(60, 2))
        with self.assertRaises(ValueError):
            required_path(60, -1)
        a = self.analysis["whole_path_acceptance"]
        self.assertIsNone(a["path_upper_bound_k_per_w"])
        self.assertFalse(a["guardbanded110c_accepted"])
        self.assertFalse(self.analysis["frozen_heat_kit_modified"])
        self.assertFalse(self.analysis["fabrication_released"])
        self.assertEqual(self.analysis["physical_tests_performed"], 0)

    @unittest.skipUnless(os.environ.get("AFX_THERMAL_SOLVERS") == "1", "optionalSciPy solver")
    def test_real_network_wall_and_tim_mutations_increase_path(self):
        from ..network import solve

        args = dict(contact_native=METAL, grid=80, pcb_path=ROOT / "sources/power_p03.kicad_pcb")
        baseline = solve(**args, via_wall_um=50, tim_k=6)
        thin = solve(**args, via_wall_um=25, tim_k=6)
        poor = solve(**args, via_wall_um=50, tim_k=4)
        self.assertEqual(baseline["actual_via_centres_inside_ep"], 9)
        self.assertLess(baseline["ep_peak_to_land_network_c_per_w"], thin["ep_peak_to_land_network_c_per_w"])
        self.assertLess(baseline["ep_peak_to_land_network_c_per_w"], poor["ep_peak_to_land_network_c_per_w"])


if __name__ == "__main__":
    unittest.main()
