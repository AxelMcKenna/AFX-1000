"""Crash prevention tests; every subprocess launcher is mocked."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import run


class CrashGuard(unittest.TestCase):
    def test_native_signal_and_container_fatal_exit_stop(self):
        for code in [-6, -11, 125, 134, 137, 139]:
            self.assertTrue(run.fatal(code, ""))

    def test_known_empty_is_distinct_from_execution_failure(self):
        self.assertFalse(run.fatal(1, "Current top level object is empty."))
        self.assertTrue(run.fatal(1, "cannot load engine"))
        self.assertTrue(run.fatal(0, "ERROR: cannot parse input"))
        self.assertTrue(run.fatal(0, "WARNING: missing source"))
        self.assertTrue(run.fatal(0, "Incompatible processor"))

    def test_prior_failure_prevents_any_launch(self):
        with tempfile.TemporaryDirectory() as d:
            failed = Path(d) / "failed.json"
            failed.write_text("{}")
            with patch.object(run, "FAILED", failed), patch.object(run.subprocess, "run") as launch:
                with patch("sys.argv", ["runner", "probe"]), self.assertRaises(AssertionError):
                    run.main()
                launch.assert_not_called()

    def test_wrong_image_or_missing_restart_authorization_prevents_launch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            policy = root / "policy.json"
            for values in [dict(native_cad_launches_disabled=True, allowed_isolated_image="unapproved"),
                           dict(native_cad_launches_disabled=True, allowed_isolated_image=run.IMAGE,
                                isolated_Linux_restart_authorized_by_user=False)]:
                policy.write_text(json.dumps(values))
                with patch.object(run, "STOP", policy), patch.object(run, "FAILED", root / "absent"):
                    with patch.object(run.subprocess, "run") as launch:
                        with patch("sys.argv", ["runner", "probe"]), self.assertRaises(AssertionError):
                            run.main()
                        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
