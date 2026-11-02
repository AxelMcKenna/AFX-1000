"""Fault injection for six-section audio joining and powered bypass qualifiers."""

import json
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.fabrication import audit_audio_main as audit


class AudioMainIntegration(unittest.TestCase):
    def setUp(self):
        self.parts,self.pins=netlist(audit.OUT/"netlist.xml")

    def test_recorded_six_section_proof_replays(self):
        self.assertEqual(audit.check(),json.loads(audit.HANDOFF.read_text()))

    def test_master_output_cannot_use_twelve_volt_rail(self):
        self.pins["U501"]["8"]="P12"
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts,self.pins)

    def test_relay_coil_cannot_use_analog_five_volt_rail(self):
        self.pins["K401"]["1"]="V5_REG"
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts,self.pins)

    def test_input_and_output_range_coils_cannot_diverge(self):
        self.pins["K503"]["8"]="BYPASS/INPUT_LOW"
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts,self.pins)

    def test_processed_stereo_output_cannot_be_swapped(self):
        self.pins["K601"]["4"],self.pins["K601"]["5"]=self.pins["K601"]["5"],self.pins["K601"]["4"]
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts,self.pins)

    def test_adc_sense_cannot_join_other_polarity(self):
        self.pins["R104"]["1"]="ADC_LN"
        with self.assertRaises(AssertionError):
            audit.verify_export(self.parts,self.pins)

    def test_wet_enable_cannot_bypass_clear_qualifier(self):
        self.pins["U606"]["5"]="V3V3_IO"
        with self.assertRaises(AssertionError):
            audit.coupled_logic(self.pins)

    def test_gain_change_must_invalidate_input_ready(self):
        self.pins["U606"]["13"]="V3V3_IO"
        with self.assertRaises(AssertionError):
            audit.coupled_logic(self.pins)

    def test_manual_bypass_must_keep_qualified_input_connected(self):
        self.pins["U602"]["1"]="BYPASS/PROCESS_OK"
        with self.assertRaises(AssertionError):
            audit.coupled_logic(self.pins)

    def test_raw_supply_cannot_replace_protected_supply(self):
        rows=audit.connections()
        row=next(r for r in rows if r["audio_header"]=="J701" and r["audio_pin"]=="1")
        row["peer_header"]="J1"
        with self.assertRaises(AssertionError):
            audit.harness(self.pins,rows)

    def test_sai_clock_wire_cannot_swap_with_frame_sync(self):
        rows=audit.connections()
        row=next(r for r in rows if r["audio_header"]=="J203" and r["audio_pin"]=="2")
        row["peer_pin"]="3"
        with self.assertRaises(AssertionError):
            audit.harness(self.pins,rows)


if __name__=="__main__":
    unittest.main()
