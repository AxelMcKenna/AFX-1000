"""Synthetic, temporary parser fixtures are never physical measurement evidence."""

import copy
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.qualification.check import evaluate
from hardware.qualification.generate import template
from hardware.qualification.spec import REPO, build_plan, digest


class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_plan()
        cls.now = dt.datetime(2026, 10, 25, tzinfo=dt.timezone.utc)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="rmx-synthetic-parser-fixture-")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        fixture = self.root / "SYNTHETIC-NOT-A-MEASUREMENT.txt"
        fixture.write_text(
            "Synthetic parser fixture only; not a calibration, firmware or physical capture.\n"
        )
        self.artifact = dict(path=fixture.name, sha256=digest(fixture))
        self.record = template(self.plan)
        self.record["evidence_kind"] = "synthetic_fixture"

    def check(self, record=None, plan=None):
        return evaluate(
            plan or self.plan, record or self.record, self.root, now=self.now, allow_synthetic=True
        )

    def measured(self, identifier="source_P19", state="measured_pass"):
        case = next(c for c in self.plan["cases"] if c["id"] == identifier)
        entry = next(c for c in self.record["cases"] if c["id"] == identifier)
        self.record["operator"] = "SYNTHETIC TEST FIXTURE"
        self.record["device"].update(
            assembly_serial="SYNTHETIC",
            hardware_revision="SYNTHETIC",
            board_variant="E14/E25-baseline",
            firmware_sha256=self.artifact["sha256"],
            firmware_image=copy.deepcopy(self.artifact),
            source_commit=self.plan["source_base_commit"],
            build_source_attestation="SYNTHETIC FIXTURE ONLY; not a physical firmware claim",
        )
        self.record["setup"].update(
            description="SYNTHETIC FIXTURE",
            ambient_c=20,
            current_limit_a=0.01,
            dummy_load_description="SYNTHETIC",
            ground_probe_method="SYNTHETIC",
            supply_and_fuse_description="SYNTHETIC",
            fixture_release=dict(
                plan_sha256=self.plan["plan_sha256"],
                reviewer="SYNTHETIC",
                scope="system" if case["requires_completed_system_design"] else "isolated_board",
                document=copy.deepcopy(self.artifact),
                approved_at_utc="2026-10-23T00:00:00Z",
            ),
        )
        self.record["instruments"] = [
            dict(
                id=kind,
                kind=kind,
                model="SYNTHETIC",
                serial="SYNTHETIC",
                calibration=dict(
                    state="current",
                    valid_from_utc="2026-01-01T00:00:00Z",
                    valid_until_utc="2027-01-01T00:00:00Z",
                    certificate=copy.deepcopy(self.artifact),
                ),
            )
            for kind in case["instrument_kinds"]
        ]
        entry.update(
            state=state,
            dut=dict(board_serial="SYNTHETIC", assembly_revision="SYNTHETIC"),
            started_at_utc="2026-10-24T00:00:00Z",
            finished_at_utc="2026-10-24T00:01:00Z",
            instrument_ids=case["instrument_kinds"][:],
            captures=[dict(**self.artifact, conditions=case["conditions"][:])],
        )
        entry["readings"] = []
        for condition in case["conditions"]:
            values = {}
            for key, limit in case["metrics"].items():
                low, high = limit["minimum"], limit["maximum"]
                values[key] = (
                    limit["expected"]
                    if limit["unit"] == "bool"
                    else (
                        (low + high) / 2
                        if low is not None and high is not None
                        else low
                        if low is not None
                        else high
                        if high is not None
                        else 1
                    )
                )
            entry["readings"].append(dict(condition=condition, values=values))
        return entry

    def test_unmeasured_template_remains_not_run_or_blocked(self):
        result = self.check()
        self.assertFalse(result["all_case_comparisons_passed"])
        self.assertFalse(result["physical_measurements_claimed"])
        self.assertFalse(result["build_ready"])
        self.assertEqual(set(result["state_counts"]), {"not_run", "blocked"})

    def test_cli_require_pass_rejects_a_valid_unmeasured_template(self):
        plan = self.root / "plan.json"
        capture = self.root / "unmeasured-template.json"
        plan.write_text(json.dumps(self.plan))
        capture.write_text(json.dumps(template(self.plan)))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "hardware.qualification.check",
                str(capture),
                "--plan",
                str(plan),
                "--require-pass",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_synthetic_valid_isolated_case_exercises_comparisons_without_physical_claim(self):
        self.measured()
        result = self.check()
        self.assertEqual(result["state_counts"]["measured_pass"], 1)
        self.assertFalse(result["physical_measurements_claimed"])
        with self.assertRaisesRegex(ValueError, "Synthetic fixtures"):
            evaluate(self.plan, self.record, self.root, now=self.now)

    def test_pass_cannot_omit_readings_capture_or_metadata(self):
        self.measured()["readings"] = []
        with self.assertRaisesRegex(ValueError, "cannot omit readings"):
            self.check()
        for field in ["captures", "instrument_ids"]:
            self.record = template(self.plan)
            self.record["evidence_kind"] = "synthetic_fixture"
            self.measured()[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check()
        self.measured()
        self.record["operator"] = None
        with self.assertRaisesRegex(ValueError, "operator"):
            self.check()

    def test_unknown_missing_or_duplicate_cases_are_rejected(self):
        self.record["cases"].pop()
        with self.assertRaisesRegex(ValueError, "Missing, duplicate or unknown"):
            self.check()
        self.record = template(self.plan)
        self.record["evidence_kind"] = "synthetic_fixture"
        self.record["cases"][-1] = copy.deepcopy(self.record["cases"][0])
        with self.assertRaisesRegex(ValueError, "Missing, duplicate or unknown"):
            self.check()

    def test_stale_sources_and_edited_limits_cannot_pass(self):
        self.record["source_sha256"] = {}
        with self.assertRaisesRegex(ValueError, "snapshot"):
            self.check()
        edited = copy.deepcopy(self.plan)
        edited["cases"][0]["metrics"]["minimum_v"]["minimum"] = 0
        with self.assertRaisesRegex(ValueError, "edited/stale"):
            self.check(plan=edited)

    def test_head_only_change_does_not_stale_unchanged_design_snapshot(self):
        with patch("hardware.qualification.spec.subprocess.check_output", return_value="a" * 40):
            later = build_plan()
            self.assertNotEqual(later["source_base_commit"], self.plan["source_base_commit"])
            self.assertEqual(later["source_sha256"], self.plan["source_sha256"])
            self.assertFalse(self.check()["physical_measurements_claimed"])

    def test_device_source_context_can_be_a_later_descendant(self):
        self.measured()
        self.record["device"]["source_commit"] = "a" * 40
        with patch("hardware.qualification.check.subprocess.run") as git:
            git.return_value.returncode = 0
            result = self.check()
        self.assertEqual(result["state_counts"]["measured_pass"], 1)
        self.assertEqual(
            result["firmware_build_to_source_linkage"], "operator_attestation_not_independently_rebuilt"
        )

    def test_shallow_checkout_accepts_unchanged_unmeasured_plan_without_base_object(self):
        seed = self.root / "synthetic-source-repository"
        seed.mkdir()
        git_prefix = [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Synthetic Test Fixture",
            "-c",
            "user.email=fixture@example.invalid",
        ]

        def git(*args):
            return subprocess.run([*git_prefix, *args], cwd=seed, check=True, capture_output=True, text=True)

        git("init", "--quiet", "--initial-branch=main")
        for name in self.plan["source_sha256"]:
            target = seed / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
        git("add", ".")
        git("commit", "--quiet", "-m", "Synthetic source fixture; not project development")
        frozen = build_plan(seed)
        (seed / "frozen-plan.json").write_text(json.dumps(frozen))
        (seed / "frozen-template.json").write_text(json.dumps(template(frozen)))
        git("add", "frozen-plan.json", "frozen-template.json")
        git("commit", "--quiet", "-m", "Synthetic generated-plan fixture")
        clone = self.root / "synthetic-shallow-checkout"
        subprocess.run(
            [
                "git",
                "-c",
                "protocol.file.allow=always",
                "clone",
                "--quiet",
                "--depth",
                "1",
                seed.as_uri(),
                str(clone),
            ],
            check=True,
            capture_output=True,
        )
        missing = subprocess.run(
            ["git", "cat-file", "-e", frozen["source_base_commit"] + "^{commit}"],
            cwd=clone,
            capture_output=True,
        )
        self.assertNotEqual(missing.returncode, 0)
        shallow = subprocess.check_output(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=clone, text=True
        )
        self.assertEqual(shallow.strip(), "true")
        record = json.loads((clone / "frozen-template.json").read_text())
        result = evaluate(frozen, record, clone, repo=clone, now=self.now)
        self.assertFalse(result["source_base_context"]["base_object_available"])
        self.assertFalse(result["physical_measurements_claimed"])
        self.assertEqual(set(result["state_counts"]), {"not_run", "blocked"})
        (clone / "hardware/qualification/README.md").write_text("Changed synthetic source")
        with self.assertRaisesRegex(ValueError, "edited/stale"):
            evaluate(frozen, record, clone, repo=clone, now=self.now)

    def test_missing_physical_source_history_blocks_a_claimed_measurement_pass(self):
        entry = self.measured(state="blocked")
        with patch("hardware.qualification.check.available_commit", return_value=False):
            result = self.check()
            case = next(c for c in result["cases"] if c["id"] == "source_P19")
            self.assertEqual(case["state"], "blocked")
            self.assertTrue(any("ancestry is unavailable" in reason for reason in case["reasons"]))
            entry["state"] = "measured_pass"
            with self.assertRaisesRegex(ValueError, "derived blocked"):
                self.check()

    def test_wrong_variant_or_firmware_hash_is_rejected(self):
        self.measured()
        self.record["device"]["board_variant"] = "P01"
        with self.assertRaisesRegex(ValueError, "separate reviewed plan"):
            self.check()
        self.record["device"]["board_variant"] = "E14/E25-baseline"
        self.record["device"]["firmware_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Firmware image checksum"):
            self.check()

    def test_corrupt_or_escaped_artifacts_are_rejected(self):
        self.measured()
        (self.root / self.artifact["path"]).write_text("Corrupted synthetic fixture")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.check()
        entry = self.measured()
        # Restore the other references so this reaches the capture path check.
        (self.root / self.artifact["path"]).write_text(
            "Synthetic parser fixture only; not a calibration, firmware or physical capture.\n"
        )
        entry["captures"][0]["path"] = "../outside.txt"
        with self.assertRaisesRegex(ValueError, "inside capture directory"):
            self.check()

    def test_expired_calibration_future_dates_and_incomplete_conditions_are_rejected(self):
        self.measured()
        self.record["instruments"][0]["calibration"]["valid_until_utc"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "Calibration"):
            self.check()
        entry = self.measured()
        entry["finished_at_utc"] = "2027-10-24T00:01:00Z"
        with self.assertRaisesRegex(ValueError, "future"):
            self.check()
        self.measured()["readings"].pop()
        with self.assertRaisesRegex(ValueError, "condition readings"):
            self.check()

    def test_negative_rail_polarity_and_nonfinite_numbers_are_rejected(self):
        entry = self.measured("source_N19")
        self.assertEqual(self.check()["state_counts"]["measured_pass"], 1)
        for reading in entry["readings"]:
            reading["values"] = dict(minimum_v=18.9, maximum_v=19)
        entry["state"] = "failed"
        self.assertEqual(self.check()["state_counts"]["failed"], 1)
        for value in [float("nan"), float("inf"), True, "-19 V"]:
            entry["readings"][0]["values"]["minimum_v"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Non-finite/non-numeric"):
                self.check()

    def test_unqualified_timing_and_current_design_holds_cannot_be_passed(self):
        entry = self.measured("startup", state="blocked")
        result = self.check()
        row = next(c for c in result["cases"] if c["id"] == "startup")
        self.assertEqual(row["state"], "blocked")
        self.assertTrue(any("Unqualified" in reason for reason in row["reasons"]))
        entry["state"] = "measured_pass"
        with self.assertRaisesRegex(ValueError, "derived blocked"):
            self.check()
        sd = next(c for c in self.plan["cases"] if c["id"] == "sd_boot")
        self.assertIsNone(sd["metrics"]["boot_elapsed_ms"]["maximum"])

    def test_soak_duration_cannot_exceed_capture_interval(self):
        self.measured("soak", state="failed")
        self.assertEqual(self.check()["state_counts"]["failed"], 1)

    def test_send_return_noise_target_is_stricter_than_master(self):
        entry = self.measured("audio_quality", state="failed")
        for row in entry["readings"]:
            row["values"]["snr_db"] = 100
        result = self.check()
        case = next(c for c in result["cases"] if c["id"] == "audio_quality")
        self.assertIn("send_return: snr_db", case["reasons"])
        self.assertNotIn("master: snr_db", case["reasons"])


if __name__ == "__main__":
    unittest.main()
