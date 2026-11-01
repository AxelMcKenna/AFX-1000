"""Protect the complete original rail-window circuit in the selected PCB."""

import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.evidence_paths import recorded_path


class RailMonitorCircuit(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[2]
        scope = json.loads((self.repo/"hardware/fabrication/scope.json").read_text())
        self.role = next(r for r in scope["roles"] if r["role"] == "rail_monitor")
        self.folder = (self.repo/self.role["source"]).parent

    def test_selected_native_circuit_preserves_every_original_part_and_pin(self):
        original = self.repo/"hardware/electronics/rail_monitor/generated/netlist.xml"
        old_parts,old_pins = netlist(original)
        parts,pins = netlist(self.folder/"netlist.xml")
        self.assertEqual(len(parts),181)
        self.assertEqual(pins,old_pins)
        for ref in parts:
            for field in ("value","footprint"):
                self.assertEqual(parts[ref].findtext(field),old_parts[ref].findtext(field),(ref,field))

    def test_handoff_dependencies_match_and_release_is_withheld(self):
        record = json.loads((self.repo/self.role["handoff"]).read_text())
        for name,digest in record["source_sha256"].items():
            with self.subTest(name=name):
                self.assertEqual(sha(recorded_path(name)),digest)
        self.assertFalse(record["fabrication_released"])
        self.assertFalse(record["physical_qualified"])
        self.assertFalse(record["manufacturing_process_accepted"])


if __name__ == "__main__":
    unittest.main()
