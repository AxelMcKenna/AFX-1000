"""Actual native pin-map and adverse allocation checks for FP01."""

import json
import math
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.qualification.boards.fan_protection import design


class Protection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = design.analyze()
        cls.parts, cls.pins = netlist(design.OUT / "netlist.xml")

    def test_dbv_pin_contract_independent_of_generator(self):
        for ref, side in [("U1", "L"), ("U101", "R")]:
            self.assertEqual(self.parts[ref].findtext("value"), "TPS2553DBVR-1")
            self.assertEqual(
                self.pins[ref],
                {
                    "1": "FAN5V_IN",
                    "2": "FAN_GND",
                    "3": "FAN5V_IN",
                    "4": f"FAN_{side}_FAULT_N",
                    "5": f"FAN_{side}_ILIM",
                    "6": f"FAN_{side}_5V",
                },
            )

    def test_fan_connectors_preserve_black_red_yellow_assignment(self):
        for ref, side in [("J2", "L"), ("J3", "R")]:
            self.assertEqual(self.pins[ref], {"1": "FAN_GND", "2": f"FAN_{side}_5V", "3": f"FAN_{side}_TACH"})

    def test_tach_pullup_uses_switched_power_in_actual_netlist(self):
        for ref, side in [("R2", "L"), ("R102", "R")]:
            self.assertEqual(set(self.pins[ref].values()), {f"FAN_{side}_5V", f"FAN_{side}_TACH"})
            self.assertNotIn("FAN5V_IN", self.pins[ref].values())

    def test_no_unimplemented_status_pullup_is_invented(self):
        for net in ["FAN_L_FAULT_N", "FAN_R_FAULT_N"]:
            refs = {ref for ref, pins in self.pins.items() if net in pins.values()}
            self.assertEqual(refs, {"J4", "U1" if "_L_" in net else "U101"})

    def test_erc_contains_no_findings(self):
        erc = json.loads((design.OUT / "erc.json").read_text())
        self.assertEqual([v for s in erc["sheets"] for v in s["violations"]], [])

    def test_equation_matches_independent_table_row(self):
        lo, hi = design.current_interval(210000, 0)
        self.assertAlmostEqual(lo, 0.110, delta=0.002)
        self.assertAlmostEqual(hi, 0.150, delta=0.002)

    def test_extra_resistor_uncertainty_widens_interval(self):
        exact = design.current_interval(100000, 0)
        uncertain = design.current_interval(100000, 0.02)
        self.assertLess(uncertain[0], exact[0])
        self.assertGreater(uncertain[1], exact[1])

    def test_minimum_threshold_exceeds_normal_motor_provision(self):
        self.assertGreater(self.report["current_limit_interval_a"][0], 1.2 * 0.157)
        self.assertLess(self.report["current_limit_interval_a"][1], 0.310)

    def test_partition_does_not_add_motor_load_twice(self):
        p = self.report["digital_reserve_partition"]
        total = math.fsum(v for k, v in p.items() if k.endswith("_a") and k != "original_a")
        self.assertAlmostEqual(total, 0.416)
        self.assertGreater(p["remaining_for_health_logic_and_LED_a"], 0.006)

    def test_test_only_source_is_rejected(self):
        p = self.report["source_port_correction"]
        self.assertIs(p["old_FV01_J3_suggestion_usable"], False)
        self.assertEqual(p["source_stud"], "P03.J23")
        self.assertIs(p["new_branch_tap_connector_joint_and_return_implemented"], False)

    def test_no_dynamic_or_physical_acceptance_from_dc_screen(self):
        self.assertIsNone(self.report["maximum_fault_energy_j"])
        self.assertIsNone(self.report["conditional_voltage_screen"]["true_complete_fan_voltage_interval_v"])
        for key in [
            "PCB_implemented",
            "health_interlock_implemented",
            "physical_qualified",
            "fabrication_released",
        ]:
            self.assertIs(self.report[key], False)

    def test_input_rejection(self):
        for value, tol in [(10000, 0), (250000, 0), (100000, -1), (math.nan, 0.01), (math.inf, 0.01)]:
            with self.assertRaises(ValueError):
                design.current_interval(value, tol)

    def test_captured_sources_match_originals(self):
        report = json.loads((design.OUT / "analysis.json").read_text())
        for name, h in report["source_sha256"].items():
            self.assertEqual(design.sha(design.REPO / name), h, name)
            self.assertEqual(design.sha(design.ROOT / "sources" / name), h, name)


if __name__ == "__main__":
    unittest.main()
