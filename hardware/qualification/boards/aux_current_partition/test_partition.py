"""Source ownership and real interface regressions; no hardware pass asserted."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist

from .analyze import analyze, ledger, power_run

ROOT = Path(__file__).resolve().parent


def physical_roles_match(pins, expected):
    return all(pins.get(ref) == roles for ref, roles in expected.items())


class PartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = analyze()

    def test_actual_original_PG_sink_and_EN_nodes(self):
        _, p = netlist(ROOT / "sources/P03/generated/complete-scratch-netlist.xml")
        self.assertEqual(p["U102"]["3"], "POWER_RUN")
        self.assertEqual(p["U102"]["5"], "VIN_IC")
        self.assertEqual(p["J106"]["3"], "POWER_RUN")
        self.assertTrue(self.a["value_only_repair_REJECTED"])

    def test_no_resistor_only_solution_and_150_is_rejected(self):
        self.assertTrue(self.a["value_only_feasible_intersection_empty"])
        self.assertFalse(any(x["joint_value_only_feasible"] for x in self.a["POWER_RUN_value_comparisons"]))
        candidate = self.a["rejected150_HIGH_comparison"]
        self.assertGreater(candidate["target_margin_v"], 0)
        self.assertFalse(candidate["PG1mA_row_supported"])
        self.assertLess(power_run(3300)["E28_RUN_min_v"], 2.0)

    def test_native_leaf_physical_roles_and_wrong_TPS_pin_mutation(self):
        parts, p = netlist(ROOT / "leaf/generated/netlist.xml")
        roles = self.a["conditional_new_leaf"]["actual_physical_pin_roles"]
        self.assertEqual(len(parts), 14)
        self.assertTrue(physical_roles_match(p, roles))
        wrong = copy.deepcopy(p)
        wrong["U1"]["4"], wrong["U1"]["6"] = wrong["U1"]["6"], wrong["U1"]["4"]
        self.assertFalse(physical_roles_match(wrong, roles))

    def test_B2B_common_source_not_common_drain(self):
        _, p = netlist(ROOT / "leaf/generated/netlist.xml")
        self.assertEqual(p["Q2"]["2"], p["Q3"]["2"])
        self.assertEqual(p["Q2"]["3"], "AUX")
        self.assertEqual(p["Q3"]["3"], "PRELIMIT")
        self.assertNotEqual(p["Q2"]["3"], p["Q3"]["3"])
        self.assertEqual(p["R4"], {"1": "PRELIMIT", "2": "POWER_RUN_E28_LEAF"})
        self.assertNotIn("POWER_RUN_INTERNAL", p["R4"].values())

    def test_leaf_conditional_HIGH_OFF_and_POR_test_load(self):
        l = self.a["conditional_new_leaf"]
        self.assertGreater(l["steady_HIGH_receiving_v"], 2.4)
        self.assertLess(l["destination_open_times1p2_v"], 0.4)
        self.assertLess(l["POR_current_times1p2_a"], 15e-6)
        self.assertLess(l["PG_LOW_sink_current_upper_at_VOLp4_a"], 0.001)
        self.assertGreater(l["input_gate_HIGH_receiving_v"], 2)
        self.assertGreater(l["bootstrap_initial_abs_VGS_floor_receiving_v"], 1.8)
        self.assertFalse(l["bootstrap_diode_VF_at3mA_hot_qualified"])
        self.assertIsNone(l["loaded_cutoff_upper_s"])
        self.assertFalse(l["below0p8V_partial_power_safe"])

    def test_full_reserve_not_spent_after_reference_reownership(self):
        for s in self.a["pool_scenarios"]:
            self.assertAlmostEqual(
                s["source_total_receiving_a"],
                s["unique_source_subtotal_a"] + s["preserved_NF_full_reserve_headroom_a"],
            )
            self.assertAlmostEqual(
                s["source_total_receiving_a"],
                s["E28_guarded_a"]
                + s["P03_guarded_a"]
                + s["NF_guarded_allocation_a"]
                + s["new_leaf_guarded_receiving_a"],
            )
        self.assertEqual(self.a["NF_allocations_already_guarded_normal_fault_a"], [0.011, 0.014])

    def test_60mA_not_claimed_and_current_sensitivity(self):
        e = self.a["E28"]
        self.assertEqual(len(e["active_Schmitt_inputs"]), 22)
        self.assertEqual(len(e["OC_pullups"]), 21)
        self.assertFalse({"R93", "R142", "R143"} & set(e["internal_output_pulldowns"]))
        self.assertGreater(e["scenarios"][0]["guarded_sum_a"], 0.060)
        less = ledger(slow_input_extra=0)
        self.assertAlmostEqual(
            e["scenarios"][0]["guarded_sum_a"] - less["scenarios"][0]["guarded_sum_a"], 22 * 0.0005 * 1.2
        )
        self.assertIsNone(e["complete_hot_VDD_VI_TT_static_dynamic_physical_bound_a"])

    def test_short_transient_remains_failed_not_hidden(self):
        s = next(s for s in self.a["pool_scenarios"] if s["name"].startswith("leaf_short"))
        self.assertFalse(s["numerical_receiving_screen_inside90mA"])
        self.assertGreater(s["source_total_receiving_a"], 0.100)
        self.assertTrue(self.a["no_source_pool_increase"])
        self.assertFalse(self.a["source_ldo_thermal_and_dynamic_stability_qualified"])

    def test_integration_proposal_new_refs_and_no_original_pin_swap(self):
        x = json.loads((ROOT / "integration-proposal.json").read_text())
        original, _ = netlist(ROOT / "sources/P03/generated/complete-scratch-netlist.xml")
        refs = {p["proposed_P03_ref"] for p in x["required_new_parts"]}
        self.assertEqual(len(refs), 12)
        self.assertFalse(refs & set(original))
        self.assertFalse(x["PCB_source_written"])
        self.assertEqual(
            x["changed_existing_pin"], {"J106.3": {"old_net": "POWER_RUN", "new_net": "POWER_RUN_E28_LEAF"}}
        )
        self.assertEqual(x["original_U102_pin_roles_preserved"], {"3": "POWER_RUN", "5": "VIN_IC"})

    def test_native_ERC_and_pin_value_parity_are_actual(self):
        native = json.loads((ROOT / "leaf/generated/native.json").read_text())
        self.assertFalse(native["erc_findings"])
        self.assertFalse(native["native_pin_value_mismatches"])
        self.assertTrue(all(x["returncode"] == 0 for x in native["command_results"]))
        self.assertFalse(native["PCB_implemented"])


if __name__ == "__main__":
    unittest.main()
