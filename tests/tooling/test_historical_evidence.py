"""Historical captures cannot silently approve changed native inputs."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.cad.a12 import historical


class HistoricalEvidence(unittest.TestCase):
    def test_real_incomplete_capture_remains_explicit(self):
        index = json.loads(historical.INDEX.read_text())
        missing = [e for e in index["entries"] if e["status"] == "historical_capture_missing"]
        self.assertEqual({e["original_path"] for e in missing}, {
            "hardware/cad/a12/thermal/README.md",
            "hardware/electronics/power_distribution/p03/generated/placement.json",
        })
        self.assertFalse(index["all_historical_inputs_reconstructible"])
        self.assertFalse(index["applies_to_current_board_inputs"])
        for entry in index["entries"]:
            if entry["status"] == "exact_captured_bytes":
                self.assertEqual(historical.sha(historical.REPO / entry["captured_path"]), entry["expected_sha256"])

    def test_altered_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = Path(directory) / "source"
            captured.write_bytes(b"actual historical native input")
            expected = hashlib.sha256(captured.read_bytes()).hexdigest()
            name = "tests/tooling/test_historical_evidence.py"
            index = Path(directory) / "index.json"
            index.write_text(json.dumps({"entries": [{
                "original_path": name, "expected_sha256": expected,
                "captured_path": str(captured), "status": "exact_captured_bytes",
            }]}))
            with patch.object(historical, "INDEX", index):
                result = historical.inspect_hashes({name: expected})
                self.assertTrue(result["historical_capture_complete"])
                self.assertFalse(result["applies_to_current_inputs"])
                self.assertFalse(result["fabrication_released"])
                captured.write_bytes(b"changed bytes")
                with self.assertRaisesRegex(AssertionError, "Changed captured evidence"):
                    historical.resolve(name, expected)

    def test_unrecognized_stale_input_fails_instead_of_becoming_history(self):
        with self.assertRaisesRegex(AssertionError, "Unrecognized stale/missing"):
            historical.inspect_hashes({"tests/tooling/test_historical_evidence.py": "0" * 64})

    def test_missing_record_cannot_be_used_as_reconstructed_input(self):
        index = json.loads(historical.INDEX.read_text())
        entry = next(e for e in index["entries"] if e["status"] == "historical_capture_missing")
        with self.assertRaisesRegex(AssertionError, "cannot be reconstructed"):
            historical.resolve(entry["original_path"], entry["expected_sha256"])
