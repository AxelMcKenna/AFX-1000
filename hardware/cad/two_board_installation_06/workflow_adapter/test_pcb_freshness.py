"""Negative controls for the mechanical bridge, using a real captured PCB."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bridge', HERE / 'pcb_freshness.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
sx = bridge.sx


class MechanicalFreshness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = bridge.REPO / 'hardware/fabrication/staging/two-board-power-control-corridors-native-02/power_protection.kicad_pcb'
        cls.tree = sx.read_sexpr(cls.path.read_text())
        cls.original = bridge.snapshot(cls.path)

    def rejected(self, mutate, expected):
        tree = copy.deepcopy(self.tree)
        mutate(tree)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mutated.kicad_pcb'
            path.write_text(sx.sexpr(tree))
            differences = bridge.compare(self.original, bridge.snapshot(path))
        self.assertTrue(any(d['field'] == expected for d in differences), differences)

    def test_move(self):
        self.rejected(lambda t: sx.first(sx.first(t, 'footprint'), 'at').__setitem__(1, sx.a(999)), 'pose')

    def test_side(self):
        self.rejected(lambda t: sx.first(sx.first(t, 'footprint'), 'layer').__setitem__(1, 'B.Cu'), 'pose')

    def test_value(self):
        def mutate(t):
            next(p for p in sx.children(sx.first(t, 'footprint'), 'property') if p[1] == 'Value')[2] = 'UNREVIEWED PART'
        self.rejected(mutate, 'properties')

    def test_drill(self):
        def mutate(t):
            pad = next(p for f in sx.children(t, 'footprint') for p in sx.children(f, 'pad') if sx.children(p, 'drill'))
            sx.first(pad, 'drill')[1] = sx.a(9)
        self.rejected(mutate, 'physical')

    def test_courtyard(self):
        def mutate(t):
            line = next(line for f in sx.children(t, 'footprint') for line in sx.children(f, 'fp_line') if str(sx.first(line, 'layer')[1]).endswith('CrtYd'))
            sx.first(line, 'start')[1] = sx.a(999)
        self.rejected(mutate, 'physical')

    def test_outline(self):
        def mutate(t):
            for line in sx.children(t, 'gr_line'):
                if sx.first(line, 'layer')[1] == 'Edge.Cuts':
                    for tag in ('start', 'end'):
                        point = sx.first(line, tag)
                        point[1] = sx.a(float(point[1]) + 1)
        self.rejected(mutate, 'outline')

    def test_missing_footprint(self):
        self.rejected(lambda t: t.remove(sx.first(t, 'footprint')), 'presence')

    def test_identity(self):
        self.assertEqual([], bridge.compare(self.original, bridge.snapshot(self.path)))


if __name__ == '__main__':
    unittest.main()
