import copy
import importlib.util
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location("access_review", ROOT / "review.py")
review = importlib.util.module_from_spec(s)
s.loader.exec_module(review)


class AccessEar(unittest.TestCase):
    def test_exact_translation_rejects_other_changes(self):
        old = read_sexpr((review.SOURCE / "processor_carrier.kicad_pcb").read_text())
        new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
        change = json.loads((ROOT / "generated/design-change.json").read_text())
        review.compare(old, new, change)
        for kind in ["J13", "H9_other_x", "H9_drill", "via", "outline", "keepout"]:
            q = copy.deepcopy(new)
            if kind == "J13":
                f = next(x for x in children(q, "footprint") if review.reference(x) == "J13")
                first(f, "at")[1] = "0"
            elif kind.startswith("H9"):
                f = next(x for x in children(q, "footprint") if review.reference(x) == "H9")
                if kind == "H9_drill":
                    first(children(f, "pad")[0], "drill")[1] = "2.2"
                else:
                    first(f, "at")[1] = "251"
            elif kind == "via":
                first(children(q, "via")[0], "at")[1] = "0"
            elif kind == "outline":
                f = next(x for x in children(q, "gr_line") if first(x, "layer")[1] == "Edge.Cuts")
                first(f, "start")[1] = "0"
            else:
                f = next(
                    x
                    for x in children(q, "zone")
                    if children(x, "keepout")
                    and str(first(x, "uuid")[1]) == "ae9d9028-310a-5458-a9e2-6ffd8f76ab30"
                )
                first(f, "layers").pop()
            with self.assertRaises(AssertionError, msg=kind):
                review.compare(old, q, change)

    def test_current_native_and_actual_copper(self):
        r = review.run(write=False)
        self.assertGreater(r["actual_inter_hole_gate_width_mm"], 4.8)
        self.assertEqual(r["top_bypass_width_mm"], 0)
        self.assertFalse(r["parent_PDN_inherited"])


if __name__ == "__main__":
    unittest.main()
