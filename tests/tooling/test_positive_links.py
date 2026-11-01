"""Portable busbar receiving contracts, real failure mutations and sealed evidence."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hardware.cad.a12.positive_links.analysis import area_screens
from hardware.cad.a12.positive_links.contract import problems
from hardware.cad.a12.positive_links.generate import OUT, ROOT, load, sha
from hardware.cad.a12.positive_links.verify import stale_paths


class PositiveLinks(unittest.TestCase):
    def setUp(self):
        self.d = load()

    def test_declared_candidate_contract(self):
        self.assertEqual(problems(self.d), [])

    def test_exact_selected_tdk_height_precedes_generic_0805(self):
        from hardware.cad.a12.positive_links.selected_parts import requirement

        for mpn in ("C2012X7R1H225K125AC", "C2012X7R1E475K125AB"):
            row = requirement("Capacitor_SMD:C_0805_2012Metric", "TDK " + mpn)
            self.assertAlmostEqual(row["assembled_projection_requirement_mm"], 1.55)
            self.assertEqual(row["manufacturer_body_maximum_mm"], [2.2, 1.45, 1.45])
            self.assertFalse(row["physical_verified"])
            with self.assertRaises(ValueError):
                requirement("Capacitor_SMD:C_0603_1608Metric", mpn)
            self.assertIsNone(requirement("Capacitor_SMD:C_0805_2012Metric", mpn + "BAD"))

    def test_copper_section_removes_maximum_tin_and_edge_break(self):
        a = area_screens(self.d)
        self.assertAlmostEqual(a["bulk"], 6.1444)
        self.assertAlmostEqual(a["hole_neck"], 6.3208)
        altered = copy.deepcopy(self.d)
        altered["surface"]["maximum_project_um_each_face"] = 50
        self.assertTrue(any("copper" in r for r in problems(altered)))

    def test_narrow_stock_rejected(self):
        self.d["bar"]["width_range"][0] = 5.9
        self.assertIn("insufficient copper bulk", problems(self.d))

    def test_large_hole_rejected(self):
        self.d["bar"]["hole_range"][1] = 4.0
        self.assertIn("insufficient copper hole_neck", problems(self.d))

    def test_actual_failed_transverse_riser_mutation_rejected(self):
        p = self.d["paths"]["DIG"]["points"]
        del p[3]
        p[3][0] = 114
        self.assertTrue(any("riser changes transverse axis" in e for e in problems(self.d)))

    def test_diagonal_path_rejected_without_silent_axis_choice(self):
        self.d["paths"]["ANA"]["points"][1][1] += 0.1
        self.assertTrue(any("non-orthogonal" in e for e in problems(self.d)))

    def test_actual_failed_low_crossbolt_rejected(self):
        self.d["cap"]["cross_bolt_axis_above_copper_bottom_mm"] = 6.2
        self.assertIn("insufficient nut cavity floor wall", problems(self.d))

    def test_thin_bridge_roof_rejected(self):
        self.d["cap"]["bridge_top_above_copper_bottom_mm"] = 8
        self.assertIn("insufficient nut cavity roof wall", problems(self.d))

    def test_unmatched_cavity_rejected(self):
        self.d["cap"]["landing_cavity_must_match_received_copper_thickness"] = False
        self.assertIn("cap cavity must match received copper", problems(self.d))

    def test_radial_fit_receiving_and_motion_bounds(self):
        self.d["cap"]["inner_landing_diameter"] = 10.05
        self.assertIn("cap cannot receive maximum landing", problems(self.d))
        self.d = load()
        self.d["cap"]["inner_landing_diameter"] = 10.5
        self.assertIn("cap radial motion exceeds envelope", problems(self.d))

    def test_excess_cap_motion_rejected(self):
        self.d["cap"]["landing_cavity_z_clearance_down_up_mm"] = [0.9, 0.05]
        self.assertIn("cap downward motion exceeds envelope", problems(self.d))

    def test_excess_stud_torque_and_unmeasured_release_rejected(self):
        self.d["terminal_hardware"]["trial_torque_nm"] = 0.6
        self.d["fabrication_released"] = True
        errors = problems(self.d)
        self.assertIn("stud torque exceeds manufacturer", errors)
        self.assertIn("unmeasured release flag fabrication_released", errors)

    def test_shared_packet_is_called_directly_and_selected_heights_match(self):
        from hardware.cad.a12.positive_links import collisions

        real = collisions.packet
        with mock.patch.object(collisions, "packet", wraps=real) as shared:
            native, _, _ = collisions.snapshot()
        shared.assert_called_once_with()
        selected = native["shared_selected_height_resolutions"]
        self.assertEqual(
            {r["ref"] for r in selected if r["mpn"].startswith("C2012")},
            {"C200", "C202", "C203", "C220", "C222", "C223"},
        )
        self.assertTrue(
            all(
                r["assembled_projection_requirement_mm"] == 1.55
                for r in selected
                if r["mpn"].startswith("C2012")
            )
        )

    def test_complete_nominal_step_assembly_review_is_source_bound(self):
        r = json.loads((OUT / "complete-geometry-review.json").read_text())
        self.assertEqual(stale_paths(r["source_sha256"], ROOT), [])
        self.assertEqual(r["part_count"], 29)
        self.assertEqual(r["possible_pairs"], 406)
        self.assertEqual(r["complete_assembly_solid_count"], 29)
        self.assertTrue(r["complete_assembly_matches_all_individual_parts"])
        self.assertEqual(r["unexpected_intersections"], [])
        self.assertEqual(len(r["nonzero_intersections"]), 8)
        self.assertTrue(all(x["permitted_nominal_thread_overlap"] for x in r["nonzero_intersections"]))
        self.assertAlmostEqual(r["independent_interference_control_mm3"], 0.008)
        self.assertFalse(r["physical_fit_verified"])

    def test_validation_only_refresh_cannot_hide_native_driver_changes(self):
        from hardware.cad.a12.positive_links.refresh_validation import gate_only_change

        old = (OUT / "history/validation-only-before-collision-artifact-gate/verify.py").read_text()
        current = (ROOT / "verify.py").read_text()
        self.assertTrue(gate_only_change(old, current))
        self.assertFalse(gate_only_change(old, current.replace("timeout=180", "timeout=181")))

    def test_gate_rejects_absent_copper_collision_and_control_mutations(self):
        from hardware.cad.a12.positive_links.verify import gate_errors

        original = json.loads((OUT / "verification.json").read_text())
        geometry = json.loads((OUT / "geometry.json").read_text())
        baseline = copy.deepcopy(original)
        for key in (
            "stale_sources",
            "native_inputs_changed_during_run",
            "native_failures",
            "collision_failures",
        ):
            baseline[key] = []
        self.assertEqual(gate_errors(baseline, geometry), [])
        for mutation in (
            "empty_copper",
            "missing_copper",
            "wrong_volume",
            "collision",
            "empty_control",
            "wrong_control",
            "stale",
        ):
            r = copy.deepcopy(baseline)
            if mutation == "empty_copper":
                r["native_checks"]["copper"] = {"result": "empty", "volume_mm3": 0}
            if mutation == "missing_copper":
                del r["native_checks"]["copper"]
            if mutation == "wrong_volume":
                r["native_checks"]["copper"]["volume_mm3"] *= 0.5
            if mutation == "collision":
                r["native_checks"]["case_collision"] = {"result": "valid native manifold", "volume_mm3": 1}
            if mutation == "empty_control":
                r["native_checks"]["positive_control"] = {"result": "empty", "volume_mm3": 0}
            if mutation == "wrong_control":
                r["native_checks"]["support_positive_control"]["volume_mm3"] = 1
            if mutation == "stale":
                r["stale_sources"] = ["changed-source"]
            with self.subTest(mutation=mutation):
                self.assertTrue(gate_errors(r, geometry))

    def test_saved_report_cli_exit_and_seal_gate_require_actual_copper(self):
        from hardware.cad.a12.positive_links.verify import saved_report_errors

        original = json.loads((OUT / "verification.json").read_text())
        geometry = json.loads((OUT / "geometry.json").read_text())
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name in ("copper", "positive_control", "support_positive_control"):
                shutil.copy2(OUT / ("native-" + name + ".stl"), base / ("native-" + name + ".stl"))
            hashes = {str(p): sha(p) for p in base.glob("*.stl")}
            r = copy.deepcopy(original)
            for key in ("source_sha256", "geometry_sha256", "native_input_sha256", "native_evidence_sha256"):
                r[key] = hashes
            for key in (
                "stale_sources",
                "native_inputs_changed_during_run",
                "native_failures",
                "collision_failures",
            ):
                r[key] = []
            gp = base / "geometry.json"
            gp.write_text(json.dumps(geometry))
            rp = base / "verification.json"
            rp.write_text(json.dumps(r))
            cmd = [
                sys.executable,
                "-m",
                "hardware.cad.a12.positive_links.verify",
                "--check-report",
                str(rp),
                "--geometry",
                str(gp),
            ]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            bad = copy.deepcopy(r)
            bad["native_checks"]["case_collision"] = {"result": "valid native manifold", "volume_mm3": 1}
            rp.write_text(json.dumps(bad))
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            self.assertTrue(saved_report_errors(bad, geometry, base))
            collision = base / "native-case_collision.stl"
            shutil.copy2(base / "native-copper.stl", collision)
            forged = copy.deepcopy(r)
            all_actual = {str(p): sha(p) for p in base.glob("*.stl")}
            for key in ("source_sha256", "geometry_sha256", "native_input_sha256", "native_evidence_sha256"):
                forged[key] = all_actual
            self.assertEqual(forged["native_checks"]["case_collision"], {"result": "empty", "volume_mm3": 0})
            self.assertIn(
                "declared empty collision has artifact: case_collision",
                saved_report_errors(forged, geometry, base),
            )
            rp.write_text(json.dumps(forged))
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            collision.unlink()
            rp.write_text(json.dumps(r))
            (base / "native-copper.stl").unlink()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            self.assertTrue(saved_report_errors(r, geometry, base))

    def test_missing_and_changed_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            p = base / "native-input"
            p.write_text("original")
            hashes = {"native-input": sha(p)}
            self.assertEqual(stale_paths(hashes, base), [])
            p.write_text("changed")
            self.assertEqual(stale_paths(hashes, base), ["native-input"])
            p.unlink()
            self.assertEqual(stale_paths(hashes, base), ["native-input"])

    def test_sealed_sections_fit_sources_and_no_physical_claims(self):
        for file in ["analysis.json", "geometry.json", "self-fit.json"]:
            report = json.loads((OUT / file).read_text())
            for name, expected in report["source_sha256"].items():
                self.assertEqual(sha(ROOT / name), expected, (file, name))
        report = json.loads((OUT / "analysis.json").read_text())
        for link in report["links"].values():
            self.assertTrue(link["all_witnesses_meet_project_minimum"])
            self.assertGreater(len(link["witnesses"]), 20)
            self.assertGreaterEqual(link["minimum_witness_area_mm2"], 6)
            self.assertFalse(link["joint_resistance_included"])
        fit = json.loads((OUT / "self-fit.json").read_text())
        self.assertTrue(fit["all_declared_nominal_fits_clear"])
        self.assertEqual(len(fit["checks"]), 48)
        self.assertFalse(fit["physical_fit_verified"])

    def test_native_full_coverage_and_sealed_positive_controls(self):
        r = json.loads((OUT / "verification.json").read_text())
        self.assertEqual(r["stale_sources"], [])
        self.assertEqual(r["native_inputs_changed_during_run"], [])
        self.assertEqual(r["collision_failures"], [])
        self.assertEqual(r["native_failures"], [])
        self.assertTrue(r["positive_control_detected"])
        self.assertGreater(r["native_checks"]["positive_control"]["volume_mm3"], 0.007)
        self.assertGreater(r["native_checks"]["support_positive_control"]["volume_mm3"], 0.007)
        self.assertEqual(r["native_checks"]["copper"]["result"], "valid native manifold")
        self.assertEqual(len(r["native_checks"]), 10)
        geo = json.loads((OUT / "geometry.json").read_text())
        nominal_volume = sum(geo[n + "-CU"]["volume_mm3"] for n in ("ANA", "DIG"))
        self.assertLess(
            abs(r["native_checks"]["copper"]["volume_mm3"] - nominal_volume) / nominal_volume, 0.0005
        )
        for group in ["source_sha256", "geometry_sha256", "native_input_sha256", "native_evidence_sha256"]:
            self.assertGreater(len(r[group]), 3)
            from hardware.cad.a12.historical import inspect_hashes

            audit = inspect_hashes(r[group])
            self.assertTrue(audit["historical_capture_complete"], group)
            self.assertFalse(audit["fabrication_released"])
            if group == "source_sha256":
                self.assertFalse(audit["applies_to_current_inputs"])
        packet = json.loads((OUT / "obstacles.json").read_text())
        self.assertEqual(
            packet["intentional_connected_studs_excluded"], ["E28_J10", "E28_J11", "P03_J23", "P03_J24"]
        )
        self.assertGreaterEqual(len(packet["native_component_records"]), 500)
        self.assertEqual(len([c for c in packet["cylinders"] if c[0].endswith("_mount_head")]), 14)
        self.assertIn("actual rotated", packet["switch_native_geometry"])
        for flag in [
            "physical_fit_verified",
            "cover_and_restraint_qualified",
            "electrical_joint_qualified",
            "fabrication_released",
            "selected_for_production",
        ]:
            self.assertFalse(r[flag])

    def test_sealed_review_packet_and_no_release_inference(self):
        p = json.loads((OUT / "review-packet.json").read_text())
        for group in ("source_sha256", "evidence_sha256", "native_geometry_sources"):
            from hardware.cad.a12.historical import inspect_hashes

            audit = inspect_hashes(p[group])
            self.assertTrue(audit["historical_capture_complete"], group)
            self.assertFalse(audit["fabrication_released"])
            if group in ("source_sha256", "native_geometry_sources"):
                self.assertFalse(audit["applies_to_current_inputs"])
        for flag in (
            "all_continuous_receiving_support_tolerances_proved",
            "physical_fit_verified",
            "dielectric_qualified",
            "complete_link_resistance_verified",
            "mechanical_lifetime_qualified",
            "fabrication_released",
            "selected_for_production",
        ):
            self.assertFalse(p[flag])

    def test_conservative_support_bounds_contain_actual_step(self):
        r = json.loads((OUT / "support-bounds.json").read_text())
        self.assertEqual(stale_paths(r["source_sha256"], ROOT), [])
        self.assertEqual(r["contained_actual_step_sha256"], sha(OUT / "SUPPORT-ENVELOPE.step"))
        self.assertLess(r["actual_sampled_support_outside_convex_union_mm3"], 1e-7)
        self.assertTrue(r["nominal_and_generated_extrema_contained"])
        self.assertGreater(len(r["boxes"]), 5)
        self.assertGreater(len(r["cylinders"]), 10)
        self.assertFalse(r["physical_qualified"])

    @unittest.skipUnless(
        os.environ.get("AFX_POSITIVE_CAD") == "1", "Optional CadQuery cap/copper regeneration"
    )
    def test_optional_real_cap_brep_self_fit(self):
        from hardware.cad.a12.positive_links.caps import pieces
        from hardware.cad.a12.positive_links.generate import shape

        for name in self.d["paths"]:
            cu = shape(self.d, name)
            for end in (0, 1):
                for half in ["HALF-A", "HALF-B"]:
                    self.assertLess(cu.intersect(pieces(self.d, name, end)[half]).Volume(), 1e-7)


if __name__ == "__main__":
    unittest.main()
