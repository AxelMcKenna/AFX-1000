"""Synthetic metrology/parser regressions are never physical PCB evidence."""

import copy
import csv
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.qualification.boards import check
from hardware.qualification.boards.generate import template
from hardware.qualification.boards.requirements import build_plan, limit, native_source_check
from hardware.qualification.spec import digest


class BoardQualification(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="afx-synthetic-not-physical-")
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)
        self.plan = build_plan()
        self.record = template(self.plan)
        self.record["evidence_kind"] = "synthetic_fixture"
        self.now = dt.datetime(2026, 10, 25, tzinfo=dt.timezone.utc)

    def artifact(self, name, content):
        path = self.directory / name
        path.write_text("SYNTHETIC FIXTURE ONLY; NOT A MEASUREMENT\n" + content)
        return dict(path=name, sha256=digest(path))

    def attempt(self, identifier="source_N19", value=-19, uncertainty=0.001, state="measured_pass"):
        case = next(c for c in self.plan["cases"] if c["id"] == identifier)
        entry = next(c for c in self.record["cases"] if c["id"] == identifier)
        board = self.plan["boards"][case["board"]]
        document = self.artifact("review.txt", "Synthetic source/fixture/calibration review")
        self.record["operator"] = "SYNTHETIC TEST OPERATOR"
        self.record["devices"][case["board"]] = dict(
            serial="SYNTHETIC",
            assembly_revision="SYNTHETIC",
            variant=board["variant"],
            pcb_source_sha256=board["pcb_sha256"],
            source_to_device_attestation="SYNTHETIC ONLY",
            as_built_manifest=document,
            fabrication_package=document,
        )
        for kind in case["instrument_kinds"]:
            self.record["instruments"].append(
                dict(
                    id=kind,
                    kind=kind,
                    model="SYNTHETIC",
                    serial="SYNTHETIC",
                    calibration=dict(
                        valid_from_utc="2026-01-01T00:00:00Z",
                        valid_until_utc="2027-01-01T00:00:00Z",
                        certificate=document,
                    ),
                    method_reference=document,
                )
            )
        csv_path = self.directory / "measurements.csv"
        with csv_path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(check.COLUMNS)
            for condition in case["conditions"]:
                for metric, criterion in case["metrics"].items():
                    writer.writerow(
                        [
                            identifier,
                            condition,
                            metric,
                            value,
                            uncertainty,
                            criterion["unit"],
                            case["instrument_kinds"][0],
                        ]
                    )
        raw = self.artifact(
            "original-instrument.txt", "Synthetic original capture, distinct from the summary"
        )
        entry.update(
            state=state,
            started_at_utc="2026-10-24T00:00:00Z",
            finished_at_utc="2026-10-24T00:01:00Z",
            measurements_csv=dict(path=csv_path.name, sha256=digest(csv_path)),
            raw_captures=[dict(**raw, conditions=case["conditions"])],
            instrument_ids=case["instrument_kinds"][:],
            fixture=dict(
                plan_sha256=self.plan["plan_sha256"],
                board=case["board"],
                reviewer="SYNTHETIC",
                approved_at_utc="2026-10-23T00:00:00Z",
                document=document,
                condition_settings={
                    c: "SYNTHETIC reviewed numeric settings; not physical evidence"
                    for c in case["conditions"]
                },
            ),
            uncertainty_budget=dict(
                reviewer="SYNTHETIC",
                coverage_probability=0.95,
                coverage_factor=2,
                approved_at_utc="2026-10-23T00:00:00Z",
                document=document,
            ),
        )
        return entry

    def evaluate(self, *, production=False, plan=None):
        # Freeze only the trusted builder result while synthetic parser fixtures
        # are exercised. Domain agents may be refreshing independent audit files.
        with patch.object(check, "build_plan", return_value=self.plan):
            return check.evaluate(
                plan or self.plan, self.record, self.directory, now=self.now, allow_synthetic=not production
            )

    def rewrite_csv(self, transform):
        path = self.directory / "measurements.csv"
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream))
        transform(rows)
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
        for entry in self.record["cases"]:
            if entry.get("measurements_csv"):
                entry["measurements_csv"]["sha256"] = digest(path)

    def test_no_measurements_cannot_become_qualified(self):
        result = self.evaluate()
        self.assertEqual(result["physical_cases_claimed"], 0)
        self.assertTrue(all(not b["qualified"] for b in result["boards"].values()))
        self.assertFalse(result["build_ready"])
        self.assertFalse(result["fabrication_released"])

    def test_production_rejects_synthetic_fixture(self):
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            self.evaluate(production=True)

    def test_guardband_signed_negative_voltage(self):
        criterion = limit("V", -19.19, -18.81, source="synthetic project window")
        self.assertEqual(check.decision(-19, 0.01, criterion), "measured_pass")
        self.assertEqual(check.decision(-19.185, 0.01, criterion), "blocked")
        self.assertEqual(check.decision(-20, 0.01, criterion), "failed")
        self.assertEqual(check.decision(19, 0.01, criterion), "failed")

    def test_zero_uncertainty_is_not_a_physical_voltage_measurement(self):
        with self.assertRaisesRegex(ValueError, "positive expanded uncertainty"):
            check.decision(5, 0, limit("V", 4.9, 5.1, source="test"))

    def test_unknown_limit_stays_blocked(self):
        self.assertEqual(check.decision(0.1, 0.001, limit("V")), "blocked")

    def test_absolute_stress_limit_can_fail_but_never_qualify_operation(self):
        criterion = limit("V/us", 0, 1, source="synthetic absolute stress limit")
        criterion["status"] = "absolute_stress_screen_only"
        self.assertEqual(check.decision(0.5, 0.1, criterion), "blocked")
        self.assertEqual(check.decision(2, 0.1, criterion), "failed")

    def test_rejected_bias_window_has_no_approved_replacement(self):
        case = next(c for c in self.plan["cases"] if c["id"] == "adc_nbias")
        for metric in ["NBIAS_L_v", "NBIAS_R_v"]:
            self.assertEqual(case["metrics"][metric]["status"], "acceptance_limit_missing")
            self.assertIsNone(case["metrics"][metric]["maximum"])

    def test_common_validator_sources_are_bound_to_the_plan(self):
        self.assertIn("hardware/qualification/check.py", self.plan["source_sha256"])
        self.assertIn("hardware/qualification/spec.py", self.plan["source_sha256"])

    def test_nonfinite_negative_uncertainty_and_overflow_rejected(self):
        criterion = limit("V", 0, 1, source="test")
        for value, uncertainty in [(float("nan"), 0.1), (0.5, float("inf")), (0.5, -0.1), (1e308, 1e308)]:
            with self.assertRaises(ValueError):
                check.decision(value, uncertainty, criterion)

    def test_actual_csv_drives_the_signed_comparison_without_firmware(self):
        self.attempt()
        result = self.evaluate()
        case = next(c for c in result["cases"] if c["id"] == "source_N19")
        self.assertEqual(case["state"], "measured_pass")
        self.assertFalse(result["boards"]["psu"]["qualified"])
        self.assertEqual(result["physical_cases_claimed"], 0)

    def test_claimed_pass_cannot_ignore_uncertainty_overlap(self):
        self.attempt(value=-19.185, uncertainty=0.01)
        with self.assertRaisesRegex(ValueError, "derived blocked"):
            self.evaluate()

    def test_wrong_polarity_is_a_measured_failure(self):
        self.attempt(value=19, state="failed")
        self.assertEqual(
            next(c for c in self.evaluate()["cases"] if c["id"] == "source_N19")["state"], "failed"
        )

    def test_altering_only_the_plan_limits_is_rejected(self):
        altered = copy.deepcopy(self.plan)
        altered["cases"][0]["metrics"]["unintended_short_count"]["maximum"] = 100
        with self.assertRaisesRegex(ValueError, "stale or its limits"):
            self.evaluate(plan=altered)

    def test_missing_conditions_duplicates_units_and_instrument_fail(self):
        self.attempt()
        original = (self.directory / "measurements.csv").read_bytes()
        transforms = [
            lambda rows: rows.pop(),
            lambda rows: rows.append(rows[1][:]),
            lambda rows: rows[1].__setitem__(5, "mV"),
            lambda rows: rows[1].__setitem__(6, "UNKNOWN"),
        ]
        for change in transforms:
            (self.directory / "measurements.csv").write_bytes(original)
            self.rewrite_csv(change)
            with self.assertRaises(ValueError):
                self.evaluate()

    def test_unused_dmm_does_not_allow_temperature_instrument_to_measure_voltage(self):
        self.attempt()
        self.rewrite_csv(lambda rows: [row.__setitem__(6, "temperature") for row in rows[1:]])
        with self.assertRaisesRegex(ValueError, "Instrument kind cannot measure"):
            self.evaluate()

    def test_foreign_variant_cannot_use_the_baseline_plan(self):
        self.attempt()
        self.record["devices"]["psu"]["variant"] = "P02"
        with self.assertRaisesRegex(ValueError, "Wrong board variant"):
            self.evaluate()

    def test_wrong_pcb_source_cannot_pass(self):
        self.attempt()
        self.record["devices"]["psu"]["pcb_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Wrong fabricated PCB"):
            self.evaluate()

    def test_expired_calibration_or_missing_budget_cannot_pass(self):
        entry = self.attempt()
        self.record["instruments"][0]["calibration"]["valid_until_utc"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "Calibration"):
            self.evaluate()
        self.record["instruments"][0]["calibration"]["valid_until_utc"] = "2027-01-01T00:00:00Z"
        entry["uncertainty_budget"] = {}
        with self.assertRaisesRegex(ValueError, "uncertainty-budget reviewer"):
            self.evaluate()

    def test_future_times_and_postdated_fixture_review_rejected(self):
        entry = self.attempt()
        entry["finished_at_utc"] = "2030-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "Invalid/future"):
            self.evaluate()
        entry["finished_at_utc"] = "2026-10-24T00:01:00Z"
        entry["fixture"]["approved_at_utc"] = "2026-10-24T00:02:00Z"
        with self.assertRaisesRegex(ValueError, "postdates"):
            self.evaluate()

    def test_summary_cannot_be_relabelled_as_raw_evidence(self):
        entry = self.attempt()
        entry["raw_captures"][0].update(entry["measurements_csv"])
        with self.assertRaisesRegex(ValueError, "independent raw capture"):
            self.evaluate()

    def test_raw_checksum_tamper_and_escape_are_rejected(self):
        entry = self.attempt()
        raw = entry["raw_captures"][0]
        (self.directory / raw["path"]).write_text("TAMPERED SYNTHETIC FIXTURE")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.evaluate()
        raw["path"] = "../outside.txt"
        with self.assertRaisesRegex(ValueError, "inside capture"):
            self.evaluate()

    def test_incomplete_native_board_cannot_claim_powered_pass(self):
        self.attempt("protected_star_N19")
        with self.assertRaisesRegex(ValueError, "derived blocked"):
            self.evaluate()

    def test_all_cases_bind_exactly_to_three_boards_and_fault_rails(self):
        self.assertEqual(set(self.plan["boards"]), {"adc", "psu", "disconnect"})
        fault = next(c for c in self.plan["cases"] if c["id"] == "disconnect_faults")
        self.assertEqual(len([c for c in fault["conditions"] if c.endswith("_OV")]), 6)
        self.assertTrue(all(b["holds"] for b in self.plan["boards"].values()))
        self.assertTrue(self.plan["boards"]["psu"]["native_connectivity_closed"])
        self.assertFalse(self.plan["boards"]["disconnect"]["native_connectivity_closed"])

    def test_native_pass_without_source_binding_is_not_a_current_check(self):
        board = self.plan["boards"]["psu"]
        from hardware.qualification.spec import REPO

        status, _ = native_source_check(REPO, {"source_sha256": {}}, "", board["pcb"])
        self.assertFalse(status["current"])

    def test_native_record_for_different_pcb_bytes_is_rejected(self):
        from hardware.qualification.spec import REPO

        board = self.plan["boards"]["psu"]
        status, _ = native_source_check(REPO, {"source_sha256": {board["pcb"]: "0" * 64}}, "", board["pcb"])
        self.assertFalse(status["current"])
        self.assertFalse(status["pcb_source_bound"])


if __name__ == "__main__":
    unittest.main()
