"""Portable native-evidence and input/geometry contract regressions."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import capture
from .audit import check
from .capture import ROOT
from .model import world_box
from .replay import stage
from .verify import errors, specs


class Receiving(unittest.TestCase):
    def test_actual_current_part_and_mechanical_counts(self):
        d = json.loads((ROOT / "generated/model.json").read_text())
        self.assertEqual(
            (len(d["component_records"]), d["electrical_parts"], d["total_native_FPs"]), (356, 356, 358)
        )
        self.assertEqual(
            {b["id"]: (b["parts"], b["native_FPs"]) for b in d["boards"]},
            {"NF265": (265, 267), "FPC91": (91, 91)},
        )
        self.assertEqual(len({r["id"] for r in d["component_records"]}), 356)

    def test_frame_is_proper_and_rear_goes_toward_front_wall(self):
        actual = world_box([172, 180.5, 3.5], [0, 0, 1, 1], -3.66, -1.76)
        for a, b in zip(actual, [172, 182.26, 3.5, 1, 1.9, 1]):
            self.assertAlmostEqual(a, b, places=12)
        d = json.loads((ROOT / "generated/model.json").read_text())
        self.assertTrue(all(b["rotation_determinant"] == 1 for b in d["boards"]))

    def test_all14_named_rear_exceptions_and_other_policy(self):
        d = json.loads((ROOT / "generated/model.json").read_text())
        refs = {"C4", "C5", "C6", "C7", "C9", "C11", "C13", "C31", "C32", "C33", "C34", "C36", "C38", "C40"}
        self.assertEqual(set(d["rear_named1p9"]), refs)
        for r in d["component_records"]:
            if r["native_side"] == "B":
                expected = 1.9 if r["id"].startswith("NF265_") and r["ref"] in refs else 1.2
                self.assertAlmostEqual(r["projection_mm"], expected, places=12)

    def test_actual_signed_port_contract_and_split_primary_return(self):
        d = json.loads((ROOT / "supplement/contract.json").read_text())
        p = {r["ref"]: r["physical_pads"] for r in d["port_native_checks"]}
        self.assertEqual(sum(map(len, p.values())), 40)
        self.assertIsNone(p["J1"]["4"])
        self.assertEqual(p["J1"]["7"], "ABS_AUX_FAULT")
        self.assertEqual(p["J6"], {"1": "GUARDED_12V_FORCE", "2": "MODULE_INPUT_GND"})
        self.assertNotEqual(p["J6"]["2"], p["J1"]["2"])

    def test_native_rectangular_tail_axes_and_subset(self):
        d = json.loads((ROOT / "tail_shape/audit.json").read_text())
        self.assertEqual(len(d["pad_receiving_corrections"]), 106)
        for a in d["pad_receiving_corrections"]:
            old, new = a["old_square_row"], a["new_rectangular_row"]
            for i in range(3):
                self.assertLessEqual(old[i + 1] - 1e-8, new[i + 1])
                self.assertLessEqual(new[i + 1] + new[i + 4], old[i + 1] + old[i + 4] + 1e-8)
        a = next(r for r in d["pad_receiving_corrections"] if r["id"] == "NF265_U17.1")
        self.assertEqual(a["actual_native_pad_size_mm"], [1.5, 3.0])
        self.assertAlmostEqual(a["new_rectangular_row"][4], 1.9)
        self.assertAlmostEqual(a["new_rectangular_row"][6], 3.4)

    def test_saved_native_input_artifact_and_rejected_state_integrity(self):
        d = check()
        self.assertTrue(d["saved_evidence_integrity_clear"], d["errors"])
        self.assertFalse(d["all_receiving_geometry_clear"])
        self.assertEqual(d["reports"]["generated/tail-shape-native01/verification.json"]["clear"], 42)

    def test_missing_required_copper_or_body_cannot_pass_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            n = "NF265_components_geometry"
            (p / (n + ".log")).write_text("Current top level object is empty.\n")
            self.assertIn(
                "required-solid-missing", errors(n, dict(returncode=1, statistics=None), specs()[n], p)
            )

    def test_actual_nonempty_collision_rejects_forged_empty_row(self):
        root = ROOT / "generated/preflight01"
        n = "NF265_mate_other_components_collision"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            shutil.copy2(root / (n + ".stl"), p / (n + ".stl"))
            (p / (n + ".log")).write_text("Current top level object is empty.\n")
            self.assertIn(
                "nonempty-or-execution-failed", errors(n, dict(returncode=1, statistics=None), specs()[n], p)
            )

    def test_positive_control_wrong_statistics_fail(self):
        n = "NF265_PCB_positive_control"
        folder = ROOT / "generated/preflight01"
        d = json.loads((folder / "verification.json").read_text())
        row = copy.deepcopy(d["cases"][n])
        row["statistics"]["volume_mm3"] = 0.008
        self.assertIn("actual-saved-solid-mismatch", errors(n, row, specs()[n], folder))

    def test_unknown_native_case_cli_is_nonzero_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out"
            p = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hardware.cad.a12.enclosure_growth.nf265_fpc91.native_variant",
                    "--variant",
                    "tail_shape",
                    "--outdir",
                    str(target),
                    "--cases",
                    "UNDECLARED",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(target.exists())

    def test_capture_refuses_existing_snapshot(self):
        with self.assertRaises(RuntimeError):
            capture.capture()

    def test_captured_replay_closure_is_private_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "replay"
            target = stage(target)
            manifest = json.loads((target / "replay.json").read_text())
            private = capture.closure(Path(manifest["entry"]))
            self.assertTrue(all(target in p.parents for p in private))
            self.assertFalse(manifest["live_parent_designs_read"])
            with self.assertRaises(RuntimeError):
                stage(target)

    def test_real_bore_and_primary_body_positive_controls(self):
        d = json.loads((ROOT / "generated/supplement-native01/verification.json").read_text())
        self.assertEqual(len(d["cases"]), 6)
        self.assertTrue(d["all_requested_clear"])
        self.assertGreater(
            d["cases"]["actual_old_force_bore_failure_witness"]["statistics"]["volume_mm3"], 16
        )
        self.assertTrue(d["cases"]["actual_C401_C402_tail_margin_collision"]["clear"])


if __name__ == "__main__":
    unittest.main()
