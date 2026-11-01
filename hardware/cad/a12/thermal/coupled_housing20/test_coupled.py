import copy
import importlib.util
import json
import unittest

from .validate import ROOT, validate


class CoupledControls(unittest.TestCase):
    def test_actual_source_controls_and_geometry(self):
        validate(json.load(open(ROOT / "generated/analysis.json")))

    def test_false_acceptance_and_contact_geometry_mutations(self):
        r = json.load(open(ROOT / "generated/analysis.json"))
        for kind in [
            "physical",
            "uniformbase",
            "cassettebridge",
            "cellshort",
            "contactdouble",
            "stressupper",
        ]:
            q = copy.deepcopy(r)
            if kind == "physical":
                q["thermal_qualified"] = True
            elif kind == "uniformbase":
                q["prescribed_uniform_base_temperature"] = True
            elif kind == "cassettebridge":
                q["geometry"]["rear_cassette_bridge_credited"] = True
            elif kind == "cellshort":
                q["geometry"]["no_link_between_separate_same_cell_components"] = False
            elif kind == "contactdouble":
                q["loaded_cases"][0]["result"]["contact_pure_conductance_w_per_k"]["wall_lid"] *= 2
            else:
                q["stress_is_planning_diagnostic_not_measured_upper"] = False
            with self.assertRaises(AssertionError, msg=kind):
                validate(q, check_files=False)

    def test_contact_subdivision_preserves_pure_conductance(self):
        r = json.load(open(ROOT / "generated/analysis.json"))
        A = r["geometry"]["contact_area_mm2"]
        P = r["geometry"]["base_contact_length_mm"]
        for total in [A, P]:
            parts = [0.13 * total, 0.27 * total, 0.6 * total]
            for R in [0.1, 0.2]:
                g = sum(1 / (R * total / a) for a in parts)
                split = [x * f for x in parts for f in [0.23, 0.77]]
                self.assertAlmostEqual(g, 1 / R, places=12)
                self.assertAlmostEqual(sum(1 / (R * total / a) for a in split), g, places=12)

    @unittest.skipUnless(
        importlib.util.find_spec("shapely"), "optional planar-component equation control needsShapely"
    )
    def test_separate_same_cell_pieces_are_not_unioned_across_aperture(self):
        from shapely.geometry import box

        from .geometry import polygons

        cut = box(0, 0, 4, 2).difference(box(1, -1, 3, 3))
        parts = polygons(cut)
        self.assertEqual(len(parts), 2)
        self.assertEqual(sum(x.area for x in parts), 4)
        self.assertTrue(parts[0].intersection(parts[1]).is_empty)


if __name__ == "__main__":
    unittest.main()
