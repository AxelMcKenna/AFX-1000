import unittest
from types import SimpleNamespace
from shapely.geometry import LineString, box
from hardware.fabrication.digital_route_shortcuts import simplify


class ShortcutTests(unittest.TestCase):
    def test_removes_bends_and_preserves_vias_and_endpoints(self):
        s = SimpleNamespace(legal=lambda *args: True)
        result = dict(runs=[('F.Cu',[(0,0),(1,1),(2,0)])],vias=[(0,0)])
        r = simplify(s,'n',result)
        self.assertEqual(r,dict(runs=[('F.Cu',[(0,0),(2,0)])],vias=[(0,0)]))

    def test_does_not_shortcut_across_foreign_copper(self):
        obstacle = box(.5,-.5,1.5,.5)
        s = SimpleNamespace(legal=lambda n,f,p: not LineString(p).intersects(obstacle))
        r = simplify(s,'n',dict(runs=[('F.Cu',[(0,0),(0,1),(2,1),(2,0)])],vias=[]))
        self.assertFalse(LineString(r['runs'][0][1]).intersects(obstacle))
        self.assertGreater(len(r['runs'][0][1]),2)

    def test_illegal_original_segment_rejected(self):
        s = SimpleNamespace(legal=lambda *args: False)
        with self.assertRaises(AssertionError):
            simplify(s,'n',dict(runs=[('F.Cu',[(0,0),(1,0)])],vias=[]))


if __name__ == '__main__':
    unittest.main()
