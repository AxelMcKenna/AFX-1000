import copy
import unittest

from hardware.electronics.common.sexpr import a, children, first, read_sexpr

from .validate import ROOT, validate


class Mount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text())

    def test_actual_clip_successor(self):
        self.assertEqual(validate(self.tree)["clip_keepout_records"], 16)

    def test_missing_inner_clip_keepout_rejected(self):
        t = copy.deepcopy(self.tree)
        z = next(z for z in children(t, "zone") if children(z, "name") and str(first(z, "name")[1]).startswith("MOUNT_CLIP_") and first(z, "layer")[1] == "In2.Cu")
        t.remove(z)
        with self.assertRaisesRegex(AssertionError, "Missing all-layer"):
            validate(t)

    def test_via_allowed_in_clip_rejected(self):
        t = copy.deepcopy(self.tree)
        z = next(z for z in children(t, "zone") if children(z, "name") and str(first(z, "name")[1]).startswith("MOUNT_CLIP_"))
        first(first(z, "keepout"), "vias")[1] = a("allowed")
        with self.assertRaises(AssertionError):
            validate(t)

    def test_clock_copper_deletion_rejected(self):
        t = copy.deepcopy(self.tree)
        n = next(n for n in children(t, "segment") if first(n, "net")[1] == "/XTAL1")
        t.remove(n)
        with self.assertRaisesRegex(AssertionError, "unrelated"):
            validate(t)

    def test_component_move_rejected(self):
        t = copy.deepcopy(self.tree)
        f = children(t, "footprint")[0]
        first(f, "at")[1] = a(float(first(f, "at")[1]) + .1)
        with self.assertRaisesRegex(AssertionError, "footprint"):
            validate(t)

    def test_narrow_RAW5_track_rejected(self):
        t = copy.deepcopy(self.tree)
        n = next(n for n in children(t, "segment") if first(n, "net")[1] == "/FAN5V_IN")
        first(n, "width")[1] = a(.15)
        with self.assertRaises(AssertionError):
            validate(t)


if __name__ == "__main__":
    unittest.main()
