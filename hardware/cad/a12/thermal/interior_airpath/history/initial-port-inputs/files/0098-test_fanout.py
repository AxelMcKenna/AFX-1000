import copy
import importlib.util
import json
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location("fanout_review", ROOT / "review.py")
review = importlib.util.module_from_spec(s)
s.loader.exec_module(review)


class FanoutCandidate(unittest.TestCase):
    def test_original_objects_and_new_ports_reject_undeclared_edits(self):
        old = read_sexpr((review.SOURCE / "processor_carrier.kicad_pcb").read_text())
        new = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
        change = json.load(open(ROOT / "generated/design-change.json"))
        review.compare(old, new, change)
        for kind in ["J13", "H9", "new_port", "via", "keepout"]:
            q = copy.deepcopy(new)
            if kind in ["J13", "H9", "new_port"]:
                ref = kind if kind != "new_port" else "J14"
                f = next(x for x in children(q, "footprint") if review.reference(x) == ref)
                first(f, "at")[1] = "0"
            elif kind == "via":
                first(children(q, "via")[0], "at")[1] = "0"
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

    def test_current_native_pin_rotation_flood_and_source_proofs(self):
        r = review.run(write=False)
        self.assertTrue(r["actual_source_output_flood_connectivity_all4_active_layers"])
        self.assertFalse(r["source_to_load_PDN_solved"])

    def test_source_tree_keeps_reserve_and_unknown_returns(self):
        r = json.load(open(ROOT / "generated/fanout-ledger.json"))
        self.assertAlmostEqual(sum(r["input_positive_allocation_a"].values()), 2.4)
        self.assertEqual(r["input_positive_allocation_a"]["reserve_unassigned"], 0.416)
        self.assertFalse(r["reserve_assigned_load_or_connector"])
        self.assertEqual([x["positive_current_allocation_a"] for x in r["new_private_wires"]], [0.14, 0.08])
        self.assertTrue(
            all(
                x["route_length_mm"] is None and not x["joint_or_current_qualified"]
                for x in r["new_private_wires"]
            )
        )
        self.assertEqual(r["source_pcb_sha256"], review.sha(ROOT / "processor_carrier.kicad_pcb"))
        self.assertEqual(r["native_netlist_sha256"], review.sha(ROOT / "generated/netlist.xml"))


if __name__ == "__main__":
    unittest.main()
