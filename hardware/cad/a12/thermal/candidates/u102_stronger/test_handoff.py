"""Portable actual-artifact mutations; no solver/native tools required."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import handoff


class StrongerCellEvidence(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((handoff.OUT / "verification.json").read_text())
        self.geometry = json.loads((handoff.OUT / "geometry.json").read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        for p in handoff.OUT.iterdir():
            if p.suffix in {".stl", ".log"}:
                shutil.copy2(p, self.output / p.name)

    def errors(self):
        return handoff.artifact_errors(self.report, self.geometry, self.output)

    def test_actual_selected_source_and_all_saved_native_artifacts(self):
        self.assertEqual(handoff.packet_errors(), [])
        self.assertEqual(self.errors(), [])

    def test_complete_seal_and_stale_byte_mutation(self):
        a = json.loads((handoff.ROOT / "handoff.json").read_text())
        self.assertEqual(handoff.saved_seal_errors(a), [])
        first = next(iter(a["sha256"]))
        a["sha256"][first] = "0" * 64
        self.assertTrue(handoff.saved_seal_errors(a))

    def test_missing_required_copper_cannot_be_declared_empty(self):
        (self.output / "geometry.stl").unlink()
        self.report["native_checks"]["geometry"] = dict(result="empty", returncode=1)
        self.assertTrue(any("geometry" in e for e in self.errors()))

    def test_missing_separate_land_fails_even_if_combined_exists(self):
        (self.output / "LAND.stl").unlink()
        self.assertTrue(any("LAND" in e for e in self.errors()))

    def test_forged_empty_collision_with_actual_solid_is_rejected(self):
        shutil.copy2(self.output / "positive_control.stl", self.output / "component_collision.stl")
        self.assertTrue(any("forged empty" in e for e in self.errors()))

    def test_real_nonzero_collision_rejected_even_with_matching_metadata(self):
        name = "link_collision"
        shutil.copy2(self.output / "positive_control.stl", self.output / (name + ".stl"))
        shutil.copy2(self.output / "positive_control.log", self.output / (name + ".log"))
        self.report["native_checks"][name] = copy.deepcopy(self.report["native_checks"]["positive_control"])
        self.assertIn(name + ": collision", self.errors())

    def test_witness_actual_metadata_and_volume_enforced(self):
        name = "J106_tail_witness"
        self.report["native_checks"][name]["volume_mm3"] = 0
        self.assertTrue(any("mismatch" in e for e in self.errors()))
        shutil.copy2(self.output / "geometry.stl", self.output / (name + ".stl"))
        self.report["native_checks"][name].update(handoff.binary_stl(self.output / (name + ".stl")))
        self.assertIn(name + ": witness failed", self.errors())

    def test_cli_rejection_exits_nonzero(self):
        with (
            patch.object(handoff, "packet_errors", return_value=["Injected missing copper"]),
            patch.object(handoff, "ROOT", self.output),
            patch.object(handoff, "REPO", self.output),
        ):
            with self.assertRaises(SystemExit) as error:
                handoff.main()
            self.assertNotEqual(error.exception.code, 0)
            self.assertFalse(
                json.loads((self.output / "handoff.json").read_text())["packet_integrity_accepted"]
            )

    def test_saved_sensitivity_is_correct_thickness_and_remains_unqualified(self):
        a = json.loads((handoff.OUT / "front-cell-thermal.json").read_text())
        self.assertEqual(a["pcb_sha256"], handoff.PCB)
        rows = a["scenarios"]
        fine = next(r["result"] for r in rows if r["grid"] == 320 and r["scenario"] == "sensitivity")
        self.assertAlmostEqual(fine["conditional_total_junction_to_base_c_per_w"], 41.9246637491, places=7)
        self.assertAlmostEqual(a["conditional65base_plus2uncertainty_c"], 107.3024695195, places=7)
        self.assertFalse(a["thermal_path_qualified"])
        self.assertFalse(a["physical_loop_length_and_stability_acceptance"])
        self.assertIsNone(a["total_path_upper_k_per_w"])
        self.assertIsNone(a["actual_local_base_upper_c"])
        self.assertEqual(a["physical_tests_performed"], 0)


if __name__ == "__main__":
    unittest.main()
