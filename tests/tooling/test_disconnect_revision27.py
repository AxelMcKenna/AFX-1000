"""E27 circuit preservation, diagnostic solver and qualification rejection tests."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import read_sexpr
from hardware.electronics.rail_disconnect.revision26.check import preserved_geometry
from hardware.electronics.rail_disconnect.revision27.device_review import charge_screen, gate_screen
from hardware.electronics.rail_disconnect.revision27.qualify import validate_native
from hardware.electronics.rail_disconnect.revision27.replay import replay_bytes

try:
    import numpy as np

    from hardware.electronics.rail_disconnect.revision27.copper import RHO20, Mesh, solve_network
except ImportError:
    np = None
ROOT = Path(__file__).resolve().parents[2] / "hardware/electronics/rail_disconnect"


class SourceAndGateTests(unittest.TestCase):
    def test_replay_restores_actual_candidate_and_preserves_all_parent_items(self):
        base = read_sexpr((ROOT / "revision26/rail_disconnect.kicad_pcb").read_text())
        candidate = (ROOT / "revision27/rail_disconnect.kicad_pcb").read_bytes()
        tree = read_sexpr(candidate.decode())
        self.assertEqual(tree[: len(base)], base)
        self.assertTrue(all(n[0] in ("segment", "via") for n in tree[len(base) :]))
        recipe = json.loads((ROOT / "revision27/reviewed-additions.json").read_text())
        self.assertEqual(replay_bytes(recipe), candidate)
        preserved_geometry(tree, base)

    def test_tampered_replay_checksum_is_rejected(self):
        recipe = json.loads((ROOT / "revision27/reviewed-additions.json").read_text())
        recipe["candidate_pcb_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            replay_bytes(recipe)

    def test_native_warning_or_open_cannot_be_reported_away(self):
        raw = json.loads((ROOT / "revision27/generated/drc.json").read_text())
        report = json.loads((ROOT / "revision27/generated/pilot-findings.json").read_text())
        validate_native(report, raw)
        for key in ("native_drc_violations", "native_open_connections"):
            bad = copy.deepcopy(report)
            bad[key] = 0
            with self.assertRaises(AssertionError):
                validate_native(bad, raw)

    def test_charge_and_energy_scaling_do_not_become_a_timing_or_soa_pass(self):
        four = gate_screen(4, 153e-9, 4e-6)
        two = gate_screen(2, 153e-9, 2e-6)
        self.assertAlmostEqual(four["test_load_scale"], 612)
        self.assertAlmostEqual(
            four["charge_at_manufacturer_test_c"], 2 * two["charge_at_manufacturer_test_c"]
        )
        self.assertGreater(
            two["minimum_loaded_gate_v_with_allocations"], four["minimum_loaded_gate_v_with_allocations"]
        )
        self.assertIsNone(four["actual_turnon_or_turnoff_bound_s"])
        base = charge_screen(0.00564, 5.1, 0.001)
        slower = charge_screen(0.00564, 5.1, 0.002)
        double = charge_screen(0.00564, 10.2, 0.001)
        self.assertAlmostEqual(base["ideal_average_charging_a"], 28.764)
        self.assertAlmostEqual(slower["ideal_average_charging_a"], base["ideal_average_charging_a"] / 2)
        self.assertAlmostEqual(double["capacitor_energy_j"], 4 * base["capacitor_energy_j"])
        self.assertFalse(base["mosfet_soa_qualified"])


@unittest.skipIf(np is None, "NumPy is required for finite-volume diagnostics")
class DiagnosticSolverTests(unittest.TestCase):
    def test_series_and_parallel_networks_match_exact_circuit_results(self):
        series = solve_network(
            np.array([0, 1]), np.array([1, 2]), np.array([0.5, 0.25]), 3, np.array([0]), np.array([2])
        )
        self.assertAlmostEqual(series["ohm"], 6, places=9)
        parallel = solve_network(
            np.array([0, 0]), np.array([1, 1]), np.array([0.5, 0.25]), 2, np.array([0]), np.array([1])
        )
        self.assertAlmostEqual(parallel["ohm"], 1 / 0.75, places=9)

    def test_disconnected_network_is_not_a_zero_resistance_pass(self):
        row = solve_network(np.array([0]), np.array([1]), np.array([1.0]), 3, np.array([0]), np.array([2]))
        self.assertEqual(row["status"], "mesh_disconnected")
        self.assertNotIn("ohm", row)

    def fixture(self, via=True):
        board = """(kicad_pcb
        (footprint "synthetic" (layer "F.Cu") (at 110 110)
          (property "Reference" "A")
          (pad "1" smd rect (at 0 0) (size .6 .6) (layers "F.Cu") (net "/TEST")))
        (footprint "synthetic" (layer "B.Cu") (at 110 110)
          (property "Reference" "B")
          (pad "1" smd rect (at 0 0) (size .6 .6) (layers "B.Cu") (net "/TEST")))
        %s)""" % (
            '(via (at 110 110) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net "/TEST"))' if via else ""
        )
        return read_sexpr(board)

    def test_actual_barrel_conductance_and_plating_are_finite(self):
        mesh = Mesh(self.fixture(), "TEST", 0.1)
        row = mesh.resistance([("A", "1")], [("B", "1")], temp=20)
        expected = RHO20 * 1.6 / (np.pi * ((0.15 + 0.025) ** 2 - 0.15**2))
        self.assertAlmostEqual(row["ohm"], expected, places=10)
        thicker = mesh.resistance([("A", "1")], [("B", "1")], temp=20, plating=0.05)
        self.assertLess(thicker["ohm"], row["ohm"])

    def test_removing_the_only_via_breaks_opposite_layer_connection(self):
        mesh = Mesh(self.fixture(False), "TEST", 0.1)
        row = mesh.resistance([("A", "1")], [("B", "1")])
        self.assertEqual(row["status"], "mesh_disconnected")


if __name__ == "__main__":
    unittest.main()
