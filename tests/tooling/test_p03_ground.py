"""Independent analytical checks for the diagnostic sheet/barrel network."""

import math
import unittest
from types import SimpleNamespace

try:
    import numpy as np
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse.linalg import spsolve

    from hardware.qualification.boards.p03_ground import graph
except ImportError:
    graph = None


@unittest.skipIf(graph is None, "Optional NumPy/SciPy diagnostic dependencies unavailable")
class GroundPhysics(unittest.TestCase):
    def test_uniform_sheet_matches_closed_form(self):
        mask = np.zeros((6, 20, 10), dtype=bool)
        mask[0] = True
        mesh = SimpleNamespace(mask=mask, x=np.arange(20), y=np.arange(10), holes=[], pads={})
        lap, _, _ = graph(mesh, np.array([0.035, 0.2, 0.6, 1, 1.4, 1.565]), np.full(6, 0.07), 0.05, 1, 20)
        free = np.arange(10, 200)
        rhs = np.zeros(190)
        rhs[-10:] = 0.1
        potential = spsolve(lap[free][:, free], rhs)
        expected = 19 * 1.8e-5 / (10 * 0.07)
        np.testing.assert_allclose(potential[-10:], expected, rtol=1e-10)
        self.assertAlmostEqual(float(potential @ rhs), expected, places=12)

    def test_one_barrel_matches_cylindrical_wall(self):
        mask = np.zeros((6, 1, 1), dtype=bool)
        mask[[0, 5]] = True
        mesh = SimpleNamespace(
            mask=mask, x=np.array([0.0]), y=np.array([0.0]), holes=[((0, 0), 0.25, 0.3)], pads={}
        )
        depths = np.array([0.0425, 0.22, 0.6, 1.0, 1.38, 1.5575])
        area = math.pi * (0.175**2 - 0.125**2)
        for scale, temperature in [(1, 20), (1.1, 85)]:
            lap, _, _ = graph(mesh, depths, np.full(6, 0.07), 0.05, scale, temperature)
            actual = 1 / float(lap[1, 1])
            expected = 2e-5 * (1 + 0.0041 * (temperature - 20)) * 1.515 * scale / area
            self.assertAlmostEqual(actual, expected, places=12)

    def test_missing_barrel_does_not_connect_layers(self):
        mask = np.zeros((6, 1, 1), dtype=bool)
        mask[[0, 5]] = True
        mesh = SimpleNamespace(mask=mask, x=np.array([0.0]), y=np.array([0.0]), holes=[], pads={})
        lap, _, _ = graph(mesh, np.array([0.04, 0.2, 0.6, 1, 1.4, 1.56]), np.full(6, 0.07), 0.05, 1, 85)
        count, labels = connected_components(lap, directed=False)
        self.assertEqual(count, 2)
        self.assertNotEqual(labels[0], labels[1])


if __name__ == "__main__":
    unittest.main()
