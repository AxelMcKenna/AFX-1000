"""Actual-interface regressions and counterexamples for the low-power revision."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist

from .analyze import analyze

ROOT=Path(__file__).resolve().parent


def physical_map_ok(pins):
    return (pins["U1"]["4"]=="AUX" and pins["U1"]["6"]=="RUN_GATE_COMMAND"
            and pins["U2"]["2"]=="RUN_GATE_COMMAND" and pins["U2"]["4"]=="RUN_BUFFERED_SOURCE"
            and pins["U2"]["3"]=="AGND" and pins["U2"]["5"]=="AUX")


class LowPowerRun(unittest.TestCase):
    def test_actual_native_pin_roles_and_swap_mutation(self):
        _,pins=netlist(ROOT/"generated/netlist.xml")
        self.assertTrue(physical_map_ok(pins))
        wrong=copy.deepcopy(pins)
        wrong["U1"]["4"],wrong["U1"]["6"]=wrong["U1"]["6"],wrong["U1"]["4"]
        self.assertFalse(physical_map_ok(wrong))
        self.assertEqual(pins["R4"],{"1":"RUN_BUFFERED_SOURCE","2":"POWER_RUN_E28_LEAF"})

    def test_guarded_pool_fits_without_raising_source_capacity(self):
        d=analyze()
        self.assertTrue(d["all_receiving_scenarios_inside90mA"])
        self.assertLess(max(x["source_total_receiving_a"] for x in d["pool_scenarios"]),.09)
        self.assertEqual(d["existing_LDO_rating_a"],.1)
        self.assertFalse(d["source_regulator_or_voltage_changed"])
        self.assertFalse(d["original_PG_sink_load_increased"])
        self.assertEqual(d["original_R113_ohm"],3300)
        for row in d["pool_scenarios"]:
            self.assertLess(1.2*row["raw_receiving_before_joint1p2_a"],.1)

    def test_input_current_counterexample_is_not_hidden(self):
        failed=analyze(extra_per_input=200e-6)
        self.assertFalse(failed["all_receiving_scenarios_inside90mA"])
        self.assertGreater(max(x["source_total_receiving_a"] for x in failed["pool_scenarios"]),.09)
        self.assertFalse(analyze()["nonrail_receiving_bound_manufacturer_guaranteed"])
        self.assertIsNone(analyze()["complete_hot_current_physical_bound_a"])

    def test_high_LOW_and_output_drive_current_requirements(self):
        d=analyze()
        self.assertGreater(d["minimum_HIGH_guarded_margin_v"],0)
        self.assertGreater(d["source_RESET_HIGH_guarded_margin_v"],0)
        self.assertLess(d["disconnected_times1p2_v"],d["LOW_acceptance_floor_v"])
        self.assertLess(d["source_POR_pull_current_times1p2_a"],d["primary_POR_test_a"])
        self.assertLess(d["source_normal_output_current_max_a"],d["primary_light_load_row_max_a"])
        self.assertLess(d["short_current_times1p2_a"],d["source_pin_abs_max_output_a"])
        self.assertLess(d["wire_open_RC_to_LOW_acceptance_s"],.001)
        self.assertIsNone(d["standalone_loaded_cutoff_upper_s"])
        self.assertFalse(d["threshold_ratio_receiving"]["manufacturer_continuous_ratio_guarantee"])

    def test_original10k_receiver_is_rejected(self):
        bad=analyze(receiver_resistance=10000)
        self.assertLess(bad["minimum_HIGH_guarded_margin_v"],0)
        self.assertGreater(bad["source_normal_output_current_max_a"],20e-6)

    def test_all_eight_triples_keep_pin_functions_and_package(self):
        old={c["ref"]:c for c in json.loads((ROOT/"sources/E28-components.json").read_text())}
        new={c["ref"]:c for c in json.loads((ROOT/"e28-components-proposed.json").read_text())}
        refs=[r for r,c in old.items() if c["part"]=="SN74LVC3G17DCUR"]
        self.assertEqual(len(refs),8)
        for ref in refs:
            self.assertEqual(new[ref]["part"],"SN74AUP3G17DCUR")
            self.assertEqual(new[ref]["pins"],old[ref]["pins"])
            self.assertEqual(new[ref]["footprint"],old[ref]["footprint"])
            for pin in new[ref]["pins"]:
                if pin["kind"]!="output" or pin["net"] is None:
                    continue
                users=[(c,p) for c in new.values() for p in c["pins"] if p["net"]==pin["net"] and c["ref"]!=ref]
                self.assertTrue(users)
                self.assertTrue(all(p["kind"]=="input" and c["part"].startswith("SN74") for c,p in users))
                budget=sum(.5e-6 if c["part"].startswith("SN74AUP") else 5e-6 for c,p in users)+1e-6
                self.assertLess(budget,20e-6)

    def test_actual_source_and_receiver_native_ERC_and_parity(self):
        d=json.loads((ROOT/"generated/native.json").read_text())
        self.assertEqual(d["native_Mac_apps_launched"],0)
        for r in d["results"]:
            self.assertFalse(r["ERC"])
            self.assertFalse(r["mismatches"])
            self.assertTrue(r["source_unchanged"])
        self.assertFalse(d["PCB_implemented"])
        self.assertFalse(d["physical_qualified"])
        self.assertFalse(d["fabrication_released"])


if __name__=="__main__":
    unittest.main()
