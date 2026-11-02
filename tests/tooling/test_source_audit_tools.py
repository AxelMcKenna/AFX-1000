"""Portable evidence reads retain hashes, inventory coverage and UUID checks."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.fabrication.source_audit_tools import verified_removed_objects


class PortableRemovalEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "hardware/fabrication/input.kicad_pcb"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"immutable native input\n")
        self.node = ["segment", ["uuid", "original-copper"], ["net", "OLD_NET"]]
        self.record = dict(source_sha256={"/Users/previous-owner/dev/rmx-publish/hardware/fabrication/input.kicad_pcb":
                           hashlib.sha256(self.source.read_bytes()).hexdigest()}, removed_objects=[self.node])
        self.receipt = self.root / "construction.json"

    def check(self, count=1):
        self.receipt.write_text(json.dumps(self.record))
        with patch("hardware.fabrication.evidence_paths.REPO", self.root):
            return verified_removed_objects([self.receipt], count)

    def test_relocated_checkout_keeps_original_path_and_digest(self):
        rows, paths = self.check()
        self.assertEqual(rows, [self.node])
        self.assertEqual(paths, [self.receipt])
        self.assertIn("/Users/previous-owner/", self.receipt.read_text())

    def test_relocation_does_not_accept_changed_input_bytes(self):
        self.source.write_bytes(b"changed input\n")
        with self.assertRaisesRegex(AssertionError, "Changed recorded removal dependency"):
            self.check()

    def test_missing_inventory_entry_is_rejected(self):
        self.record["removed_objects"] = []
        with self.assertRaises(AssertionError):
            self.check()

    def test_duplicate_removed_copper_is_rejected(self):
        self.record["removed_objects"].append(self.node)
        with self.assertRaisesRegex(AssertionError, "Duplicate removal UUID"):
            self.check(2)


if __name__ == "__main__":
    unittest.main()
