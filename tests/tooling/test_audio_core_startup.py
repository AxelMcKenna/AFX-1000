"""AC02 rejects prematurely enabled drivers and bypassed bias qualification."""

import copy
import json
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_audio_startup import OUT, check, powered_logic, timing


class AudioCoreStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.pins = netlist(OUT / "netlist.xml")

    def test_saved_source_bound_handoff(self):
        self.assertEqual(check(),json.loads((OUT / "integration-handoff.json").read_text()))

    def test_request_before_clock_ramp_rejected(self):
        pins=copy.deepcopy(self.pins)
        pins["U210"]["3"]="CHIP_EN"
        with self.assertRaises(AssertionError):
            powered_logic(pins)

    def test_bias_gate_bypass_rejected(self):
        pins=copy.deepcopy(self.pins)
        pins["U212"]["2"]="CODEC/SETTLE_ENABLE"
        with self.assertRaises(AssertionError):
            powered_logic(pins)

    def test_final_gate_cannot_bypass_bias_with_stale_timer(self):
        pins=copy.deepcopy(self.pins)
        pins["U209"]["1"]="CODEC/SETTLE_ENABLE"
        with self.assertRaises(AssertionError):
            powered_logic(pins)

    def test_old_minimum_capacitance_misses_ADC_settling(self):
        self.assertFalse(timing(1.5e-6)["passes"])
        self.assertTrue(timing(1.6e-6)["passes"])

    def test_legacy_chip_enable_wire_must_not_be_reused(self):
        self.assertEqual(self.pins["J104"]["2"],"ADC_DRV_ENABLE")
        self.assertEqual(self.pins["J205"]["8"],"CHIP_EN")
        self.assertNotEqual(self.pins["J104"]["2"],self.pins["J205"]["8"])


if __name__ == "__main__":
    unittest.main()
