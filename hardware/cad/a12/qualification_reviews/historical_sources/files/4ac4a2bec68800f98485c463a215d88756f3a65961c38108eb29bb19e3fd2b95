"""Portable real design contracts; no CAD, SciPy, network or physical-pass fiction."""

import copy
import gzip
import hashlib
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a12.historical import inspect_hashes, resolve
from hardware.cad.a12.thermal.analyze import (
    analytical,
    compression,
    in_polygon,
    overlaps,
    point_segment_distance,
    via_resistance,
)
from hardware.cad.a12.thermal.generate import (
    OUT,
    REPO,
    carrier_windows,
    circle_rect_area,
    contact_contains,
    lands,
    load,
    mounts,
    sha,
)
from hardware.cad.a12.thermal.verify import binary_stl


class PowerThermal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load()
        cls.analysis = json.loads((OUT / "analysis.json").read_text())
        cls.receipt = json.loads((OUT / "verification.json").read_text())

    def test_historical_capture_reports_stale_inputs_without_current_approval(self):
        missing = []
        for group in ("source_sha256", "evidence_sha256"):
            self.assertGreater(len(self.receipt[group]), 8)
            audit = inspect_hashes(self.receipt[group])
            self.assertFalse(audit["fabrication_released"])
            missing.extend(e["original_path"] for e in audit["sources"] if e["resolved_path"] is None)
            if group == "source_sha256":
                self.assertFalse(audit["applies_to_current_inputs"])
                self.assertFalse(audit["historical_capture_complete"])
        self.assertEqual(set(missing), {
            "hardware/cad/a12/thermal/README.md",
            "hardware/electronics/power_distribution/p03/generated/placement.json",
        })
        required = {
            str((REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb").relative_to(REPO)),
            str((REPO / "tests/tooling/test_power_thermal.py").relative_to(REPO)),
        }
        self.assertTrue(required.issubset(self.receipt["source_sha256"]))

    def test_matched_pad_and_shim_stack_sweeps_real_tolerance(self):
        actual = analytical(self.d)
        self.assertGreater(actual["compression_sweep_count"], 4000)
        self.assertTrue(actual["matched_compression_screen_all_pass"])
        self.assertGreaterEqual(actual["matched_compression_min"], 0.10)
        self.assertLessEqual(actual["matched_compression_max"], 0.30)
        for key, value in actual.items():
            self.assertEqual(self.analysis[key], value, key)
        d = copy.deepcopy(self.d)
        d["base"]["board_height_shim_range"] = [0, 0]
        self.assertFalse(compression(d, [1.6764] * 4)["compression_allocation_satisfied"])
        d = copy.deepcopy(self.d)
        d["tim"]["contact_bondline_allocation_uncertainty"] = 0.30
        self.assertFalse(compression(d, [1.3716] * 4)["compression_allocation_satisfied"])

    def test_unmatched_tolerance_extremes_and_thinner_pad_rejected(self):
        self.assertFalse(compression(self.d, [1.3716, 1.6764] * 2)["compression_allocation_satisfied"])
        self.assertFalse(compression(self.d, [2.0] * 4)["compression_allocation_satisfied"])
        self.assertTrue(self.analysis["naive_4mm_pad_over_3p7mm_gap_has_no_guaranteed_contact"])
        with self.assertRaises(ValueError):
            compression(self.d, [2.54])

    def test_via_barrels_are_not_misrepresented_as_solid_copper(self):
        self.assertAlmostEqual(via_resistance(count=6) * 6, via_resistance())
        self.assertGreater(via_resistance(count=6), 25)
        self.assertGreater(via_resistance(plating_um=20), via_resistance(plating_um=25))
        self.assertGreater(
            via_resistance(plating_um=10, count=36), via_resistance(plating_um=25, count=36) * 2
        )
        with self.assertRaises(ValueError):
            via_resistance(plating_um=0)
        self.assertEqual(self.analysis["via_resin_fill_thermal_credit"], 0)

    def test_u13_requires_actual_sheet_spreading_and_guardbanded_whole_path(self):
        report = json.loads((OUT / "u13-path.json").read_text())
        for path, expected in report["source_sha256"].items():
            self.assertEqual(sha(resolve(path, expected)), expected)
        for row in report["scenarios"] + [report["finer_grid"]]:
            self.assertTrue(row["solver_converged"])
            self.assertLess(row["kcl_residual_w"], 1e-8)
            self.assertEqual(row["included_layers"], ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"])
            self.assertGreater(row["actual_via_centres_inside_ep"], 0)
            self.assertGreater(row["actual_matching_through_vias"], row["actual_via_centres_inside_ep"])
            required = (85 - 60) / row["power_allocation_w"]
            self.assertAlmostEqual(row["required_total_junction_to_base_at_60c_c_per_w"], required)
            self.assertAlmostEqual(
                row["conditional_junction_at_60c_base_c"],
                60 + row["power_allocation_w"] * row["conditional_total_junction_to_base_c_per_w"],
            )
            self.assertFalse(row["physical_junction_verified"])
            self.assertFalse(row["thermal_path_qualified"])
            self.assertAlmostEqual(
                row["remaining_after_declared_contact_for_parameter_uncertainty_c_per_w"],
                required - row["conditional_total_junction_to_base_c_per_w"],
            )
        self.assertEqual(
            hashlib.sha256(
                gzip.decompress((REPO / report["compressed_native_input_evidence"]).read_bytes())
            ).hexdigest(),
            report["native_copper_origin_sha256"],
        )
        self.assertFalse(report["contact_spreading_and_parameter_uncertainty_guaranteed"])
        self.assertFalse(report["whole_path_acceptance"]["guardbanded_85c_project_acceptance"])
        self.assertIsNone(report["whole_path_acceptance"]["bounded_total_path_upper_c_per_w"])
        self.assertTrue(report["whole_path_acceptance"]["missing_bound_inputs_are_not_zero"])
        self.assertFalse(report["illustrative_sensitivity_is_a_manufacturer_bound"])
        self.assertEqual(report["physical_tests_performed"], 0)

    def test_corrected_loss_ledger_is_source_bound_and_prior_total_is_superseded(self):
        from hardware.cad.a12.thermal.analyze import HEAT, native_heat_and_vias

        ledger = resolve(self.analysis["loss_ledger_path"], self.analysis["loss_ledger_sha256"])
        self.assertEqual(sha(ledger), self.analysis["loss_ledger_sha256"])
        source = json.loads(ledger.read_text())
        for path, expected in source["source_sha256"].items():
            dependency = Path(path)
            if not dependency.is_absolute():
                dependency = REPO / dependency
            self.assertEqual(self.receipt["source_sha256"][str(dependency.relative_to(REPO))], expected)
        self.assertAlmostEqual(
            sum(row[2] for row in HEAT.values()), source["total_conservative_loss_allocation_w"]
        )
        self.assertAlmostEqual(self.analysis["total_provision_w"], 10.557756677906315)
        self.assertGreater(HEAT["U102"][2], 0.96)
        self.assertGreater(HEAT["U10"][2], 0.62)
        with tempfile.TemporaryDirectory() as folder:
            pcb = Path(folder) / "power_p03.kicad_pcb"
            pcb.write_text("(kicad_pcb)")
            (pcb.parent / "heatmap.json").write_text(
                json.dumps({"source_sha256": {"/earlier/power_p03.kicad_pcb": "0" * 64}})
            )
            with self.assertRaisesRegex(AssertionError, "Stale heat ledger"):
                native_heat_and_vias(self.d, pcb)

    def test_hot_rails_have_selected_tim_and_no_accidental_chassis_bond(self):
        self.assertIn("floating CHASSIS", self.d["quiet_ground_policy"])
        self.assertIn("P12_SRC", {x["electrical_node"] for x in lands(self.d)})
        self.assertIn("RAW_N17", {x["electrical_node"] for x in lands(self.d)})
        self.assertIsNone(self.d["tim"]["minimum_guaranteed_thermal_conductivity"])
        self.assertFalse(self.d["tim"]["dielectric_test_is_assembly_approval"])
        for row in lands(self.d):
            self.assertAlmostEqual(row["cut_global"][2] - row["metal_global"][2], 2)
            self.assertAlmostEqual(row["cut_global"][3] - row["metal_global"][3], 2)

    def test_larger_u13_contact_preserves_real_mount_relief_and_excludes_ideal_area_credit(self):
        site = next(s for s in lands(self.d) if s["refs"] == ["U13"])
        self.assertAlmostEqual(circle_rect_area([-2, -2, 4, 4], [0, 0], 1), math.pi)
        self.assertAlmostEqual(circle_rect_area([0, 0, 2, 2], [0, 0], 1), math.pi / 4)
        self.assertEqual(circle_rect_area([3, 3, 2, 2], [0, 0], 1), 0)
        self.assertAlmostEqual(site["metal_contact_area_mm2"], 165.4714282901014)
        self.assertLess(site["metal_contact_area_mm2"], 192)
        self.assertFalse(contact_contains(site, 285, 112))
        self.assertFalse(contact_contains(site, 281, 112))
        self.assertTrue(contact_contains(site, 280, 112))
        window = next(s for s in carrier_windows(self.d) if s["id"] == site["id"])
        self.assertAlmostEqual(window["subtract_circle"]["radius_mm"] - 3.4, 1.0)
        # A removed relief would put live-contact geometry over the bare mount.
        bad = copy.deepcopy(site)
        del bad["corner_relief"]
        self.assertTrue(contact_contains(bad, 285, 112))

    def test_immutable_process_trial_energy_balance_and_construction_holds(self):
        report = json.loads((OUT / "u13-process-trials.json").read_text())
        original = REPO / report["historical_report_path"]
        self.assertEqual(sha(original), report["historical_report_sha256"])
        historical = json.loads(original.read_text())
        self.assertEqual(report["scenarios"], historical["scenarios"])
        self.assertEqual(report["historical_original_source_sha256"], historical["source_sha256"])
        for path, expected in report["source_sha256"].items():
            self.assertEqual(sha(REPO / path), expected)
        self.assertEqual(
            hashlib.sha256(
                gzip.decompress((REPO / report["compressed_native_input"]).read_bytes())
            ).hexdigest(),
            report["native_origin_sha256"],
        )
        for row in report["scenarios"].values():
            parts = row["unit_heat_energy_decomposition_c_per_w"]
            self.assertAlmostEqual(
                parts["direct_ep_via_barrels"] + parts["remote_field_via_barrels"],
                parts["via_barrels_all_segments"],
                places=9,
            )
            self.assertAlmostEqual(
                sum(parts["sheet_spreading_by_layer"].values())
                + parts["via_barrels_all_segments"]
                + parts["tim_bulk_under_actual_bottom_copper"],
                row["ep_mean_to_land_network_c_per_w"],
                places=7,
            )
            self.assertLess(row["kcl_residual_w"], 1e-8)
            self.assertFalse(row["thermal_path_qualified"])
        rows = report["scenarios"]
        self.assertGreater(rows["native_1p6_wall25"]["conditional_junction_at_60c_base_c"], 85)
        self.assertGreater(
            rows["wall35_current_stack"]["conditional_total_junction_to_base_c_per_w"],
            rows["wall50_outer85"]["conditional_total_junction_to_base_c_per_w"],
        )
        self.assertGreater(
            rows["wall50_illustrative_lower_k"]["conditional_total_junction_to_base_c_per_w"],
            rows["wall50_outer85"]["conditional_total_junction_to_base_c_per_w"],
        )
        process = json.loads((OUT.parent / "process-candidates.json").read_text())
        self.assertEqual(process["actual_direct_ep_array"]["pitch_mm"], 0.5)
        self.assertFalse(process["fabricator_dfm_approved"])
        self.assertFalse(report["guardbanded_85c_acceptance"])
        self.assertEqual(report["physical_tests_performed"], 0)

    def test_construction_requirement_cannot_reuse_wrong_board_or_invalid_wall(self):
        from hardware.cad.a12.thermal.u13_path import read_construction

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "construction.json"
            contract = dict(
                pcb_sha256="a" * 64, via_wall_minimum_required_um=50, board_nominal_thickness_mm=1.6
            )
            path.write_text(json.dumps(contract))
            self.assertEqual(read_construction(path, "a" * 64), contract)
            with self.assertRaises(ValueError):
                read_construction(path, "b" * 64)
            for bad in [None, True, 0, -50, "50", float("nan"), float("inf")]:
                contract["via_wall_minimum_required_um"] = bad
                path.write_text(json.dumps(contract))
                with self.assertRaises(ValueError):
                    read_construction(path, "a" * 64)

    def test_independent_native_solids_agree_and_positive_control_detects_collision(self):
        actual = binary_stl(OUT / "native-base.stl")
        self.assertEqual(actual, {k: self.receipt["native_checks"]["base"][k] for k in actual})
        self.assertAlmostEqual(actual["max_mm"][2], 6.3, places=4)
        self.assertAlmostEqual(actual["max_mm"][0], 334, places=3)
        self.assertAlmostEqual(
            actual["min_mm"][2],
            self.d["base"]["plate_top_z"] - self.d["base"]["plate_thickness"] - self.d["base"]["fin_height"],
            places=4,
        )
        self.assertLess(self.receipt["independent_scad_step_relative_volume_difference"], 0.0005)
        self.assertGreater(self.receipt["native_checks"]["positive_control"]["volume_mm3"], 0.9)
        self.assertIn("empty", self.receipt["native_checks"]["collision"]["result"])
        self.assertTrue(overlaps([1, 1, 3, 3], [2, 2, 4, 4]))
        self.assertFalse(overlaps([1, 1, 3, 3], [3, 1, 4, 3]))
        self.assertGreaterEqual(len(mounts(self.d)), 10)

    def test_sensitivity_failures_and_no_physical_release_are_preserved(self):
        cases = self.analysis["conditional_plate_scenarios"]
        self.assertTrue(all(c["converged"] for c in cases))
        self.assertTrue(any(c["conditional_60c_coldplate_allocation_satisfied"] for c in cases))
        self.assertTrue(any(not c["conditional_60c_coldplate_allocation_satisfied"] for c in cases))
        for document in (self.receipt, self.d):
            for flag in ("physical_fit_verified", "thermal_qualified", "fabrication_released", "build_ready"):
                self.assertFalse(document[flag])
        self.assertEqual(self.receipt["physical_tests_performed"], 0)
        self.assertFalse(self.receipt["convection_coefficient_measured"])
        self.assertFalse(self.receipt["all_package_junction_paths_verified"])
        self.assertLess(self.analysis["numerical_grid_peak_span_c"], 0.1)
        self.assertFalse(
            self.analysis["rejected_smaller_base_counterfactual"]["scenario"][
                "conditional_60c_coldplate_allocation_satisfied"
            ]
        )

    def test_retained_carrier_windows_and_actual_support_copper_clearance(self):
        interface = json.loads((OUT / "interface.json").read_text())
        self.assertEqual(interface["base_top_z"], 0)
        self.assertEqual(interface["retained_structural_carrier_z_mm"], [0, 2.8])
        self.assertEqual(len(interface["local_rectangular_carrier_windows"]), 4)
        self.assertAlmostEqual(interface["assembled_housing_height_nominal_mm"], 66.8)
        screen = self.analysis["actual_support_copper_screen"]
        self.assertGreater(screen["checked_filled_polygons"], 0)
        self.assertTrue(screen["all_ten_nominal_metal_faces_free_of_actual_native_copper"])
        self.assertEqual(len(screen["supports"]), 10)
        self.assertGreater(min(r["nearest_conservative_copper_gap_mm"] for r in screen["supports"]), 0)
        self.assertFalse(screen["manufacturer_and_registration_tolerance_approved"])
        # Filled-copper contact calculation must detect a polygon enclosing the post;
        # moving the same source boundary beyond the nominal0.7 gap must clear.
        square = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        self.assertTrue(in_polygon((0, 0), square))
        self.assertFalse(in_polygon((4, 0), square))
        self.assertAlmostEqual(point_segment_distance((0, 0), (3.7, -2), (3.7, 2)) - 3, 0.7)
        self.assertLess(point_segment_distance((0, 0), (2.9, -2), (2.9, 2)) - 3, 0)

    @unittest.skipUnless(
        os.environ.get("AFX_THERMAL_SOLVERS") == "1", "Optional NumPy/SciPy numerical regeneration"
    )
    def test_optional_actual_solver_reproduces_nominal_transfer_and_heat_balance(self):
        from hardware.cad.a12.thermal.analyze import plate_scenario

        actual = plate_scenario(self.d, 3, 0.8)
        saved = self.analysis["conditional_plate_scenarios"][2]
        self.assertAlmostEqual(actual["plate_max_c"], saved["plate_max_c"], places=7)
        self.assertAlmostEqual(actual["total_w"], self.d["design_allocations"]["total_heat_w"], places=6)
        cooler = plate_scenario(self.d, 5, 0.8)
        self.assertLess(cooler["plate_max_c"], actual["plate_max_c"])


if __name__ == "__main__":
    unittest.main()
