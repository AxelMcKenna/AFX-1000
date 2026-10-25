"""Mechanical inventory and mounting-layout regressions; no CAD backend needed."""

import json
import math
import re
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware/cad/a08"))
from build import inventory  # noqa: E402
from generate import panel_layout, schedule  # noqa: E402


class MechanicalInventory(unittest.TestCase):
    def test_every_control_has_the_required_printed_parts(self):
        buttons, knobs = schedule()
        parts = inventory()
        self.assertEqual(len(buttons), 29)
        self.assertEqual(len(knobs), 10)
        self.assertEqual(
            {p["name"] for p in parts if p["part"] == "button"},
            {"button-" + b[0] for b in buttons},
        )
        for part, count in [
            ("button", 29),
            ("holder", 29),
            ("clip", 29),
            ("knob", 10),
            ("selector_cap", 2),
        ]:
            self.assertEqual(
                sum(p["quantity"] for p in parts if p["part"] == part), count
            )
        self.assertEqual(len({p["name"] for p in parts}), len(parts))

    def test_fasteners_have_separate_seats_and_clear_bank_light_pipes(self):
        buttons, _ = schedule()
        centers = []
        for button in buttons:
            angle = math.radians(button[7])
            for x, y in button[8]:
                point = (
                    button[5] + x * math.cos(angle) - y * math.sin(angle),
                    button[6] + x * math.sin(angle) + y * math.cos(angle),
                )
                for previous in centers:
                    self.assertGreater(math.dist(previous, point), 5.0)
                for led_x in [82, 101, 120, 139]:
                    self.assertGreater(math.dist(point, (led_x, 103)), 3.6)
                centers.append(point)
        self.assertEqual(len(centers), 58)

    def test_sector_fixings_clear_the_opening_and_cap(self):
        buttons, _ = schedule()
        for button in buttons:
            if button[1] != "sector":
                continue
            inner = 43.5 + button[8][0][0]
            outer = 43.5 + button[8][1][0]
            self.assertLess(inner + 2.3 + 0.3, 35)
            self.assertGreater(outer - 2.3 - 0.3, 52)

    def test_panel_cutouts_follow_the_control_source(self):
        generated = ROOT / "hardware/cad/a08/generated/layout.scad"
        actual = {}
        for line in generated.read_text().splitlines():
            match = re.fullmatch(r"(\w+) = (.*);", line)
            if match:
                actual[match[1]] = json.loads(match[2])
        self.assertEqual(panel_layout(), actual)

    def test_generated_schedule_matches_source_layout(self):
        buttons, knobs = schedule()
        saved = json.loads(
            (ROOT / "hardware/cad/a08/generated/control-schedule.json").read_text()
        )
        self.assertEqual(saved["buttons"], buttons)
        self.assertEqual(saved["knobs"], knobs)


if __name__ == "__main__":
    unittest.main()
