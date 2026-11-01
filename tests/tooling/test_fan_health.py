"""Portable fan-monitor regression and conditional thermal-budget checks."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a12.thermal.airflow_operating_point.test_budget import OperatingPoint
from hardware.qualification.boards.fan_health.temperature import code, compute

REPO = Path(__file__).resolve().parents[2]
FH = REPO / "hardware/qualification/boards/fan_health"


class FanHealth(unittest.TestCase):
    def test_portable_fault_monitor(self):
        compiler = shutil.which("clang") or shutil.which("cc")
        if compiler is None:
            self.skipTest("A C compiler is required to execute the portable monitor")
        with tempfile.TemporaryDirectory(prefix="afx-fan-health-") as directory:
            binary = str(Path(directory) / "test_health")
            result = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 str(FH / "firmware/health.c"), str(FH / "firmware/test_health.c"),
                 "-o", binary], text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([binary], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertRegex(result.stdout, r"FH01 software engine: \d+ assertions passed")

    def test_sensor_faults_and_plausible_cold_remain_distinguishable(self):
        result = compute()
        self.assertTrue(result["short_and_open_detected_under_comparison"])
        self.assertLess(result["cold_minus10_code_upper"], result["firmware_open_code"])
        self.assertGreater(code(25), result["firmware_hot_code"])
        self.assertLess(code(70), result["firmware_hot_code"])

    def test_beta_model_does_not_invent_temperature_guarantee(self):
        result = compute()
        self.assertIsNone(result["guaranteed_hot_trip_interval_c"])
        self.assertFalse(result["actual_sensor_location_and_lag_qualified"])
        self.assertFalse(result["beta_approximation_discrepancy_bounded"])
        self.assertFalse(result["fabrication_released"])
        saved = json.loads((FH / "generated/temperature-comparison.json").read_text())
        self.assertEqual(result.keys(), saved.keys())
        for key, value in result.items():
            if isinstance(value, float):
                self.assertAlmostEqual(value, saved[key], places=9, msg=key)
            elif key == "modeled_trip_interval_c":
                for actual, expected in zip(value, saved[key], strict=True):
                    self.assertAlmostEqual(actual, expected, places=9, msg=key)
            else:
                self.assertEqual(value, saved[key], key)


def load_tests(loader, tests, pattern):
    # Reuse the actual branch/conservation regression suite in normal CI.
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(FanHealth),
        loader.loadTestsFromTestCase(OperatingPoint),
    ])
