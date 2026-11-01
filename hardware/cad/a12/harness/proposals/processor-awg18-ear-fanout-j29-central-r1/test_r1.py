import copy
import json
import unittest

from review import ROOT, SOURCE, check_ast, ref, run

from hardware.electronics.common.sexpr import children, first, read_sexpr


class SelectedR1(unittest.TestCase):
    def test_native_source_contracts(self):
        r = run(write=False)
        self.assertTrue(r["manufacturer_lands_exact"])
        self.assertFalse(r["physical_qualified"])

    def test_exact_object_preservation_negative_mutations(self):
        a = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
        b = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
        c = json.loads((ROOT / "generated/design-change.json").read_text())
        check_ast(a, b, c)
        for name in ["J29", "J13", "H9", "R1pad", "R1court", "foreignclock", "newSeedroute", "existingvia"]:
            q = copy.deepcopy(b)
            if name in ["J29", "J13", "H9"]:
                first(next(f for f in children(q, "footprint") if ref(f) == name), "at")[1] = "0"
            elif name == "R1pad":
                first(
                    children(next(f for f in children(q, "footprint") if ref(f) == "R1"), "pad")[0], "size"
                )[1] = "0.5"
            elif name == "R1court":
                first(
                    next(
                        x
                        for x in children(
                            next(f for f in children(q, "footprint") if ref(f) == "R1"), "fp_rect"
                        )
                        if first(x, "layer")[1] == "F.CrtYd"
                    ),
                    "start",
                )[1] = "0"
            elif name in ["foreignclock", "newSeedroute"]:
                net = "/BCLK" if name == "foreignclock" else "/SEED_VIN"
                first(next(x for x in children(q, "segment") if first(x, "net")[1] == net), "start")[1] = "0"
            else:
                first(children(q, "via")[0], "at")[1] = "0"
            with self.assertRaises(AssertionError, msg=name):
                check_ast(a, q, c)


if __name__ == "__main__":
    unittest.main()
