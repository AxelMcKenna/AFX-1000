"""Read-only package mutations; native copper fault injection is separate."""

import copy
import unittest
from unittest.mock import patch

import review

from hardware.electronics.common.sexpr import children, first, read_sexpr


class SupportTests(unittest.TestCase):
    def test_current_package_and_raw_proof(self):
        r = review.run(write=False)
        self.assertEqual(r["total_footprints"], 86)
        self.assertEqual(r["schematic_components_unchanged"], 77)
        self.assertFalse(r["physical_qualified"])
        self.assertFalse(r["source_parent_PDN_result_inherited"])
        self.assertFalse(r["full_tensor_started"])

    def test_moved_J13_bad_bore_missing_layer_and_small_keepout_rejected(self):
        old = read_sexpr((review.SOURCE / "processor_carrier.kicad_pcb").read_text())
        actual = read_sexpr((review.ROOT / "processor_carrier.kicad_pcb").read_text())
        oldzones = {str(first(z, "uuid")[1]) for z in children(old, "zone")}
        for mode in ["moved_J13", "bad_bore", "missing_layer", "small_keepout"]:
            bad = copy.deepcopy(actual)
            h9 = next(f for f in children(bad, "footprint") if review.reference(f) == "H9")
            zone = next(z for z in children(bad, "zone") if str(first(z, "uuid")[1]) not in oldzones)
            if mode == "moved_J13":
                j = next(f for f in children(bad, "footprint") if review.reference(f) == "J13")
                first(j, "at")[1] = "257.5"
            elif mode == "bad_bore":
                first(children(h9, "pad")[0], "drill")[1] = "2.0"
            elif mode == "missing_layer":
                first(zone, "layers").remove("In1.Cu")
            else:
                for p in first(first(zone, "polygon"), "pts")[1:]:
                    p[1] = str(252 + (float(p[1]) - 252) * 0.8)
                    p[2] = str(155.2 + (float(p[2]) - 155.2) * 0.8)
            with self.subTest(mode=mode), patch.object(review, "read_sexpr", side_effect=[old, bad]):
                with self.assertRaises(AssertionError):
                    review.run(write=False)


if __name__ == "__main__":
    unittest.main()
