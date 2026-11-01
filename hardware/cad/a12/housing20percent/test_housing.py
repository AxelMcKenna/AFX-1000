import copy
import json
import unittest

from .plan import ROOT, geometry
from .validate import validate


class H20Controls(unittest.TestCase):
    def test_exact_envelopes(self):
        a = geometry(334, 157, 38)
        b = geometry(334, 188.4, 45.6)
        self.assertEqual(str(b["floor_mm2"] / a["floor_mm2"]), "6/5")
        self.assertEqual(str(b["box_volume_mm3"] / a["box_volume_mm3"]), "36/25")
        self.assertEqual(str(b["box_outer_area_mm2"] / a["box_outer_area_mm2"]), "542169/444350")
        p = json.loads((ROOT / "dimensions.json").read_text())
        self.assertEqual(p["added_strip_world_xy"], [0, 157, 334, 188.4])
        self.assertFalse(p["all_control_PCB_mounts_or_shaft_contracts_closed"])
        self.assertEqual(p["candidate_shell_fasteners_xy"][-3:], [[8, 180.4], [167, 180.4], [326, 180.4]])

    def test_actual_model_controls_and_source_freshness(self):
        validate(json.loads((ROOT / "generated/thermal.json").read_text()))

    def test_false_acceptance_and_numerical_failure_mutations(self):
        r = json.loads((ROOT / "generated/thermal.json").read_text())
        for mutation in ["physical", "installed_h", "heat", "energy", "old_equations", "invented_front_fins"]:
            q = copy.deepcopy(r)
            if mutation == "physical":
                q["thermal_qualified"] = True
            elif mutation == "installed_h":
                q["installed_h_lower_bound"] = 3
            elif mutation == "heat":
                q["heat_target_w"] *= 0.8
            elif mutation == "energy":
                q["enlarged_base_cases"][0]["result"]["energy_balance_residual_w"] = 0.1
            elif mutation == "old_equations":
                q["FF02_baseline_lid_replay_delta_w"] = 0.5
            else:
                q["new_metal_shell_prescribed_base_cases"][0]["old_FF02_fins_XY_unchanged_no_front_fins"] = (
                    False
                )
            with self.assertRaises(AssertionError, msg=mutation):
                validate(q, check_files=False)


if __name__ == "__main__":
    unittest.main()
