import copy
import json
import unittest

import numpy as np

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr

from .analyze import ROOT, analyze, sha
from .led_network import solve, values
from .review import evaluate_cone, primary_pin_roles, review, validate


class UVRecoveryNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = analyze()
        _, cls.pins = netlist(ROOT / "generated/netlist.xml")

    def test_primary_physical_roles_and_native_exported_cone(self):
        r = review()
        self.assertEqual(r["physical_TPS3890_count"], 7)
        self.assertFalse(r["physical_role_errors"])
        self.assertEqual(len(r["truth_cases"]), 16)
        self.assertEqual(r["actual_new_component_refs"], ["C100", "R98", "R99", "U58"])
        self.assertFalse(r["actual_E28_native_latch_integration_implemented"])
        self.assertEqual(primary_pin_roles(ROOT / "sources/parent261/generated/netlist.xml"), (7, []))

    def test_post_ARM_UV_fault_does_not_reset_ARM(self):
        before = evaluate_cone(self.pins, True, True, True)
        fault = evaluate_cone(self.pins, True, False, True)
        self.assertFalse(before["E28_COMBINED_FAULT_REQUEST"])
        self.assertTrue(fault["E28_COMBINED_FAULT_REQUEST"])
        waiting = evaluate_cone(self.pins, True, False, False)
        self.assertFalse(waiting["N19_F_SOURCE"])
        # The actual retained-latch reset is GLOBAL, not UV/SAFE. This tests
        # the dangerous fault-erasing wiring mutation, not just a truth table.
        bad = copy.deepcopy(self.pins)
        bad["U50"]["2"] = "ABS_AUX_FAULT"
        self.assertTrue(validate(bad))

    def test_wrong_fault_polarity_and_RAW5_input_into_HCS_rejected(self):
        for ref, pin, wrong in [
            ("U51", "13", "ABS_AUX_FAULT"),
            ("U48", "13", "CLAMP_SUPPLY_ENABLE"),
            ("U58", "5", "DIG5_FORCE"),
        ]:
            bad = copy.deepcopy(self.pins)
            bad[ref][pin] = wrong
            self.assertTrue(validate(bad), (ref, pin))

    def test_energy_gate_cannot_be_bypassed(self):
        bad = copy.deepcopy(self.pins)
        bad["R11"]["1"] = "DIG5_FORCE"
        self.assertTrue(validate(bad))
        self.assertEqual(self.pins["U56"]["4"], "DIG5_FORCE")

    def test_all_MID_paths_are_actual_native_resistors(self):
        r, edges = values()
        self.assertEqual(len(edges), 7)
        self.assertEqual([r[k] for k in ["R5", "R98", "R12", "R99"]], [10000] * 4)
        bad = copy.deepcopy(self.pins)
        bad["R98"]["1"] = "N19_CLAMP_LED_A"
        self.assertTrue(validate(bad))

    def test_DC_enclosure_replays_actual_worst_case_and_rejects_weak_bleed(self):
        saved = json.loads((ROOT / "generated/LED-DC-network.json").read_text())
        r, edges = values()
        w = saved["worst"]
        current, residual, _ = solve(w["resistances_ohm"], edges, w["LED_shorts"], w["sink_shorts"])
        self.assertAlmostEqual(float(np.max(current)), saved["independent_Norton_enclosure_a"], places=13)
        self.assertLess(residual, 1e-15)
        self.assertLess(saved["forward_current_times1p2_a"], 10e-6)
        # Same load/backfeed requirements with a real, weaker1k bleed fail
        # the guarded receiving comparison. No guessed LED VF is credited.
        rb = 1000 * 1.03
        weak = 11e-6 * rb / (rb + min(r["R4"], r["R11"]) * 0.97) + 1e-6
        self.assertGreater(1.2 * weak, 10e-6)
        self.assertEqual(saved["dc_cases"], 65536)
        self.assertEqual(saved["forward_LED_comparisons"], 262144)
        self.assertFalse(saved["dynamic_gate_feedthrough_capacitive_and_optical_response_accepted"])
        self.assertIsNone(saved["full_cutoff_upper_s"])

    def test_UV_loading_delay_and_discrete_table_limits_remain_conditional(self):
        c = self.analysis["RAW5_supervisor_control"]
        self.assertGreater(c["settled_HIGH_given_requirements_v"], c["U58_VTplus_enclosure_receiving_v"])
        self.assertLess(c["settled_LOW_receiving_v"], c["U58_VTminus_enclosure_receiving_v"])
        self.assertLess(c["supervisor_sink_a"], c["supervisor_4p8V_sink_test_capacity_a"])
        self.assertGreater(
            c["threshold_crossing_current_available_a"], c["crossing_smart_pulldown_receiving_a"]
        )
        self.assertGreater(c["complete_delay_receiving_s"][0], 0.070)
        self.assertLess(c["complete_delay_receiving_s"][1], 0.162)
        self.assertIsNone(c["minimum_recognized_UV_pulse_guaranteed_s"])
        self.assertIsNone(c["physical_OFF_duration_guaranteed_s"])

    def test_LED_minimum_and_maximum_loaded_drive_are_both_screened(self):
        led = self.analysis["LED"]
        self.assertGreaterEqual(led["IF_lower_a"], 1.2 * led["hot_trigger_max_receiving_a"])
        self.assertLess(led["guarded_sink_current_a"], led["LVC_2p3V_VOLp3_test_current_a"])
        self.assertLess(led["complete_command_load_times1p2_a"], 20e-6)
        self.assertFalse(led["all_hot_Vf_IFC_IFT_RON_and_OPTICAL_timing_accepted"])

    def test_external_output_omission_fixed_and_all_pools_guarded(self):
        p = self.analysis["power"]
        self.assertGreater(p["two15k_host_pull_downs_plus_receiving_leaks_screen_a"], 0.0003)
        self.assertLessEqual(
            p["two15k_host_pull_downs_plus_receiving_leaks_screen_a"],
            p["old261_external_output_current_omission_corrected_a"],
        )
        self.assertLess(p["AUX_normal_guarded_a"], 0.011)
        self.assertLess(p["AUX_fault_guarded_a"], 0.014)
        self.assertLess(p["full_known_DIG_guarded_a"], 2.44)
        self.assertGreater(p["DIG_remaining_unassigned_a"], 0)
        self.assertLess(p["bleed_power_times1p2_w"], p["conditional_85C_TNPW1206_derated_power_w"])
        self.assertEqual(
            p["provisional_capacity_heat_w"],
            json.loads((ROOT / "sources/parent261/generated/analysis.json").read_text())["power"][
                "provisional_capacity_heat_w"
            ],
        )
        self.assertFalse(p["total_AUX_pool_partition_accepted"])

    def test_primary_return_cannot_rejoin_quiet_ground(self):
        bad = copy.deepcopy(self.pins)
        bad["U17"]["1"] = "AGND"
        self.assertTrue(validate(bad))
        self.assertFalse(self.analysis["primary_return"]["board_AGND_tie_permitted"])

    def test_DCK5_saved_land_matches_actual_manufacturer_drawing(self):
        fp = read_sexpr((ROOT / "NF05R_Manufacturer.pretty/TI_DCK0005A.kicad_mod").read_text())
        pads = {n[1]: n for n in children(fp, "pad")}
        self.assertEqual(set(pads), {"1", "2", "3", "4", "5"})
        centers = {"1": [-1.1, -0.65], "2": [-1.1, 0], "3": [-1.1, 0.65], "4": [1.1, 0.65], "5": [1.1, -0.65]}
        for n, p in pads.items():
            self.assertEqual(list(map(float, first(p, "size")[1:])), [0.95, 0.4])
            self.assertEqual(list(map(float, first(p, "at")[1:])), centers[n])
        r = json.loads((ROOT / "generated/package-fixture/verification.json").read_text())
        self.assertFalse(r["results"]["manufacturer"]["violations"])
        self.assertFalse(r["results"]["manufacturer"]["unconnected_items"])
        self.assertTrue(
            any(v["type"] == "clearance" for v in r["results"]["enlarged_DCU_pad_rejected"]["violations"])
        )
        self.assertFalse(r["actual_NF05_board_implemented"])

    def test_native_receipts_and_frozen_parent_hashes_current(self):
        for name, digest in json.loads((ROOT / "sources/manifest.json").read_text()).items():
            self.assertEqual(sha(ROOT / "sources" / name), digest, name)
        for report in [
            "native-review",
            "analysis",
            "equivalence",
            "LED-DC-network",
            "package-fixture/verification",
        ]:
            r = json.loads((ROOT / "generated" / f"{report}.json").read_text())
            for key in ["source_sha256", "artifact_sha256"]:
                for name, digest in r.get(key, {}).items():
                    self.assertEqual(sha(ROOT / name), digest, (report, name))
        parent = ROOT.parent / "absolute_aux_gate"
        handoff = json.loads((ROOT / "sources/parent261/handoff.json").read_text())
        for name, digest in handoff["files_sha256"].items():
            self.assertEqual(sha(parent / name), digest, ("sealed261", name))
        if (ROOT / "handoff.json").exists():
            for name, digest in json.loads((ROOT / "handoff.json").read_text())["files_sha256"].items():
                self.assertEqual(sha(ROOT / name), digest, name)

    def test_no_qualification_from_conditional_calculations(self):
        a = self.analysis
        for key in [
            "PCB_implemented",
            "startup_qualified",
            "partial_power_qualified",
            "physical_qualified",
            "release_approved",
        ]:
            self.assertFalse(a[key], key)
        self.assertIsNone(a["hardoff"]["maximum_actual_loaded_cutoff_s"])
        self.assertFalse(a["retained_ARM_UV_fault"]["no_reclose_guarantee_during_deep_AUX_corruption"])


if __name__ == "__main__":
    unittest.main()
