"""Actual-source mutations; optional solver replay; no tool or download requirement."""

import copy
import json
import math
import os
import unittest

from hardware.cad.a12.thermal.candidates.u10.candidate import geometry_inventory
from hardware.cad.a12.thermal.candidates.u10.handoff import artifact_errors
from hardware.cad.a12.thermal.candidates.u10.network import solve
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr

from .contract import ep_vias
from .handoff import required_volume_errors
from .synthesize import BASE, CONTACT, ROOT


class StrongerU10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = read_sexpr((ROOT / "variant/power_p03.kicad_pcb").read_text())
        cls.analysis = json.loads((ROOT / "generated/analysis.json").read_text())

    def test_actual_eight_barrels_and_factory_dimensions(self):
        c = ep_vias(self.tree)
        self.assertEqual(c["actual_ep_via_count"], 8)
        self.assertAlmostEqual(c["minimum_finished_bore_edge_gap_mm"], 0.25)
        self.assertFalse(c["process_approved"])
        self.assertIsNone(c["factory_plating_maximum_um"])

    def test_missing_or_wrong_net_barrel_cannot_pass(self):
        for mode in ["missing", "wrongnet", "hole"]:
            tree = copy.deepcopy(self.tree)
            via = next(
                v for v in children(tree, "via") if [float(x) for x in first(v, "at")[1:3]] == [193.8, 128.55]
            )
            if mode == "missing":
                tree.remove(via)
            elif mode == "wrongnet":
                first(via, "net")[1] = "/AGND"
            else:
                first(via, "drill")[1] = ".3"
            with self.assertRaises(AssertionError):
                ep_vias(tree)

    def test_actual_pose_unchanged_and_ledger_does_not_waive_opens(self):
        original = read_sexpr((BASE / "variant/power_p03.kicad_pcb").read_text())
        self.assertEqual(
            geometry_inventory(original)["footprints"], geometry_inventory(self.tree)["footprints"]
        )
        receipt = self.analysis["native_electrical"]
        self.assertEqual(len(receipt["additional_removed_objects"]), 82)
        self.assertEqual(receipt["opens"], 19)
        self.assertEqual(receipt["hard_drc"], 0)
        self.assertFalse(receipt["electrically_complete"])
        self.assertIn("NREF_FILTER", {r["node"] for r in receipt["additional_removed_objects"]})

    def test_no_allowances_shrunk_and_no_package_upper_invented(self):
        prior = json.loads((BASE / "generated/analysis.json").read_text())["illustrative_sensitivity"][
            "results"
        ][-1]
        new = self.analysis["scenarios"][-1]["result"]
        for k in [
            "tim_gap_assumed_mm",
            "tim_k_typical_w_per_mk",
            "copper_k_assumed_w_per_mk",
            "extra_contact_assumed_c_per_w",
            "native_stack_total_mm",
            "power_allocation_w",
            "package_theta_jc_c_per_w",
        ]:
            self.assertEqual(prior[k], new[k], k)
        self.assertEqual(new["actual_via_centres_inside_ep"], 8)
        self.assertGreater(new["sink_area_under_matching_bottom_copper_mm2"], 13)
        self.assertLess(new["sink_area_under_matching_bottom_copper_mm2"], 13.505)
        self.assertLess(
            new["conditional_junction_at_60c_base_c"], prior["conditional_junction_at_60c_base_c"]
        )
        self.assertFalse(self.analysis["thermal_path_qualified"])
        self.assertIsNone(self.analysis["package_upper_k_per_w"])
        self.assertIsNone(self.analysis["acceptance"]["total_path_upper_k_per_w"])

    def test_all_native_cases_and_missing_geometry_mutation(self):
        report = json.loads((ROOT / "generated/verification.json").read_text())
        self.assertEqual(artifact_errors(report, ROOT / "generated"), [])
        bad = copy.deepcopy(report)
        bad["native_checks"]["geometry"]["result"] = "empty"
        self.assertTrue(artifact_errors(bad, ROOT / "generated"))

    def test_partial_required_geometry_cannot_pass_as_full_kit(self):
        from hardware.cad.a12.thermal.verify import binary_stl

        native = json.loads((ROOT / "generated/verification.json").read_text())
        geometry = json.loads((ROOT / "generated/geometry.json").read_text())
        self.assertEqual(required_volume_errors(native, geometry), [])
        # A real, valid nonempty LAND solid alone is insufficient when TIM is required.
        native["native_checks"]["geometry"] = binary_stl(ROOT / "generated/LAND.stl")
        self.assertGreater(native["native_checks"]["geometry"]["volume_mm3"], 1)
        self.assertTrue(required_volume_errors(native, geometry))

    def test_u102_native_angle_audit_and_thickness_hold(self):
        audit = json.loads((ROOT / "generated/u102-angle-audit.json").read_text())
        native = json.loads((ROOT / "sources/u102-native-pad-orientation.json").read_text())
        c = next(r for r in native["rows"] if r["reference"] == "C109")
        self.assertEqual(c["pad_absolute_angle_degrees"], 90)
        self.assertEqual(c["world_bbox_size_mm"], [1.45, 1])
        for r in audit["comparisons"]:
            self.assertLess(abs(r["junction_change_c"]), 0.0001)
        thick = audit["corrected_extra_1p76mm_sensitivity"]
        self.assertAlmostEqual(thick["native_stack_total_mm"], 1.76)
        self.assertGreater(thick["conditional_junction_at_60c_base_c"] + 5 + 2, 110)
        self.assertFalse(audit["frozen_files_modified"])

    def test_historical_u10_and_all_new_bound_inputs_unchanged(self):
        h = json.loads((BASE / "handoff.json").read_text())
        for p, expected in h["sha256"].items():
            self.assertEqual(sha(REPO / p), expected, p)
        seal = json.loads((ROOT / "handoff.json").read_text())
        self.assertTrue(seal["packet_integrity_accepted"])
        for p, expected in seal["sha256"].items():
            self.assertEqual(sha(REPO / p), expected, p)
        for r in [self.analysis, json.loads((ROOT / "generated/u102-angle-audit.json").read_text())]:
            for p, expected in r["source_sha256"].items():
                self.assertEqual(sha(REPO / p), expected, p)

    @unittest.skipUnless(
        os.environ.get("AFX_THERMAL_SOLVERS") == "1", "Optional NumPy/SciPy actual-copper solve"
    )
    def test_actual_saved_network_replay(self):
        result = solve(
            CONTACT,
            grid=160,
            pcb_path=ROOT / "variant/power_p03.kicad_pcb",
            via_wall_um=50,
            tim_k=6,
            tim_gap_mm=1.22,
            contact_c_per_w=0.8,
            copper_k=385,
        )
        expected = self.analysis["scenarios"][0]["result"]
        self.assertAlmostEqual(
            result["conditional_total_junction_to_base_c_per_w"],
            expected["conditional_total_junction_to_base_c_per_w"],
            places=8,
        )
        self.assertTrue(math.isfinite(result["ep_peak_to_land_network_c_per_w"]))


if __name__ == "__main__":
    unittest.main()
