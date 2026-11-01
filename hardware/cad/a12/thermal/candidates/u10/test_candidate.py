"""Actual-source/face/polarity/artifact mutations; numeric solver optional."""

import copy
import json
import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

from .analyze import ep_contract, required_path
from .generate import OUT, ROOT
from .handoff import CASES, artifact_errors
from .network import REPO, saved_pad_angle, sha, solve


class U10Candidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = json.loads((OUT / "analysis.json").read_text())
        cls.native = json.loads((OUT / "verification.json").read_text())

    def test_actual_dd_live_ep_and_source_faces(self):
        before = ep_contract(ROOT / "sources/power_p03.kicad_pcb")
        after = ep_contract(ROOT / "variant/power_p03.kicad_pcb")
        self.assertEqual(before["U10"]["face"], "B.Cu")
        self.assertEqual(after["U10"]["face"], "F.Cu")
        self.assertEqual(before["U10"]["housing_xy_mm"], [260.5, 136.5])
        self.assertEqual(after["U10"]["housing_xy_mm"], [262.2, 137.3])
        self.assertEqual(after["U10"]["ep_node"], "RAW_N22")
        self.assertEqual(after["U11"]["ep_node"], "RAW_N17")
        self.assertEqual(after["U11"]["face"], "F.Cu")
        self.assertEqual(after["U10"]["package_theta_jc_reference_k_per_w"], 5.5)
        self.assertFalse(self.a["primary_source"]["contacting_plastic_top_is_equivalent"])

    def test_wrong_live_net_or_part_cannot_use_dd_metric(self):
        original = read_sexpr((ROOT / "variant/power_p03.kicad_pcb").read_text())
        for mode in ["ground", "wrongpart"]:
            tree = copy.deepcopy(original)
            f = next(
                f
                for f in children(tree, "footprint")
                if any(p[1:3] == ["Reference", "U10"] for p in children(f, "property"))
            )
            if mode == "ground":
                first(next(p for p in children(f, "pad") if p[1] == "11"), "net")[1] = "/AGND"
            else:
                next(p for p in children(f, "property") if p[1] == "Value")[2] = "TPS7A1601DGNR"
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "wrong.kicad_pcb"
                p.write_text(sexpr(tree))
                with self.assertRaises(AssertionError):
                    ep_contract(p)

    def test_saved_pad_angles_match_independent_native_reader(self):
        native = json.loads((ROOT / "sources/native-pad-orientation.json").read_text())
        pcb = ROOT / "variant/power_p03.kicad_pcb"
        self.assertEqual(sha(pcb), native["pcb_sha256"])
        self.assertEqual(sha(ROOT / "native_pad_orientation.py"), native["reader_source_sha256"])
        tree = read_sexpr(pcb.read_text())
        fps = {
            next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
            for f in children(tree, "footprint")
        }
        for row in native["rows"]:
            pad = next(p for p in children(fps[row["reference"]], "pad") if p[1] == row["pad"])
            angle = saved_pad_angle(pad)
            self.assertEqual(angle, row["pad_absolute_angle_degrees"])
            x, y = map(float, first(pad, "size")[1:3])
            c, s = abs(math.cos(math.radians(angle))), abs(math.sin(math.radians(angle)))
            for observed, expected in zip([x * c + y * s, x * s + y * c], row["world_bbox_size_mm"]):
                self.assertAlmostEqual(observed, expected, places=6)
        c51 = next(r for r in native["rows"] if r["reference"] == "C51")
        self.assertEqual(c51["footprint_angle_degrees"], 90)
        self.assertEqual(c51["pad_absolute_angle_degrees"], 90)
        self.assertEqual(c51["world_bbox_size_mm"], [2.7, 1.15])
        # The old double-addition is demonstrably inconsistent with native geometry.
        self.assertNotEqual([1.15, 2.7], c51["world_bbox_size_mm"])

    def test_real_copper_and_routing_obligations_are_explicit(self):
        a = self.a
        n = a["nominal"]["results"][-1]
        self.assertEqual(n["native_ep"]["face"], "F.Cu")
        self.assertEqual(n["actual_via_centres_inside_ep"], 4)
        self.assertGreater(n["sink_area_under_matching_bottom_copper_mm2"], 8)
        self.assertLess(n["sink_area_under_matching_bottom_copper_mm2"], n["metal_contact_area_mm2"])
        self.assertEqual(n["source_dimensions_mm"], [1.55, 2.28])
        self.assertLess(n["kcl_residual_w"], 1e-8)
        self.assertFalse(n["fictitious_sink_or_gmin_added"])
        self.assertEqual(a["actual_native_electrical"]["opens"], 16)
        self.assertEqual(a["actual_native_electrical"]["hard_drc"], 0)
        self.assertFalse(a["actual_native_electrical"]["electrically_complete"])
        plan = json.loads((ROOT / "relocation-clearance-plan.json").read_text())
        self.assertEqual(len(plan["removed_source_objects"]), 22)

    def test_sensitivity_failure_cannot_be_promoted_to_qualified(self):
        n = self.a["nominal"]["results"][-1]
        s = self.a["illustrative_sensitivity"]["results"][-1]
        self.assertLess(n["conditional_junction_at_60c_base_c"], 110)
        self.assertGreater(s["conditional_junction_at_60c_base_c"], 110)
        self.assertAlmostEqual(s["native_stack_total_mm"], 1.76)
        self.assertFalse(self.a["illustrative_sensitivity"]["manufacturer_guaranteed_enclosure"])
        self.assertFalse(self.a["acceptance"]["guardbanded_project_acceptance"])
        self.assertIsNone(self.a["acceptance"]["path_upper_k_per_w"])
        self.assertLess(required_path(65, 2), required_path(60, 0))
        with self.assertRaises(ValueError):
            required_path(60, -1)

    def test_actual_native_geometry_and_both_face_tail_witnesses(self):
        self.assertEqual(artifact_errors(self.native), [])
        self.assertEqual(set(self.native["native_checks"]), set(CASES))
        for name in ["positive_control", "source_front_witness", "C32_tail_witness"]:
            self.assertAlmostEqual(self.native["native_checks"][name]["volume_mm3"], 0.008, places=5)

    def test_missing_geometry_or_forged_empty_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            for name in CASES:
                p = OUT / (name + ".stl")
                if p.exists():
                    shutil.copy2(p, out / p.name)
                shutil.copy2(OUT / (name + ".log"), out / (name + ".log"))
            self.assertEqual(artifact_errors(self.native, out), [])
            (out / "geometry.stl").unlink()
            self.assertTrue(artifact_errors(self.native, out))
            shutil.copy2(OUT / "geometry.stl", out / "geometry.stl")
            shutil.copy2(OUT / "positive_control.stl", out / "component_collision.stl")
            self.assertTrue(artifact_errors(self.native, out))
        changed = copy.deepcopy(self.native)
        changed["native_checks"]["source_front_witness"]["volume_mm3"] = 0
        self.assertTrue(artifact_errors(changed))

    def test_all_sealed_artifacts_and_inputs_intact(self):
        h = json.loads((ROOT / "handoff.json").read_text())
        self.assertTrue(h["packet_integrity_accepted"])
        self.assertFalse(h["routing_complete"])
        self.assertFalse(h["thermal_path_qualified"])
        for path, expected in h["sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)
        for path, expected in self.a["source_sha256"].items():
            self.assertEqual(sha(REPO / path), expected, path)

    @unittest.skipUnless(os.environ.get("AFX_THERMAL_SOLVERS") == "1", "Optional NumPy/SciPy solve")
    def test_actual_saved_copper_numeric_replay(self):
        result = solve(
            [190.1, 127.7, 193.75, 131.4],
            grid=160,
            pcb_path=ROOT / "variant/power_p03.kicad_pcb",
            via_wall_um=50,
            contact_c_per_w=0.8,
        )
        self.assertAlmostEqual(
            result["conditional_total_junction_to_base_c_per_w"],
            self.a["nominal"]["results"][0]["conditional_total_junction_to_base_c_per_w"],
            places=8,
        )
        with self.assertRaises(AssertionError):
            solve(
                [190.1, 131.5, 193.75, 135.5],
                grid=160,
                pcb_path=ROOT / "sources/power_p03.kicad_pcb",
                via_wall_um=50,
            )


if __name__ == "__main__":
    unittest.main()
