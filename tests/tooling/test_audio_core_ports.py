"""Audio-leg pin maps reject raw supplies, crossed domains and duplicate crimps."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.fabrication.audit_audio_ports import OUT, check, circuit, connections, harness


class AudioCorePorts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.pins,_=circuit()

    def test_source_bound_handoff(self):
        saved=json.loads((OUT/"integration-handoff.json").read_text())
        # AC03 is historical: replay its actual captured peer projects, rather
        # than expecting its receipt to name today's later E28 selection.
        selected=saved["audio_leg_connection_schedule"]["peer_source_selection"]
        snapshot={"roles":[dict(role=role,source=source,
                    native_review=str(Path(source).parent/"review.json")) for role,source in selected.items()]}
        scope=OUT.parents[3]/"hardware/fabrication/scope.json"
        read=Path.read_text
        def historical_selection(path,*args,**kwargs):
            return json.dumps(snapshot) if path==scope else read(path,*args,**kwargs)
        with patch.object(Path,"read_text",historical_selection):
            self.assertEqual(check(),saved)

    def reject(self,bundle,pin,**changes):
        rows=copy.deepcopy(connections())
        row=next(r for r in rows if r["bundle"]==bundle and r["core_pin"]==str(pin))
        row.update(changes)
        with self.assertRaises(AssertionError):
            harness(self.pins,rows)

    def test_raw_supply_cannot_replace_disconnect_output(self):
        self.reject("CORE-ANALOG-POWER",1,peer_header="J1")

    def test_five_volts_cannot_feed_MCU_logic_supply(self):
        self.reject("CORE-MCU-CONTROL",2,peer_role="rail_disconnect",peer_header="J3",peer_pin="6")

    def test_bias_channels_cannot_be_swapped(self):
        self.reject("CORE-BIAS-SENSE",2,peer_pin="3")

    def test_serial_clock_cannot_be_swapped_with_frame_sync(self):
        self.reject("CORE-SAI",2,peer_pin="3")

    def test_left_audio_cannot_be_swapped_with_right(self):
        self.reject("CORE-INPUT",1,peer_pin="3")

    def test_two_output_wires_cannot_share_one_source_contact(self):
        self.reject("CORE-BYPASS-HEALTH",10,peer_role="processor_carrier",peer_header="J6",peer_pin="6")

    def test_no_external_driver_enable_contact(self):
        for ref,terminals in self.pins.items():
            if ref.startswith("J"):
                self.assertNotIn("ADC_DRV_ENABLE",terminals.values())
                self.assertNotIn("CHIP_EN",terminals.values())


if __name__=="__main__":
    unittest.main()
