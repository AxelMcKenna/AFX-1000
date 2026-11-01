import copy
import json
import unittest

from analyze import power_rating, resistor_interval
from validate import ROOT, validate


class SeedBudget(unittest.TestCase):
    def test_source_native_geometry_and_no_false_acceptance(self):
        e = json.loads((ROOT / "generated/endpoint-R1.json").read_text())
        m = json.loads((ROOT / "generated/Seed3-applicability.json").read_text())
        validate(e, m)
        for name in [
            "half_load",
            "generic1W",
            "unknown_ground_zero",
            "complete_pass",
            "full_case_gap",
            "only_U1_control_missing",
            "wrong_hole",
            "wrong_PIN40",
        ]:
            a, b = copy.deepcopy(e), copy.deepcopy(m)
            if name == "half_load":
                next(r for r in a["R1_candidates"] if r["mpn"] == "WSLT2512R4700FEA")["load_a"] = 0.5
            elif name == "generic1W":
                next(r for r in a["R1_candidates"] if r["mpn"] == "WSLT2512R4700FEA")[
                    "manufacturer_P70_after_high_R_derating_w"
                ] = 1
            elif name == "unknown_ground_zero":
                a["complete_source_to_Seed_guaranteed_interval_v"] = [4.39, 5.09]
            elif name == "complete_pass":
                a["physical_qualified"] = True
            elif name == "full_case_gap":
                b["controls"]["outside_complete_existing_reserve_mm3"] = 0.01
            elif name == "only_U1_control_missing":
                b["controls"]["outside_U1_box_only_positive_witness_mm3"] = 0
            elif name == "wrong_hole":
                b["pads"][0]["step_nominal_grid_difference_mm"] = 0.1
            else:
                b["CSV_pin40_DAISY_name_PG3_disagrees_with_PDF_DGND_but_primary_function_GND"] = False
            with self.assertRaises(AssertionError, msg=name):
                validate(a, b, files=False)

    def test_actual_resistance_and_both_derating_factors(self):
        self.assertAlmostEqual(power_rating(0.47, 70, 170), 0.815)
        self.assertAlmostEqual(power_rating(0.47, 100, 170), 0.5705)
        self.assertAlmostEqual(power_rating(0.47, 125, 275), 0.815 * 150 / 205)
        r = resistor_interval(0.47)[1]
        self.assertLess(power_rating(0.47, 100, 170), 1.2 * r)
        self.assertGreater(power_rating(0.47, 125, 275), 1.2 * r)
        self.assertAlmostEqual(resistor_interval(0.47)[1], 0.48615625)


if __name__ == "__main__":
    unittest.main()
