"""Fault injection for the combined digital interfaces and source parity."""

import copy
import json
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.fabrication import audit_digital_core as audit


class DigitalIntegration(unittest.TestCase):
    def setUp(self):
        self.parts, self.pins = netlist(audit.OUT / "netlist.xml")

    def test_saved_native_proof_replays(self):
        self.assertEqual(audit.check(), json.loads((audit.OUT / "integration-handoff.json").read_text()))

    def test_reset_cannot_move_to_five_volts(self):
        self.pins["U2001"]["18"] = "5V_DIG"
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts, self.pins)

    def test_spi_clock_data_swap_is_rejected(self):
        self.pins["U3005"]["3"], self.pins["U3005"]["4"] = self.pins["U3005"]["4"], self.pins["U3005"]["3"]
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts, self.pins)

    def test_source_resistor_change_is_rejected(self):
        parts = copy.deepcopy(self.parts)
        parts["R3001"].find("value").text = "0"
        with self.assertRaises(AssertionError):
            audit.verify_export(parts, self.pins)

    def test_manual_bypass_cannot_join_codec_run(self):
        self.pins["U2003"]["22"] = "CODEC_RUN"
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts, self.pins)

    def test_removed_header_cannot_remain(self):
        self.parts["J3011"] = copy.deepcopy(self.parts["J3002"])
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts, self.pins)


if __name__ == "__main__":
    unittest.main()
