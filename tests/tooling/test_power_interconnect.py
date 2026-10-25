"""Source/disconnect pin contracts and deliberately unreleased harness trials."""

import copy
import json
import unittest

from hardware.wiring.power import ELECTRONICS, plan, screen, validate


class PowerInterconnect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = plan()
        cls.rows = json.loads(
            (ELECTRONICS / "rail_disconnect/generated/electrical-screens.json").read_text()
        )["normal_drop"]

    def test_source_connectors_match_all_eleven_pins(self):
        validate(self.p["wires"])

    def test_missing_ground_is_rejected(self):
        p = copy.deepcopy(self.p["wires"])
        p.pop(1)
        with self.assertRaisesRegex(AssertionError, "Missing or duplicated"):
            validate(p)

    def test_protected_net_cannot_replace_source_net(self):
        p = copy.deepcopy(self.p["wires"])
        p[0]["to_net"] = "P19"
        with self.assertRaisesRegex(AssertionError, "net mismatch"):
            validate(p)

    def test_auxiliary_and_run_cannot_swap(self):
        p = copy.deepcopy(self.p["wires"])
        p[-1]["to_pin"] = 1
        with self.assertRaisesRegex(AssertionError, "pin order"):
            validate(p)

    def test_18awg_geometry_trial_is_not_marked_qualified(self):
        r = screen(self.p, self.rows)
        self.assertEqual([x["wire_only_trial_passes"] for x in r], [False, False])
        self.assertTrue(all(not x["production_distribution_qualified"] for x in r))
        self.assertTrue(
            all(w["cut_length_mm"] is None and not w["assembly_released"] for w in self.p["wires"])
        )

    def test_lost_source_margin_does_not_produce_a_positive_wire_allowance(self):
        rows = copy.deepcopy(self.rows)
        r = next(r for r in rows if r["name"] == "5V_DIG")
        r["protected_dc_with_digital_ripple_v"][0] = 4.89
        with self.assertRaisesRegex(AssertionError, "no remaining"):
            screen(self.p, rows)
