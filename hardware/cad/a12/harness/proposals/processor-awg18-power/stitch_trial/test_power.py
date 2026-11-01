"""Boundary/mutation checks for the E19 diagnostic, not synthetic qualification."""

import copy
import json
import unittest
from pathlib import Path

import numpy as np
from mesh import LAYERS, Mesh, response

from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent


class FinitePowerTests(unittest.TestCase):
    def test_four_layers_and_finite_actual_holes(self):
        pads = json.loads((ROOT / "generated/baseline/pads.json").read_text())
        tree = read_sexpr((ROOT / "generated/baseline/filled.kicad_pcb").read_text())
        m = Mesh(tree, pads, "5V_DIG", 0.15)
        n = m.network([0.035] * 4, [0.0175, 0.2525, 1.3475, 1.5825])
        self.assertEqual(LAYERS, ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"))
        self.assertGreater(n["finite_holes"], 0)
        with self.assertRaises(AssertionError):
            m.network([0.07] * 6, [0, 0.1, 0.2, 0.3, 0.4, 0.5])
        with self.assertRaisesRegex(AssertionError, "absent on"):
            n["electrode"]("R1.1", "B.Cu")

    def test_current_electrodes_obey_analytic_network_and_reciprocity(self):
        ports = {"source": np.array([0]), "a": np.array([1]), "b": np.array([2])}
        n = dict(
            n=3,
            u=np.array([0, 1]),
            v=np.array([1, 2]),
            g=np.array([2.0, 4.0]),
            electrode=lambda ref, face: ports[ref],
        )
        r = response(
            n,
            ("source", "B.Cu"),
            {"a": ("a", "F.Cu"), "b": ("b", "F.Cu")},
            {"a": ("a", "F.Cu"), "b": ("b", "F.Cu")},
        )
        self.assertAlmostEqual(r["transfer_resistance_ohm"]["a"]["a"], 0.5)
        self.assertAlmostEqual(r["transfer_resistance_ohm"]["b"]["a"], 0.5)
        self.assertAlmostEqual(r["transfer_resistance_ohm"]["b"]["b"], 0.75)
        self.assertFalse(r["equipotential_pad_or_via_short_used"])
        broken = copy.copy(n)
        broken["g"] = np.array([2.0])
        broken["u"] = np.array([0])
        broken["v"] = np.array([1])
        with self.assertRaisesRegex(AssertionError, "disconnected"):
            response(broken, ("source", "B.Cu"), {"b": ("b", "F.Cu")}, {"b": ("b", "F.Cu")})

    def test_coarse_unresolved_native_annulus_is_rejected(self):
        pads = json.loads((ROOT / "generated/baseline/pads.json").read_text())
        tree = read_sexpr((ROOT / "generated/baseline/filled.kicad_pcb").read_text())
        m = Mesh(tree, pads, "AGND", 0.2)
        with self.assertRaisesRegex(AssertionError, "Unresolved AGND barrel annulus"):
            m.network([0.035] * 4, [0.0175, 0.2525, 1.3475, 1.5825])


if __name__ == "__main__":
    unittest.main()
