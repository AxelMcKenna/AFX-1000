"""Guard source circuitry, analog masks and PD route construction budgets."""

import copy
import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication import audit_audio_main_pd as audit


class PDRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = read_sexpr((audit.SOURCE / "audio_core.kicad_pcb").read_text())
        cls.board = read_sexpr((audit.OUT / "audio_core.kicad_pcb").read_text())
        cls.record = audit.read("distribution-construction.json")
        cls.captured = json.loads((audit.SOURCE / "final-native-inputs.json").read_text())

    def test_native_bus_completion_retained_circuit_and_spacing(self):
        proof = audit.check()
        self.assertEqual(proof["uncapped_open_connections"], 165)
        self.assertEqual(proof["native_islands_by_net"]["/ADC/PD_GATED"], 1)
        self.assertEqual(proof["remaining_amplifier_PD_gaps"], 3)
        self.assertEqual(proof["exhaustive_noise_geometry"]["violations"], [])

    def test_reject_changed_source_power_track(self):
        board = copy.deepcopy(self.board)
        node = next(n for n in children(board, "segment") if float(first(n, "width")[1]) == .6)
        first(node, "width")[1] = .2
        with self.assertRaisesRegex(AssertionError, "Retained or added"):
            audit.verify_routes(self.parent, board, self.record, self.captured)

    def test_reject_changed_analog_mask(self):
        board = copy.deepcopy(self.board)
        zone = next(n for n in children(board, "zone") if children(n, "keepout"))
        vertex = children(first(first(zone, "polygon"), "pts"), "xy")[0]
        vertex[1] = float(vertex[1])+.1
        with self.assertRaisesRegex(AssertionError, "Retained or added"):
            audit.verify_routes(self.parent, board, self.record, self.captured)

    def test_reject_larger_drill(self):
        board = copy.deepcopy(self.board)
        uid = self.record["added_vias"][0]["uuid"]
        first(next(n for n in children(board, "via") if str(first(n, "uuid")[1]) == uid), "drill")[1] = .4
        with self.assertRaisesRegex(AssertionError, "Retained or added"):
            audit.verify_routes(self.parent, board, self.record, self.captured)

    def test_reject_relaxed_route_length(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["maximum_planar_length_mm"] += 1
        with self.assertRaises(AssertionError):
            audit.verify_routes(self.parent, self.board, record, self.captured)

    def test_reject_false_source_island(self):
        record = copy.deepcopy(self.record)
        record["routes"][0]["source_groups"][1] = record["routes"][0]["source_groups"][0]
        with self.assertRaisesRegex(AssertionError, "False native island"):
            audit.verify_routes(self.parent, self.board, record, self.captured)

    def test_supervisor_bus_cannot_enter_FDA_protection_region(self):
        screen = audit.QuietTraceScreen(self.captured, audit.NETS)
        self.assertFalse(screen.legal("/ADC/PD_GATED", "F.Cu", [[49.2, 26.8], [49.4, 26.8]]))


if __name__ == "__main__":
    unittest.main()
