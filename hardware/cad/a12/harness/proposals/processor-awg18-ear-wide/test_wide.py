import copy
import importlib.util
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location("wide_review", ROOT / "review.py")
review = importlib.util.module_from_spec(s)
s.loader.exec_module(review)


class WideEar(unittest.TestCase):
    def test_preservation_rejects_undeclared_edits(self):
        old = read_sexpr((review.SOURCE / "processor_carrier.kicad_pcb").read_text())
        new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
        change = json.loads((ROOT / "generated/design-change.json").read_text())
        review.compare(old, new, change)
        for kind in ["J13", "H9", "via", "zone"]:
            trial = copy.deepcopy(new)
            if kind in ["J13", "H9"]:
                f = next(x for x in children(trial, "footprint") if review.reference(x) == kind)
                first(f, "at")[1] = "0"
            elif kind == "via":
                first(children(trial, "via")[0], "at")[1] = "0"
            else:
                q = next(x for x in children(trial, "zone") if children(x, "keepout"))
                first(q, "layers").pop()
            with self.assertRaises(AssertionError, msg=kind):
                review.compare(old, trial, change)

    def test_current_native_copper_and_connectivity(self):
        r = review.run(write=False)
        self.assertTrue(r["independent_cut_controls_prove_parallel_paths"])
        self.assertFalse(r["parent_PDN_inherited"])

    def test_real_fanout_destinations_and_unassigned_reserve(self):
        r = json.loads((ROOT / "generated/fanout-requirements.json").read_text())
        self.assertEqual(
            r["retained_positive_wire_current_allocations_a"],
            {"DIG-BYPASS": 0.14, "DIG-MONITOR": 0.08, "digital_reserve_no_physical_endpoint": 0.416},
        )
        self.assertIsNone(r["destinations"]["digital_reserve"])
        self.assertFalse(r["future_E19_source_ports_implemented"])
        for rel, h in r["source_sha256"].items():
            self.assertEqual(review.sha(review.REPO / rel), h)
        self.assertFalse(
            any(x["actual_native_PCB_exists"] for x in r["actual_native_destination_contracts"].values())
        )


if __name__ == "__main__":
    unittest.main()
