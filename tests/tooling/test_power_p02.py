"""Focused P02 native, actual endpoint, robust ground and operating regression."""

import copy
import json
import random
import unittest
from unittest.mock import patch

from hardware.electronics.common.netlists import netlist
from hardware.electronics.power_distribution.p02.analysis import analyze, legacy_domains, source_corners
from hardware.electronics.power_distribution.p02.check import contract
from hardware.electronics.power_distribution.p02.distribution import (
    GROUND,
    LOADS,
    ground_edges,
    inverse_ground,
    transfer_bounds,
    voltage_bounds,
)
from hardware.electronics.power_distribution.p02.loads import endpoint_contract
from hardware.electronics.power_distribution.p02.spec import ROOT


class P02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze()
        cls.parts, cls.pins = netlist(ROOT / "generated/netlist.xml")
        cls.sources, _ = source_corners(cls.parts)

    def test_native_manufacturer_pin_contract_rejects_control_miswire(self):
        contract(self.parts, self.pins)
        bad = copy.deepcopy(self.pins)
        bad["U2"]["4"] = "P02_PRE6V"
        with self.assertRaises(AssertionError):
            contract(self.parts, bad)

    def test_native_passive_contract_rejects_wrong_analog_gain(self):
        bad = copy.deepcopy(self.parts)
        bad["R12"].find("value").text = "150 0.01% 5ppm"
        with self.assertRaises(AssertionError):
            contract(bad, self.pins)

    def test_every_actual_power_endpoint_and_gain_return_checked(self):
        proof = endpoint_contract()
        self.assertEqual(proof["interboard_5v_positive_wires"], 9)
        self.assertEqual(len(self.report["source_to_load"]["endpoints"]), 13)
        self.assertTrue(proof["gain_returns_are_gain_low"])
        self.assertAlmostEqual(sum(i for r, _, i in LOADS.values() if r == "DIG"), 2.4)
        self.assertAlmostEqual(sum(i for r, _, i in LOADS.values() if r == "ANA"), 0.251)
        self.assertTrue(all(row["passes"] for row in self.report["source_to_load"]["endpoints"].values()))

    def test_missing_straps_exposes_the_original_full_distribution_gap(self):
        edges = [e for e in ground_edges() if "STRAP" not in e[3]]
        with patch(
            "hardware.electronics.power_distribution.p02.distribution.ground_edges", return_value=edges
        ):
            screen = voltage_bounds(self.sources)
        self.assertFalse(screen["all_pass"])
        self.assertFalse(screen["endpoints"]["adc_5v"]["passes"])

    def test_contact_degradation_is_not_zeroed_or_hidden(self):
        degraded = voltage_bounds(self.sources, contact_max=0.010)
        self.assertFalse(degraded["all_pass"])
        self.assertLess(degraded["endpoints"]["led_5v"]["minimum_v"], 4.9)

    def test_transfer_bound_handles_mixed_corners_not_just_all_hot(self):
        edges = [(GROUND, "a", 1, "a"), (GROUND, "b", 1, "b"), ("a", "b", 1, "bridge")]
        _, bounds = transfer_bounds(edges)
        nodes, all_hot = inverse_ground(edges, 1)
        mixed = edges[:2] + [("a", "b", 0.000001, "bridge")]
        _, z = inverse_ground(mixed, 1)
        i, j = nodes.index("a"), nodes.index("b")
        self.assertGreater(z[i][j], all_hot[i][j])
        self.assertLessEqual(z[i][j], bounds["a", "b"][1])

    def test_ground_interval_encloses_independent_random_resistances(self):
        edges = ground_edges()
        _, bounds = transfer_bounds(edges)
        rng = random.Random(20261025)
        for _ in range(24):
            mixed = [(a, b, r * rng.uniform(0.0001, 1), h) for a, b, r, h in edges]
            nodes, z = inverse_ground(mixed, 1)
            for i, a in enumerate(nodes):
                for j, b in enumerate(nodes):
                    lo, hi = bounds[a, b]
                    self.assertGreaterEqual(z[i][j], lo - 1e-12)
                    self.assertLessEqual(z[i][j], hi + 1e-12)

    def test_raw_generators_remain_in_the_native_12v_domain(self):
        domains = legacy_domains()
        self.assertEqual(domains["raw_converter_vin_net"], "VIN_PROTECTED")
        limits = self.report["operating_limits"]
        self.assertGreater(limits["digital_regulator_total_a"], 2.4)
        self.assertLess(limits["digital_regulator_total_a"], 3)
        self.assertGreater(limits["upstream"]["raw_generators_input_w"], 12)
        self.assertGreater(limits["upstream"]["input_current_at_10v5_a"], 3)
        self.assertFalse(limits["upstream"]["existing_input_path_passes"])

    def test_actual_seed_series_filter_and_minimum_load_are_budgeted(self):
        limits = self.report["operating_limits"]
        seed = limits["seed_filter"]
        self.assertAlmostEqual(seed["worst_heat_w"], 0.4747)
        self.assertGreater(seed["minimum_module_vin_v"], 4)
        self.assertFalse(seed["thermal_derating_qualified"])
        self.assertGreater(limits["minimum_load"]["digital_min_a"], 0.005)
        self.assertGreater(limits["thermal"]["digital_pass_plus_control_max_w"], 3)
        self.assertTrue(all(v > 0 for v in limits["dropout"].values()))

    def test_preconnected_ramp_does_not_claim_late_gate_closure(self):
        startup = self.report["operating_limits"]["startup"]
        self.assertTrue(startup["preconnected_ramp_current_screen_passes"])
        self.assertGreater(startup["digital_late_closure_stored_energy_j"], 0.08)
        self.assertFalse(startup["late_e26_gate_closure_current_limited"])
        self.assertFalse(startup["measured_startup_stability"])
        self.assertFalse(startup["initial_set_floor_inrush_qualified"])
        self.assertGreater(startup["initial_set_floor_digital_cap_current_demand_a"], 4)

    def test_native_erc_is_zero_and_release_flags_stay_false(self):
        erc = json.loads((ROOT / "generated/erc.json").read_text())
        self.assertFalse([v for sheet in erc["sheets"] for v in sheet.get("violations", [])])
        for key in (
            "stability_qualified",
            "startup_qualified",
            "thermal_qualified",
            "actual_harness_qualified",
            "physical_power_verified",
            "complete_unit_qualified",
            "fabrication_released",
            "build_ready",
        ):
            self.assertFalse(self.report[key], key)


if __name__ == "__main__":
    unittest.main()
