"""Readiness cannot hide missing packages, boards, wiring or stale evidence."""

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from hardware.wiring.board_readiness import check


class BoardReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = check.inventory()

    def test_external_profile_has_thirteen_boards_without_historic_duplicate_relays(self):
        names = {b["board"] for b in self.data["boards"]}
        self.assertEqual(len(names), 13)
        self.assertIn("sequenced_bypass", names)
        self.assertNotIn("bypass", names)
        self.assertNotIn("audio_bypass", names)

    def test_converter_package_and_absent_boards_are_visible(self):
        self.assertEqual(self.data["boards_with_missing_footprints"], ["converter"])
        self.assertEqual(
            set(self.data["boards_without_pcb"]),
            {"rail_monitor", "converter", "dac_receiver", "sequenced_bypass"},
        )
        self.assertFalse(self.data["build_ready"])
        self.assertFalse(self.data["complete_unit_electronics"])

    def test_peripheral_and_anode_pin_inventory_is_exact(self):
        self.assertEqual(self.data["required_unassigned_header_pin_count"], 24)
        self.assertEqual(self.data["wiring_pin_pairs_checked"], 320)
        self.assertEqual(len(self.data["unselected_distribution_fanouts"]), 19)
        required = self.data["required_unassigned_header_pins"][:-1]
        with self.assertRaises(AssertionError):
            check.validate_boards(self.data["boards"], required)

    def test_missing_converter_footprint_cannot_be_hidden(self):
        boards = copy.deepcopy(self.data["boards"])
        next(b for b in boards if b["board"] == "converter")["missing_footprint_references"] = []
        with self.assertRaisesRegex(AssertionError, "Converter package gap"):
            check.validate_boards(boards, self.data["required_unassigned_header_pins"])

    def test_a_schematic_cannot_be_reported_as_a_closed_pcb(self):
        boards = copy.deepcopy(self.data["boards"])
        board = next(b for b in boards if b["board"] == "dac_receiver")
        board["native_open_connections"] = 0
        board["recorded_native_connectivity_closed"] = True
        with self.assertRaises(AssertionError):
            check.validate_boards(boards, self.data["required_unassigned_header_pins"])

    def test_adc_characterization_board_is_not_a_final_converter_assembly(self):
        board = next(b for b in self.data["boards"] if b["board"] == "adc_driver")
        self.assertTrue(board["pcb_present"])
        self.assertTrue(board["recorded_native_connectivity_closed"])
        self.assertFalse(board["new_candidate_integrated_in_a11"])
        self.assertFalse(board["electrical_performance_qualified"])

    def test_no_candidate_is_a_fabrication_release(self):
        boards = copy.deepcopy(self.data["boards"])
        boards[0]["fabrication_released"] = True
        with self.assertRaises(AssertionError):
            check.validate_boards(boards, self.data["required_unassigned_header_pins"])

    def test_stale_or_missing_source_fingerprints_remain_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            folder = base / "board"
            folder.mkdir()
            path = folder / "circuit.txt"
            path.write_text("original")
            record = {"source_sha256": {"circuit.txt": hashlib.sha256(path.read_bytes()).hexdigest()}}
            location = folder / "generated/verification.json"
            self.assertTrue(check.record_sources(record, location)["all_recorded_sources_current"])
            path.write_text("changed")
            self.assertEqual(check.record_sources(record, location)["changed_sources"], ["circuit.txt"])
            path.unlink()
            self.assertEqual(check.record_sources(record, location)["missing_sources"], ["circuit.txt"])


if __name__ == "__main__":
    unittest.main()
