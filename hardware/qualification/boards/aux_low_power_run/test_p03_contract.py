"""Cross-board regressions reject the original raw-RUN load and pin swaps."""

import copy
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist

from .p03_contract import interface

REPO = Path(__file__).resolve().parents[4]


class IntegratedRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.source = netlist(REPO / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/netlist.xml")
        cls.receiver_parts, cls.receiver = netlist(REPO / "hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/netlist.xml")

    def test_actual_native_four_wire_contract(self):
        mapping = interface(self.parts, self.source, self.receiver_parts, self.receiver)
        self.assertEqual([(r["P03"], r["E28"]) for r in mapping],
                         [("J106.1", "J5.1"), ("J106.2", "J5.2"), ("J106.3", "J5.3"), ("J106.4", "J9.2")])

    def test_raw_RUN_cannot_bypass_output_buffer(self):
        wrong = copy.deepcopy(self.source)
        wrong["J106"]["3"] = "POWER_RUN"
        with self.assertRaises(ValueError):
            interface(self.parts, wrong, self.receiver_parts, self.receiver)

    def test_receiver_cannot_bypass_U43(self):
        wrong = copy.deepcopy(self.receiver)
        wrong["U28"]["1"] = "POWER_RUN"
        with self.assertRaises(ValueError):
            interface(self.parts, self.source, self.receiver_parts, wrong)

    def test_supervisor_package_pin_swap_is_rejected(self):
        wrong = copy.deepcopy(self.source)
        wrong["U201"]["4"], wrong["U201"]["6"] = wrong["U201"]["6"], wrong["U201"]["4"]
        with self.assertRaises(ValueError):
            interface(self.parts, wrong, self.receiver_parts, self.receiver)

    def test_READY_cannot_be_shortcut_to_RUN(self):
        wrong = copy.deepcopy(self.source)
        wrong["J106"]["4"] = "POWER_RUN_E28_LEAF"
        with self.assertRaises(ValueError):
            interface(self.parts, wrong, self.receiver_parts, self.receiver)

    def test_original_PG_pullup_value_is_preserved(self):
        wrong = copy.deepcopy(self.parts)
        wrong["R113"].find("value").text = "1k 1%"
        with self.assertRaises(ValueError):
            interface(wrong, self.source, self.receiver_parts, self.receiver)


if __name__ == "__main__":
    unittest.main()
