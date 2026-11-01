import copy
import importlib.util
import json
import math
import unittest

from validate import ROOT, validate


class CoarsePDN(unittest.TestCase):
    def test_actual_coarse_evidence_and_negative_mutations(self):
        r = json.loads((ROOT / "generated/coarse.json").read_text())
        validate(r)
        for name in ["sourceface", "double_nested", "reserve_as_known", "KCL", "physical"]:
            q = copy.deepcopy(r)
            if name == "sourceface":
                q["above_board_source_face"] = "B.Cu"
            elif name == "double_nested":
                q["fixture_corners"][0]["ground_fixture_injections_a"]["U1.20"] = 1.0
            elif name == "reserve_as_known":
                q["known_positive_total_a"] = 2.4
            elif name == "KCL":
                q["networks"]["AGND"]["max_absolute_kcl_residual_a"] = 1e-3
            else:
                q["physical_qualified"] = True
            with self.assertRaises(AssertionError, msg=name):
                validate(q, check_files=False)

    def test_outward_ports_and_unnetted_hole_capture(self):
        r = json.loads((ROOT / "generated/coarse.json").read_text())
        pads = json.loads((ROOT / "generated/pads.json").read_text())
        self.assertTrue(pads["unnetted_NPTH_pads_included_for_hole_voids"])
        self.assertTrue(
            any(p["ref"] == "H9" and not p["net"] and p["drill_mm"] == [2.4, 2.4] for p in pads["pads"])
        )
        self.assertEqual(r["networks"]["5V_DIG"]["source_face"], ["J13.1", "F.Cu"])
        self.assertEqual(r["networks"]["AGND"]["source_face"], ["J13.2", "F.Cu"])
        self.assertNotIn("J1.2", r["networks"]["AGND"]["drive_faces"])

    def test_actual_selected_R1_and_new_force_wall_capture(self):
        r = json.loads((ROOT / "generated/coarse.json").read_text())
        pads = json.loads((ROOT / "generated/pads.json").read_text())["pads"]
        selected = {p["pin"]: p for p in pads if p["ref"] == "R1"}
        self.assertEqual(selected["1"]["position_mm"], [180.0, 142.855])
        self.assertEqual(selected["2"]["position_mm"], [180.0, 137.145])
        self.assertTrue(all(p["size_mm"] == [1.65, 3.68] for p in selected.values()))
        self.assertEqual(r["networks"]["SEED_VIN"]["finite_physical_barrels"], 6)
        self.assertTrue(all(n["all_native_drill_voids"] == 270 for n in r["networks"].values()))

    @unittest.skipUnless(
        importlib.util.find_spec("scipy"), "optional tiny finite-wall equation control needsSciPy"
    )
    def test_isolated_real_annulus_has_finite_wall_resistance(self):
        from mesh import Mesh, response

        from hardware.electronics.common.sexpr import children, read_sexpr

        root = (
            ROOT
            / "sources/hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1/generated/filled.kicad_pcb"
        )
        original = read_sexpr(root.read_text())
        tree = ["kicad_pcb"] + [q for q in children(original, "gr_line") if q[0] == "gr_line"]
        pads = json.loads((ROOT / "generated/pads.json").read_text())
        p = copy.deepcopy(next(p for p in pads["pads"] if p["ref"] == "J13" and p["pin"] == "1"))
        p["ref"] = "CONTROL"
        m = Mesh(tree, {"pads": [p]}, "5V_DIG", 0.2)
        resistance = []
        for temp in [20, 100]:
            n = m.network([0.07] * 4, [0.035, 0.285, 1.315, 1.565], wall_mm=0.025, temp=temp)
            r = response(
                n, ("CONTROL.1", "F.Cu"), {"bottom": ("CONTROL.1", "B.Cu")}, {"bottom": ("CONTROL.1", "B.Cu")}
            )
            resistance.append(r["transfer_resistance_ohm"]["bottom"]["bottom"])
        bore = 1.1
        wall = 0.025
        axial = 2e-5 * 1.53 / (math.pi * ((bore + wall) ** 2 - bore**2))
        self.assertGreaterEqual(resistance[0], axial * (1 - 1e-6))
        self.assertLess(resistance[0], 2 * axial)
        self.assertAlmostEqual(resistance[1] / resistance[0], 1 + 0.00393 * 80, places=8)


if __name__ == "__main__":
    unittest.main()
