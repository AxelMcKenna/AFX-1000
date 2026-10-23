"""Archived review bundles must remain recoverable without overwriting local work."""

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.artifacts.restore import artifact_path, restore_artifact

ROOT = Path(__file__).resolve().parents[2]


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = subprocess.check_output(["git", "rev-parse", "HEAD:README.md"], cwd=ROOT, text=True).strip()
        cls.original = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=ROOT)
        cls.artifact = {
            "name": "test-review.bin",
            "local_path": "build/artifacts/releases/test-review.bin",
            "bytes": len(cls.original),
            "sha256": hashlib.sha256(cls.original).hexdigest(),
            "git_blob": blob,
        }

    def test_restore_missing_artifact_from_git(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            path = restore_artifact(ROOT, self.artifact, output)
            self.assertEqual(path.read_bytes(), self.original)
            self.assertEqual(restore_artifact(ROOT, self.artifact, output), path)
            self.assertEqual(list(output.iterdir()), [path])

    def test_mismatching_local_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            path = output / self.artifact["name"]
            path.write_bytes(b"local work")
            with self.assertRaisesRegex(ValueError, "existing file preserved"):
                restore_artifact(ROOT, self.artifact, output)
            self.assertEqual(path.read_bytes(), b"local work")

    def test_local_only_artifact_does_not_create_a_placeholder(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            with self.assertRaisesRegex(ValueError, "Local-only"):
                restore_artifact(ROOT, dict(self.artifact, git_blob=None), output)
            self.assertEqual(list(output.iterdir()), [])

    def test_manifest_cannot_escape_the_artifact_directory(self):
        with self.assertRaises(ValueError):
            artifact_path(ROOT, dict(self.artifact, local_path="../review.zip"))
