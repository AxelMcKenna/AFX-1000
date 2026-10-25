"""Reject crossed safety/audio/power interfaces and incomplete harness contracts."""

import copy
import unittest

from hardware.wiring import system


class SystemInterconnectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, _, cls.evidence = system.board_tables()
        cls.virtual = system.panel_specifications(cls.tables)[1]
        cls.wires = system.plan()["wires"]

    def check(self, wires, tables=None):
        system.validate(wires, self.tables if tables is None else tables, self.virtual)

    def test_source_protection_audio_and_front_interfaces_are_covered(self):
        self.check(self.wires)
        self.assertEqual(len(self.evidence), 13)
        self.assertEqual(len(self.wires), 320)
        self.assertEqual(sum(w["harness"] == "FRONT-CONTROLS" for w in self.wires), 64)
        self.assertEqual(sum(w["harness"] == "FRONT-POTS" for w in self.wires), 30)
        self.assertEqual(sum(w["harness"] == "PANEL-LED-SINKS" for w in self.wires), 96)
        self.assertTrue(self.evidence["rail_disconnect"]["physical_header_lands_checked"])
        self.assertTrue(self.evidence["converter"]["schematic_only_interfaces"])

    def test_missing_ground_and_duplicated_connection_are_rejected(self):
        ground = next(i for i, w in enumerate(self.wires) if w["net"] == "AGND")
        missing = copy.deepcopy(self.wires)
        missing.pop(ground)
        with self.assertRaisesRegex(AssertionError, "Missing or duplicated"):
            self.check(missing)
        duplicated = copy.deepcopy(self.wires)
        duplicated[-1] = copy.deepcopy(duplicated[0])
        with self.assertRaisesRegex(AssertionError, "duplicated endpoints"):
            self.check(duplicated)

    def test_unprotected_source_cannot_replace_a_protected_supply(self):
        changed = copy.deepcopy(self.wires)
        wire = next(w for w in changed if w["harness"] == "DIG-PROCESSOR" and w["net"] == "5V_DIG")
        wire["from"][1] = "J2"
        with self.assertRaises(AssertionError):
            self.check(changed)

    def test_alias_does_not_allow_digital_5v_to_become_analog_5v(self):
        changed = copy.deepcopy(self.wires)
        wire = next(w for w in changed if w["harness"] == "GAIN-OUTPUT_STAGE" and w["net"] == "5V_DIG")
        wire["net"] = "V5_REG"
        with self.assertRaisesRegex(AssertionError, "Wrong canonical net"):
            self.check(changed)
        tables = copy.deepcopy(self.tables)
        tables["sequenced_bypass"]["J5"]["1"] = "V5_REG"
        with self.assertRaisesRegex(AssertionError, "Alias local net changed"):
            self.check(self.wires, tables)

    def test_audio_channels_clocks_and_reset_cannot_be_crossed(self):
        for harness in ["SAI-AUDIO", "CONTROL-BUS", "ANALOG-IN"]:
            changed = copy.deepcopy(self.wires)
            wire = next(w for w in changed if w["harness"] == harness and w["to"][2] == "2")
            wire["to"][2] = "3"
            with self.subTest(harness=harness), self.assertRaises(AssertionError):
                self.check(changed)

    def test_led_cathodes_and_front_control_identities_are_exact(self):
        for harness in ["FRONT-CONTROLS", "PANEL-LED-SINKS"]:
            changed = copy.deepcopy(self.wires)
            wire = next(w for w in changed if w["harness"] == harness)
            wire["to"][1] = "wrong_control"
            with self.subTest(harness=harness), self.assertRaises(AssertionError):
                self.check(changed)

    def test_required_peripherals_fanouts_and_pitch_adapter_stay_unreleased(self):
        packet = system.plan()
        self.assertEqual(packet["remaining_required_header_pins"], 24)
        self.assertTrue(packet["fanouts"])
        self.assertTrue(packet["interface_construction"]["LED-CONTROL"]["pitch_adapter_required"])
        self.assertFalse(packet["complete_system_wiring"])
        self.assertFalse(packet["build_ready"])
        self.assertFalse(packet["electrical_and_ground_return_topology_qualified"])
        self.assertTrue(packet["source_power_voltage_loss_failures_remain"])
        self.assertTrue(all(not b["native_schematic_export_rechecked"] for b in packet["boards"].values()))
        for fanout in packet["fanouts"]:
            self.assertFalse(fanout["splice_or_distribution_assembly_selected"])

    def test_logical_pin_map_cannot_be_used_as_a_released_cut_list(self):
        for field, value in [
            ("assembly_released", True),
            ("cut_length_mm", 100),
            ("production_connector", "unreviewed"),
        ]:
            changed = copy.deepcopy(self.wires)
            changed[0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.check(changed)


if __name__ == "__main__":
    unittest.main()
