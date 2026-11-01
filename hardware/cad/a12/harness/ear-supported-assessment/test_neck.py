"""Native geometry controls, actual-source checks and negative mutations."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("neck", ROOT / "native_neck.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


def validate(report):
    assert report["source_filled_pcb_sha256"] == n.sha(n.PCB)
    assert report["source_code_sha256"] == n.sha(ROOT / "native_neck.py")
    expected = {("F.Cu", "5V_DIG"), ("In1.Cu", "AGND"), ("In2.Cu", "5V_DIG"), ("B.Cu", "5V_DIG")}
    active = [r for r in report["rows"] if r["centre_line_actual_copper"]["total_width_mm"] > 0]
    assert {(r["layer"], r["net"]) for r in active} == expected
    for r in active:
        assert r["probes_connected_before_cut"]
        assert not r["probes_connected_after_cut"]
        assert 0.77 < r["centre_line_actual_copper"]["total_width_mm"] < 0.79
    assert {(r["ref"], r["pin"]) for r in report["actual_5V_DIG_pad_nodes"]} == {
        ("J1", "1"),
        ("J13", "1"),
        ("J11", "2"),
        ("R1", "1"),
    }
    assert not report["full_PDN_solved"] and not report["physical_qualified"]


class NativeNeck(unittest.TestCase):
    def test_actual_source_and_negative_mutations(self):
        r = json.loads((ROOT / "generated/native-neck.json").read_text())
        validate(r)
        for mutation in ["stale", "bypass", "missing_ground", "invented_port"]:
            q = copy.deepcopy(r)
            if mutation == "stale":
                q["source_filled_pcb_sha256"] = "0" * 64
            elif mutation == "bypass":
                q["rows"][0]["probes_connected_after_cut"] = True
            elif mutation == "missing_ground":
                q["rows"] = [x for x in q["rows"] if x["layer"] != "In1.Cu"]
            else:
                q["actual_5V_DIG_pad_nodes"].append({"ref": "J99", "pin": "1"})
            with self.assertRaises(AssertionError, msg=mutation):
                validate(q)

    def test_native_hole_parity_and_cut_controls(self):
        p = n.polygon([(0, 0), (10, 0), (10, 4), (0, 4)])
        p.BooleanSubtract(n.polygon([(4, 1), (6, 1), (6, 3), (4, 3)]))
        s = n.cross_section(p, (0, 2), (1, 0), 0, 10)
        self.assertEqual(s["intervals_mm"], [[0, 4.0], [6.0, 10]])
        self.assertEqual(s["total_width_mm"], 8)
        self.assertTrue(set(n.component(p, (1, 2))) & set(n.component(p, (9, 2))))
        p.BooleanSubtract(n.polygon([(4.999, 0), (5.001, 0), (5.001, 4), (4.999, 4)]))
        self.assertFalse(set(n.component(p, (1, 2))) & set(n.component(p, (9, 2))))
        self.assertFalse(n.component(p, (5, 2)))
        self.assertEqual(p.OutlineCount(), 2)
        self.assertIsInstance(p, pcbnew.SHAPE_POLY_SET)


if __name__ == "__main__":
    unittest.main()
