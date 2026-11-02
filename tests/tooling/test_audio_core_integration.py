"""Saved shared-core evidence and deliberately broken analog interface joins."""

import copy
import json
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_audio_core import OUT, check, joins


class AudioCoreIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.pins = netlist(OUT / "netlist.xml")

    def test_saved_source_bound_handoff_replays(self):
        self.assertEqual(check(), json.loads((OUT / "integration-handoff.json").read_text()))

    def rejected(self, changes):
        pins = copy.deepcopy(self.pins)
        for ref, pin, net in changes:
            pins[ref][pin] = net
        with self.assertRaises(AssertionError):
            joins(pins)

    def test_missing_ADC_force_rejected(self):
        self.rejected([("R105", "2", "BROKEN_FORCE")])

    def test_sense_joined_to_wrong_polarity_rejected(self):
        self.rejected([("R104", "1", "ADC_LN")])

    def test_swapped_codec_ADC_pins_rejected(self):
        self.rejected([("U201", "15", "ADC_LN"), ("U201", "16", "ADC_LP")])

    def test_swapped_raw_DAC_pins_rejected(self):
        self.rejected([("U201", "4", "DAC_LP"), ("U201", "5", "DAC_LN")])

    def test_reference_loaded_from_wrong_channel_rejected(self):
        self.rejected([("R108", "1", "REF_ADC2")])

    def test_driver_request_disconnected_from_hardware_gate_rejected(self):
        self.rejected([("R143", "1", "ADC/BIAS_OK")])


if __name__ == "__main__":
    unittest.main()
