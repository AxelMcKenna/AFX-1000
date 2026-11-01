"""Relocate checkout paths without rewriting evidence or external inputs."""

import unittest
from pathlib import Path

from hardware.fabrication.evidence_paths import REPO, recorded_path


class RecordedPaths(unittest.TestCase):
    def test_recorded_mac_checkout_relocates_into_current_checkout(self):
        name = "/Users/previous-owner/dev/rmx-publish/hardware/fabrication/scope.json"
        self.assertEqual(recorded_path(name),REPO/"hardware/fabrication/scope.json")

    def test_github_checkout_and_relative_paths_locate_the_same_file(self):
        relative = "hardware/fabrication/scope.json"
        self.assertEqual(recorded_path("/home/runner/work/AFX-1000/AFX-1000/"+relative),REPO/relative)
        self.assertEqual(recorded_path(relative),REPO/relative)

    def test_external_inputs_are_not_silently_replaced_by_repository_files(self):
        name = "/private/tmp/manufacturer-drawing.pdf"
        self.assertEqual(recorded_path(name),Path(name))

    def test_parent_escape_is_rejected(self):
        for name in ("../../outside.pdf","/Users/previous-owner/dev/rmx-publish/../../outside.pdf"):
            with self.subTest(name=name),self.assertRaises(ValueError):
                recorded_path(name)


if __name__ == "__main__":
    unittest.main()
