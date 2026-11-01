"""AX02 native roles, ownership and refusal to turn typical rows into bounds."""

import json
import re
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist

from .analyze import analyze

ROOT = Path(__file__).resolve().parent


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = analyze()

    def test_actual_native_pinout_and_controller_roles(self):
        parts, p = netlist(ROOT / "generated/netlist.xml")
        self.assertEqual(len(parts), 10)
        self.assertEqual(parts["U2"].findtext("value"), "TPS22913CYZVR")
        self.assertEqual(p["U2"], self.a["native_switch_pin_contract"])
        self.assertEqual(p["U1"]["4"], "AUX")
        self.assertEqual(p["U1"]["6"], "RUN_GATE_COMMAND")
        self.assertEqual(p["R1"], {"1": "AUX", "2": "RUN_GATE_COMMAND"})
        self.assertEqual(p["R2"], {"1": "RUN_GATE_COMMAND", "2": "AGND"})
        self.assertEqual(p["R4"], {"1": "SWITCHED_AUX", "2": "POWER_RUN_E28_LEAF"})

    def test_no_discrete_bootstrap_or_new_regulator(self):
        parts, _ = netlist(ROOT / "generated/netlist.xml")
        self.assertFalse(any(x.startswith(("Q", "D")) for x in parts))
        self.assertTrue(self.a["discrete_common_source_bootstrap_eliminated"])
        self.assertTrue(self.a["no_extra_regulator_or_RAW5_supply_required"])
        self.assertEqual(self.a["original_internal_R113_preserved_ohm"], 3300)
        self.assertLess(self.a["original_PG1mA_sink_comparison_a"], 0.001)

    def test_independent_enable_levels_POR_loading(self):
        a = self.a
        self.assertGreater(a["ON_HIGH_receiving_v"], a["ON_HIGH_target1p2_v"])
        self.assertLess(a["ON_LOW_times1p2_v"], a["ON_LOW_primary_VIL_max_v"])
        self.assertLess(a["POR_pull_current_times1p2_a"], a["POR_test_max_a"])
        self.assertLess(a["RESET_LOW_sink_requirement_a"], a["RESET_primary_atVDDge1p5_sink_a"])
        self.assertGreater(a["normal_HIGH_receiving_v"], 2.4)
        self.assertLess(a["output_OFF_times1p2_v"], 0.4)

    def test_receiving_extra_nonrail_current_not_omitted(self):
        self.assertEqual(self.a["extra_nonrail_and_switching_current_receiving_a"], 0.001)
        self.assertFalse(self.a["extra_nonrail_and_switching_current_guaranteed"])
        self.assertGreater(self.a["normal_new_leaf_total_guarded_a"], 0.0012)

    def test_fixed_pool_full_NF_reserves_and_failed_transients(self):
        a = self.a
        self.assertEqual(a["existing_AUX_planning_pool_a"], 0.09)
        self.assertTrue(a["no_source_pool_increase"])
        for x in a["pool_scenarios"][:3]:
            self.assertLess(x["source_total_receiving_a"], 0.09)
        for x in a["pool_scenarios"][3:]:
            self.assertFalse(x["numerical_receiving_screen_inside90mA"])
        for x in a["pool_scenarios"]:
            self.assertIn(x["NF_guarded_allocation_a"], [0.011, 0.014])
            self.assertAlmostEqual(
                x["source_total_receiving_a"],
                x["unique_source_subtotal_a"] + x["preserved_NF_full_reserve_headroom_a"],
            )

    def test_typical_reverse_and_timing_not_promoted(self):
        a = self.a
        self.assertIsNone(a["primary_VRCP_max_v"])
        self.assertIsNone(a["primary_reverse_response_max_s"])
        self.assertIsNone(a["primary_reverse_afterevent_leak_max_a"])
        self.assertIsNone(a["full_loaded_cutoff_upper_s"])
        self.assertFalse(a["below1p4V_all_state_OFF_leak_qualified"])
        self.assertFalse(a["partial_power_qualified"])
        self.assertFalse(a["TPS22916_comparison_REJECTED"]["guaranteed_trip_upper_a"])

    def test_cap_inventory_has_no_peak_current_claim(self):
        c = self.a["input_cap"]
        self.assertEqual(c["required_effective_min_f"], 1e-6)
        self.assertGreater(c["initial_and_positive_temperature_input_max_partial_inventory_f"], 10e-6)
        self.assertGreater(c["ramp2p7_average_duration_only_diagnostic_s"], 0.008)
        self.assertFalse(c["actual_effective_bound_qualified"])
        self.assertTrue(c["diagnostic_is_NOT_full_AUXcap_or_peak_current_bound"])

    def test_actual_assigned_package_balls_and_receiving_dimensions(self):
        fp = (ROOT / "RMX_AX02.pretty/YZV_4_Receiving.kicad_mod").read_text()
        self.assertEqual(set(re.findall(r'\(pad "([^\"]+)"', fp)), {"A1", "A2", "B1", "B2"})
        self.assertEqual(fp.count("(size .23 .23)"), 4)
        self.assertFalse(self.a["package"]["C50_fabricator_and_assembly_pitch_process_approved"])
        self.assertTrue(self.a["package"]["land_pattern_is_receiving_not_manufacturer_approval"])

    def test_native_reports_really_clean(self):
        n = json.loads((ROOT / "generated/native.json").read_text())
        self.assertFalse(n["erc_findings"])
        self.assertFalse(n["pin_value_mismatches"])
        self.assertTrue(all(x["returncode"] == 0 for x in n["native_commands"]))
        self.assertFalse(n["original_PCB_edited"])


if __name__ == "__main__":
    unittest.main()
