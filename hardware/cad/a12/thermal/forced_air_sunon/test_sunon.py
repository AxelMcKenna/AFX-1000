"""Source-curve, allocation and adverse sensitivity checks for SF01."""

import json
import unittest
from pathlib import Path

from hardware.cad.a12.thermal.forced_air_sunon.analyze import PARTS, extract_curve, pressure, sha

ROOT = Path(__file__).resolve().parent


class SunonBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "analysis.json").read_text())

    def test_exact_primary_sources(self):
        for part in PARTS.values():
            self.assertEqual(sha(Path(part["pdf"])), part["expected_pdf_sha256"])

    def test_curve_replay(self):
        for name, part in PARTS.items():
            points = extract_curve(ROOT / "generated" / (name + "-curve.svg"), part)
            self.assertEqual(points, self.data["parts"][name]["curve_points_cfm_inH2O"])

    def test_independent_curve_endpoints(self):
        for name, part in self.data["parts"].items():
            curve = part["curve_points_cfm_inH2O"]
            expected = (8, 0.19) if name == "V1" else (7, 0.12)
            self.assertEqual(curve[0], [0, expected[1]])
            self.assertEqual(curve[-1], [expected[0], 0])

    def test_shutoff_affinity_scales_pressure_squared(self):
        for part in self.data["parts"].values():
            curve = part["curve_points_cfm_inH2O"]
            self.assertAlmostEqual(pressure(curve, 0, 0.8) / pressure(curve, 0), 0.8**2)

    def test_no_free_air_extrapolation(self):
        for part in self.data["parts"].values():
            self.assertIsNone(pressure(part["curve_points_cfm_inH2O"], 40))

    def test_selected_motor_reserve_retains_control_allocation(self):
        p = self.data["parts"]["V1"]
        self.assertAlmostEqual(p["two_fan_twenty_percent_current_provision_a"], 0.3768)
        self.assertAlmostEqual(p["remaining_digital_reserve_a"], 0.0392)
        self.assertGreater(p["remaining_digital_reserve_a"], 0.006)
        self.assertLess(p["known_plus_fans_a"], 2.4)

    def test_selected_speed_retains_channel_budget_in_adverse_sensitivity(self):
        rows = [r for r in self.data["parts"]["V1"]["pressure_cases"] if r["guard_area_each_mm2"] == 800]
        self.assertEqual(len(rows), 9)
        self.assertGreater(min(r["remaining_channel_pressure_sensitivity_pa"] for r in rows), 5)
        slower = [r for r in self.data["parts"]["V2"]["pressure_cases"] if r["guard_area_each_mm2"] == 800]
        self.assertLess(min(r["remaining_channel_pressure_sensitivity_pa"] for r in slower), 0.1)

    def test_no_physical_acceptance(self):
        for key in [
            "physical_qualified",
            "installed_flow_verified",
            "installed_noise_verified",
            "fabrication_released",
        ]:
            self.assertIs(self.data[key], False)


if __name__ == "__main__":
    unittest.main()
