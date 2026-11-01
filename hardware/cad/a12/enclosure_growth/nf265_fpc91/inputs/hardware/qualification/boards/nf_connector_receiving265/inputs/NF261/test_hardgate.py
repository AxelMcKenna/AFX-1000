import copy
import json
import unittest

from hardware.electronics.common.netlists import netlist

from .analyze import ROOT, analyze, off_discharge, sha, thresholds
from .review import main, physical_TPS3890, validate


class AbsoluteAUXGate(unittest.TestCase):
    def test_native_manufacturer_land_fixture_and_rejected_control(self):
        p = ROOT / "generated/package-fixture"
        r = json.loads((p / "verification.json").read_text())
        self.assertFalse(r["results"]["manufacturer"]["violations"])
        self.assertFalse(r["results"]["manufacturer"]["unconnected_items"])
        self.assertTrue(
            any(v["type"] == "clearance" for v in r["results"]["enlarged_DCU_pad_rejected"]["violations"])
        )
        for name, digest in r["source_sha256"].items():
            self.assertEqual(sha(ROOT / name), digest, name)
        self.assertFalse(r["actual_NF05_board_implemented"])

    def test_actual_primary_pin_maps_not_only_builder_parity(self):
        r = main()
        self.assertEqual(r["physical_TPS3890_count"], 7)
        self.assertEqual({e["ref"] for e in r["old249_swapped_START_timer_rejected"]}, {"U52", "U54"})
        # All four inherited floating monitors were already correct.
        self.assertEqual(physical_TPS3890(ROOT / "sources/sequence249/generated/netlist.xml")[0], 6)

    def test_gate_power_cannot_be_AUX(self):
        _, p = netlist(ROOT / "generated/netlist.xml")
        p["U56"]["4"] = "AUX2V6"
        self.assertTrue(validate(p))

    def test_LED_energy_bypass_mutation(self):
        _, p = netlist(ROOT / "generated/netlist.xml")
        p["R11"]["1"] = "DIG5_FORCE"
        self.assertTrue(validate(p))

    def test_driver_not_5V_logic_level_mismatch(self):
        a = analyze()["LED"]
        self.assertLess(a["new_AUP_VOH_20uA_row_lower_v"], a["old_RAW5_VIH_requirement_v"][0])
        self.assertGreaterEqual(a["new_AUP_VOH_20uA_row_lower_v"], 1.2 * a["new_LVC_VIH_primary_v"])
        self.assertLessEqual(a["full_sink_current_upper_a"], 0.008)
        self.assertLessEqual(a["AUP_20pct_loaded_current_a"], a["AUP_primary_continuous_current_row_a"])
        self.assertLess(a["powered_off_connected_default_LOW20pct_v"], 0.7)
        self.assertTrue(a["trigger_has20pct_conditionally"])
        _, p = netlist(ROOT / "generated/netlist.xml")
        p["U4"]["5"] = "DIG5_FORCE"
        self.assertTrue(validate(p))

    def test_UV_adverse_reference_resistor_bias_hysteresis(self):
        a = analyze()
        self.assertGreater(a["absolute_UV"]["falling_trip_v"][0], 2.4)
        self.assertLess(a["absolute_UV"]["rising_release_v"][1], 2.52)
        r = copy.deepcopy(a["native_resistor_values_ohm"])
        r["R92"] *= 0.94
        self.assertLess(thresholds(r)["falling_trip_v"][0], 2.4)

    def test_discharge_includes_cathode_backfeed_and_nonrail_caps(self):
        a = analyze()
        h = a["hardoff"]
        self.assertGreaterEqual(h["components_a"]["two_powered_OD_positive_leaks"], 10e-6)
        self.assertGreater(h["worst_charge_path_upper_ohm"], 10000)
        self.assertLess(h["guarded_steady_string_current_a"], h["relay_return_current_minimum_receiving_a"])
        bad = off_discharge(a["native_resistor_values_ohm"], 1000)
        self.assertIsNone(bad["RC_path_decay_diagnostic_s"])
        self.assertGreater(bad["guarded_steady_string_current_a"], 10e-6)
        self.assertFalse(h["powered_OD_leak_guaranteed_by_Ioff"])

    def test_loaded_gate_clamp_no_threshold_voltage_OFF_substitution(self):
        h = analyze()["hardoff"]
        self.assertLess(h["clamped_VGS_equilibrium_given_requirements_v"], h["clamp_target_VGS_v"])
        self.assertGreater(h["gate_discharge_time_conditional_s"], 0)
        self.assertFalse(h["MOSFET_drain_OFF_current_at_target_VGS_accepted"])
        self.assertFalse(h["clamp_load_SOAfault_max_current_and_energy_accepted"])

    def test_module_return_is_separate_real_port(self):
        _, p = netlist(ROOT / "generated/netlist.xml")
        p["C4"]["2"] = "AGND"
        self.assertTrue(validate(p))
        self.assertIsNone(analyze()["primary_return"]["full_hot_capacitance_and_input_inrush_bound_a"])

    def test_complete_current_partitions_and_heat_delta(self):
        a = analyze()["power"]
        self.assertLess(a["full_known_guarded_partition_a"], 2.44)
        self.assertGreater(a["full_known_guarded_partition_a"], 2.42)
        self.assertLess(a["new_AUX_normal20pct_a"], a["AUX_normal_receiving_proposal_a"])
        self.assertLess(a["new_AUX_fault20pct_a"], a["AUX_fault_receiving_proposal_a"])
        self.assertLess(
            1.2 * a["actual_feedback_network_DC_screen_a"], a["opamp_feedback_output_DC_receiving_a"]
        )
        self.assertAlmostEqual(a["additional20mA_source_power_screen_w"], 0.020 * 5.1 / 0.85)
        self.assertLess(a["bleed_power_with20pct_w"], a["conditional_linear_85C_derated_rating_w"])
        self.assertFalse(a["fault_standby_ledger_complete"])

    def test_receipts_all_bound(self):
        for name, digest in json.loads((ROOT / "sources/manifest.json").read_text()).items():
            self.assertEqual(sha(ROOT / "sources" / name), digest, name)
        a = json.loads((ROOT / "generated/native-review.json").read_text())
        for group in ["source_sha256", "artifact_sha256"]:
            for name, digest in a[group].items():
                self.assertEqual(sha(ROOT / name), digest, name)

    def test_undefined_power_regions_and_no_accidental_pass(self):
        a = analyze()
        self.assertFalse(a["partial_power_qualified"])
        self.assertFalse(a["startup_qualified"])
        self.assertFalse(a["physical_qualified"])
        self.assertFalse(a["release_approved"])
        self.assertEqual(len(a["source_states"]), 4)
        self.assertTrue(all(not x["qualified"] for x in a["source_states"]))
        self.assertIn("AUX_OV_hardgate_not_implemented", a["holds"])


if __name__ == "__main__":
    unittest.main()
