"""Cross-runtime NP01 policy regressions plus all unaffected legacy tests."""

import copy
import json
import math
import unittest
from pathlib import Path
from unittest import mock

from hardware.qualification.boards.nf_passive_selection import test_np01
from hardware.qualification.boards.nf_passive_selection_portable import capture_runtime, policy, verify

ROOT = Path(__file__).resolve().parent


def getpath(d, path):
    for key in path:
        d = d[key]
    return d


def setpath(d, path, value):
    parent = getpath(d, path[:-1])
    parent[path[-1]] = value


def next_steps(x, steps):
    for _ in range(steps):
        x = math.nextafter(x, math.inf)
    return x


class PortablePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = verify.reference()
        cls.path = ("selection", "rows", 24, "planning_error_scenarios", 0, "total_fraction")

    def test_all55_original_files_and_parent_seal_exact(self):
        self.assertEqual(len(capture_runtime.check_parent()["files_sha256"]), 55)
        self.assertEqual(
            capture_runtime.sha(capture_runtime.PARENT / "handoff.json"), capture_runtime.EXPECTED
        )

    def test_runtime_replay_obeys_bound(self):
        report = verify.check()
        self.assertEqual(report["errors"], [])
        self.assertTrue(
            all(max(p["ulp_distances"]) <= 4 for p in report["accepted_computed_sum_differences"])
        )
        self.assertFalse(report["physical_qualified"])

    def test_actual39_and312_saved_models_have_only23_oneULP_sums(self):
        payloads = []
        for version in ["python39", "python312"]:
            d = json.loads((ROOT / "diagnostics" / version / "runtime.json").read_text())
            self.assertEqual(d["parent_files_verified_before"], 55)
            self.assertEqual(d["parent_files_verified_after"], 55)
            payloads.append({key: d[key] for key in ["selection", "lifetime", "monitor", "power"]})
        errors, accepted = policy.compare(*payloads)
        self.assertEqual(errors, [])
        self.assertEqual(len(accepted), 23)
        self.assertTrue(all(max(p["ulp_distances"]) == 1 for p in accepted))
        self.assertLessEqual(max(x["absolute_difference"] for x in accepted), 7e-18)

    def test_legacy_failures_are_preserved_as_failures(self):
        a = (ROOT / "diagnostics/original-strict-python312.log").read_text()
        b = (ROOT / "diagnostics/original-strict-python39.log").read_text()
        self.assertIn("FAILED (failures=2)", a)
        self.assertIn("Saved additional life scenarios disagree with recalculation", a)
        self.assertIn("Ran 13 tests", b)
        self.assertIn("\nOK\n", b)

    def test_oneULP_total_with_exact_summands_allowed(self):
        changed = copy.deepcopy(self.reference)
        setpath(changed, self.path, next_steps(getpath(changed, self.path), 1))
        errors, accepted = policy.compare(self.reference, changed)
        self.assertEqual(errors, [])
        self.assertEqual(len(accepted), 1)

    def test_fiveULP_total_is_rejected(self):
        changed = copy.deepcopy(self.reference)
        setpath(changed, self.path, next_steps(getpath(changed, self.path), 5))
        errors, _ = policy.compare(self.reference, changed)
        self.assertTrue(any("four ULP" in e["reason"] for e in errors))

    def test_complete_error_material_change_is_rejected(self):
        changed = copy.deepcopy(self.reference)
        setpath(changed, self.path, getpath(changed, self.path) + 1e-8)
        self.assertTrue(policy.compare(self.reference, changed)[0])

    def test_sum_term_even_oneULP_must_match_exactly(self):
        changed = copy.deepcopy(self.reference)
        path = self.path[:-1] + ("terms", "initial")
        setpath(changed, path, next_steps(getpath(changed, path), 1))
        errors, _ = policy.compare(self.reference, changed)
        self.assertTrue(any(e["reason"] == "Summands changed" for e in errors))

    def test_geometry_and_hashes_remain_exact(self):
        for path in [
            ("selection", "rows", 0, "body_plus_seat_max_mm"),
            ("selection", "rows", 0, "body_max_mm", 0),
        ]:
            changed = copy.deepcopy(self.reference)
            setpath(changed, path, next_steps(getpath(changed, path), 1))
            self.assertTrue(
                any(e["reason"] == "Exact float mismatch" for e in policy.compare(self.reference, changed)[0])
            )
        changed = copy.deepcopy(self.reference)
        key = next(iter(changed["selection"]["primary_sha256"]))
        changed["selection"]["primary_sha256"][key] = "0" * 64
        self.assertTrue(policy.compare(self.reference, changed)[0])

    def test_flags_types_structure_and_nonfinite_are_exact(self):
        for path, value in [
            (("selection", "physical_qualified"), True),
            (("selection", "selected_passive_refs"), 196.0),
            (self.path, float("nan")),
            (self.path, float("inf")),
        ]:
            changed = copy.deepcopy(self.reference)
            setpath(changed, path, value)
            self.assertTrue(policy.compare(self.reference, changed)[0])
        changed = copy.deepcopy(self.reference)
        del changed["selection"]["rows"][3]
        self.assertTrue(policy.compare(self.reference, changed)[0])

    def test_correctly_rounded_reference_uses_five_terms_not_saved_total(self):
        before = getpath(self.reference, self.path[:-1])
        rounded = policy.exact_rounded_sum(before["terms"])
        self.assertLessEqual(policy.positive_ulp_steps(rounded, before["total_fraction"]), 4)
        with self.assertRaises(ValueError):
            policy.exact_rounded_sum({"a": 1.0})
        with self.assertRaises(ValueError):
            policy.positive_ulp_steps(-1.0, 1.0)

    def test_unknown_legacy_evidence_error_is_not_suppressed(self):
        with mock.patch.object(verify.old_verify, "saved_errors", return_value=["Changed actual native pad"]):
            result = verify.check()
        self.assertTrue(any(e["reason"] == "Changed actual native pad" for e in result["errors"]))


def load_tests(loader, tests, pattern):
    excluded = {
        "test_saved_input_native_and_seal_integrity",
        "test_replay_is_from_captured_inputs_and_refuses_overwrite",
    }
    for name in loader.getTestCaseNames(test_np01.PassiveSelection):
        if name not in excluded:
            tests.addTest(test_np01.PassiveSelection(name))
    return tests


if __name__ == "__main__":
    unittest.main()
