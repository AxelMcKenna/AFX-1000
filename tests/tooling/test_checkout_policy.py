"""Relocation must preserve sealed bytes and strict receiving comparisons."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hardware.qualification.boards.nf_passive_selection_checkout import verify
from hardware.qualification.boards.nf_passive_selection_portable import policy


class CheckoutLocations(unittest.TestCase):
    def test_location_changes_compare_equal_but_geometry_and_hash_changes_do_not(self):
        mac = {"source_sha256":{"/Users/old/dev/rmx-publish/hardware/board.kicad_pcb":"a"*64},"height_mm":1.5}
        linux = {"source_sha256":{"/home/runner/work/AFX-1000/AFX-1000/hardware/board.kicad_pcb":"a"*64},"height_mm":1.5}
        self.assertEqual(policy.compare(verify.canonical_locations(mac),verify.canonical_locations(linux))[0],[])
        for field in ("height_mm","source_sha256"):
            changed = copy.deepcopy(linux)
            if field == "height_mm":
                changed[field] = 1.50000001
            else:
                key = next(iter(changed[field]))
                changed[field][key] = "b"*64
            self.assertTrue(policy.compare(verify.canonical_locations(mac),verify.canonical_locations(changed))[0])

    def test_external_input_hash_and_missing_file_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"drawing.pdf"
            path.write_bytes(b"exact captured drawing")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(verify.checked_file(str(path),digest))
            self.assertFalse(verify.checked_file(str(path),"0"*64))
            path.unlink()
            self.assertFalse(verify.checked_file(str(path),digest))

    def test_unrecognized_saved_evidence_error_is_retained(self):
        with mock.patch.object(verify,"saved_errors",return_value=["Changed actual native pad"]):
            result = verify.check()
        self.assertTrue(any(e["reason"] == "Changed actual native pad" for e in result["errors"]))

    def test_all_original_successor_seal_files_remain_exact(self):
        root = Path(verify.capture_runtime.__file__).parent
        data = json.loads((root/"handoff.json").read_text())
        for name,digest in data["files_sha256"].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest,name)


if __name__ == "__main__":
    unittest.main()
