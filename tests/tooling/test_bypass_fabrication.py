"""Actual checked E11 evidence and original-circuit preservation regression gate."""

import json
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import native_evidence_errors, sha
from hardware.fabrication.evidence_paths import recorded_path

REPO = Path(__file__).resolve().parents[2]
CHECKED = REPO/"hardware/fabrication/staging/bypass-closed-native-03"


class BypassFabricationEvidence(unittest.TestCase):
    def test_checked_native_files_libraries_and_handoff_are_current(self):
        native = json.loads((CHECKED/"review.json").read_text())
        self.assertEqual(native_evidence_errors(CHECKED/"sequenced_bypass.kicad_pro",native),[])
        self.assertTrue(native["status"]["native_closed"])
        handoff = json.loads((CHECKED/"handoff.json").read_text())
        self.assertEqual([p for p,digest in handoff["source_sha256"].items() if not recorded_path(p).is_file() or sha(recorded_path(p)) != digest],[])
        self.assertFalse(handoff["fabrication_released"])
        self.assertFalse(handoff["physical_qualified"])

    def test_final_export_retains_the_original55_part_circuit(self):
        original,pins = netlist(REPO/"hardware/electronics/sequenced_bypass/generated/netlist.xml")
        actual,actual_pins = netlist(CHECKED/"netlist.xml")
        self.assertEqual(len(actual),55)
        self.assertEqual(pins,actual_pins)
        self.assertEqual({r:p.findtext("value") for r,p in original.items()},
                         {r:p.findtext("value") for r,p in actual.items()})
        self.assertEqual({r for r in actual if original[r].findtext("footprint") != actual[r].findtext("footprint")},{"U1","U3"})

    def test_watchdog_land_revisions_have_current_independent_circuit_and_copper_evidence(self):
        for label in ("nf-watchdog-land-native-01","fan-watchdog-land-native-01"):
            with self.subTest(label=label):
                folder = REPO/"hardware/fabrication/staging"/label
                report = json.loads((folder/"package-correction-review.json").read_text())
                self.assertEqual([p for p,digest in report["source_sha256"].items() if not recorded_path(p).is_file() or sha(recorded_path(p)) != digest],[])
                self.assertTrue(report["all_original_circuit_values_and_pin_nets_exact"])
                self.assertTrue(report["all_existing_tracks_vias_and_authored_zones_exact"])


if __name__ == "__main__":
    unittest.main()
