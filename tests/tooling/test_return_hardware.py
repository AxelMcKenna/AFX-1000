"""Portable section/stack/source contracts; no borrowed physical approval."""

import copy
import json
import unittest

from hardware.cad.a12.historical import inspect_hashes
from hardware.cad.a12.returns.generate import (
    OUT,
    assembly_stack,
    corner_disks,
    geometry,
    load,
    points,
    seat,
)


class ReturnHardware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load()
        cls.saved = json.loads((OUT / "geometry.json").read_text())
        cls.d["assembled_board_bottom_z_mm"] = cls.saved["effective_measured_plane_inputs"]
        cls.d["assembled_terminal_top_override_z_mm"] = cls.saved.get(
            "effective_terminal_top_override_z_mm", {}
        )
        cls.receipt = json.loads((OUT / "verification.json").read_text())

    def test_historical_inputs_are_captured_without_current_approval(self):
        for group in ("source_sha256", "evidence_sha256"):
            self.assertGreater(len(self.receipt[group]), 8)
            audit = inspect_hashes(self.receipt[group])
            self.assertTrue(audit["historical_capture_complete"], group)
            self.assertFalse(audit["fabrication_released"])
            if group == "source_sha256":
                self.assertFalse(audit["applies_to_current_inputs"])
        self.assertEqual(self.saved["bars"], geometry(self.d))
        self.assertEqual(self.saved["assembly_stack"], assembly_stack(self.d))

    def test_selected_tdk_0805_uses_actual_height_requirement(self):
        from hardware.cad.a12.returns.collisions import height

        for mpn in ("C2012X7R1H225K125AC", "C2012X7R1E475K125AB"):
            projection, basis, approved = height("C202", "Capacitor_SMD:C_0805_2012Metric", "TDK " + mpn)
            self.assertAlmostEqual(projection, 1.55)
            self.assertIn(mpn, basis)
            self.assertFalse(approved)

    def test_real_neck_and_ramp_normal_area_corners_exceed_allocation(self):
        for row in geometry(self.d).values():
            self.assertGreaterEqual(row["minimum_normal_section_mm2"], 20)
            self.assertAlmostEqual(row["minimum_hole_neck_section_mm2"], 20.1825)
            self.assertTrue(row["length_allocation_satisfied"])
        for key, value in [
            ("width", 5.8),
            ("hole_diameter", 4.2),
            ("thickness", 3.4),
            ("maximum_edge_break_mm", 0.4),
        ]:
            d = copy.deepcopy(self.d)
            d["assembled_terminal_top_override_z_mm"] = {}
            d["bar"][key] = value
            self.assertFalse(all(r["normal_section_allocation_satisfied"] for r in geometry(d).values()))

    def test_actual_p03_plane_changes_matched_copper_and_retainer_geometry(self):
        heights = []
        for z in (6.3, 6.5, 6.7):
            d = copy.deepcopy(self.d)
            d["assembled_terminal_top_override_z_mm"] = {}
            d["assembled_board_bottom_z_mm"]["P03"] = z
            self.assertAlmostEqual(points(d, "ANA")[-1][2], z + 6.6)
            self.assertEqual(points(d, "ANA")[0], [139, 148, 11.6])
            heights.append(seat(d, "ANA", 166))
            self.assertTrue(all(r["normal_section_allocation_satisfied"] for r in geometry(d).values()))
        self.assertLess(heights[0], heights[1])
        self.assertLess(heights[1], heights[2])

    def test_cap_clearance_and_electrical_budget_mutations_are_rejected(self):
        self.assertTrue(assembly_stack(self.d)["cap_gap_allocation_satisfied"])
        self.assertTrue(assembly_stack(self.d)["electrical_allocation_fits_target"])
        d = copy.deepcopy(self.d)
        d["retainers"]["cap_nominal_above_bar_gap"] = 0.1
        self.assertFalse(assembly_stack(d)["cap_gap_allocation_satisfied"])
        d = copy.deepcopy(self.d)
        d["terminal_hardware"]["terminal_assembly_resistance_allocation_mohm"] = 0.5
        self.assertFalse(assembly_stack(d)["electrical_allocation_fits_target"])
        self.assertAlmostEqual(assembly_stack(self.d)["complete_return_allocated_mohm"], 1.8)

    def test_torque_fixture_is_required_by_actual_thin_stem_screen(self):
        s = assembly_stack(self.d)
        self.assertGreater(
            s["hypothetical_stem_shear_under_m3_torque_mpa"], s["indicative_peek_shear_reference_mpa"]
        )
        self.assertFalse(s["m3_torque_reaction_through_post_allowed"])
        self.assertTrue(s["temporary_holding_fixture_required"])
        self.assertFalse(s["peek_properties_are_guaranteed_allowables"])
        self.assertAlmostEqual(s["m3_nominal_thread_engagement_mm"], 3.95)

    def test_native_cad_checks_keep_real_failed_ports_and_physical_holds_distinct(self):
        self.assertEqual(self.receipt["native_collision_failures"], [])
        self.assertTrue(self.receipt["native_port_contract_matches"])
        self.assertGreater(self.receipt["native_checks"]["positive_control"]["volume_mm3"], 0.9)
        self.assertLess(self.receipt["independent_native_occ_bar_volume_relative_difference"], 0.0005)
        for flag in (
            "physical_fit_verified",
            "electrical_joint_qualified",
            "mechanical_stability_qualified",
            "fabrication_released",
            "build_ready",
        ):
            self.assertFalse(self.receipt[flag])
        self.assertEqual(self.receipt["physical_tests_performed"], 0)
        self.assertFalse(self.receipt["all_component_and_mate_heights_approved"])
        self.assertFalse(self.receipt["contact_resistance_measured"])
        self.assertFalse(self.receipt["pcb_return_access_resistance_measured"])

    def test_actual_minimum_core_sections_include_the_ramp_end_turn(self):
        cad = json.loads((OUT / "cad-verification.json").read_text())
        for name in ("ANA", "DIG"):
            rows = cad[name + "_minimum_core_section_witnesses"]
            self.assertGreater(min(r["core_area_mm2"] for r in rows), 20)
        disk = next(q for q in corner_disks(self.d, "ANA") if q[:2] == [173, 133.125])
        self.assertLess(disk[2], points(self.d, "ANA")[3][2])
        self.assertAlmostEqual(disk[2] + disk[4], points(self.d, "ANA")[3][2] + 3.5)
        override = copy.deepcopy(self.d)
        override["assembled_terminal_top_override_z_mm"] = {"E28": 11.25, "P03": 13.22}
        self.assertEqual(points(override, "ANA")[0][2], 11.25)
        self.assertEqual(points(override, "ANA")[-1][2], 13.22)


if __name__ == "__main__":
    unittest.main()
