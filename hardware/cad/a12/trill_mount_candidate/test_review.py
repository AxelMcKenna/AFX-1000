import copy
import json
import unittest
from pathlib import Path

from .review import errors

ROOT = Path(__file__).resolve().parent


class Candidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / "report.json").read_text())
        cls.native = json.loads((ROOT / "generated/verification.json").read_text())

    def test_exact_saved_packet(self):
        self.assertEqual(errors(self.report, self.native), [])

    def test_backer_internal_translation_included(self):
        text = (ROOT / "sources/hardware/cad/a11/controls.scad").read_text()
        self.assertIn("translate([0,0,panel_z-34])", text)
        self.assertIn("translate([70,120,32.6])", text)
        self.assertAlmostEqual(32.6 + 43.6 - 34, self.report["design"]["upper_mating_z_mm"])

    def test_old_outline_rejected(self):
        r = copy.deepcopy(self.report)
        r["actual_width_depth_mm"] = [52, 21]
        self.assertTrue(errors(r, self.native))

    def test_grounded_mount_assumption_rejected(self):
        r = copy.deepcopy(self.report)
        r["mounts"][0]["net"] = "GND"
        self.assertTrue(errors(r, self.native))

    def test_short_posts_rejected(self):
        r = copy.deepcopy(self.report)
        r["design"]["upper_mating_z_mm"] = 40.2
        self.assertTrue(errors(r, self.native))

    def test_pin_swap_rejected(self):
        r = copy.deepcopy(self.report)
        r["communication_pads"][4]["net"] = "/I2C_SCL"
        self.assertTrue(errors(r, self.native))

    def test_missing_saddle_cannot_be_empty_pass(self):
        n = copy.deepcopy(self.native)
        n["cases"]["saddle"]["statistics"] = None
        n["cases"]["saddle"]["empty"] = True
        self.assertTrue(errors(self.report, n))

    def test_forged_empty_collision_row_with_actual_control_mesh(self):
        n = copy.deepcopy(self.native)
        n["cases"]["known_board_collision"]["role"] = "empty"
        n["cases"]["known_board_collision"]["empty"] = True
        n["cases"]["known_board_collision"]["returncode"] = 1
        self.assertTrue(errors(self.report, n))

    def test_failed_contact_not_accepted(self):
        n = copy.deepcopy(self.native)
        n["cases"]["backer_contact"]["clear"] = False
        self.assertTrue(errors(self.report, n))

    def test_physical_claim_rejected(self):
        r = copy.deepcopy(self.report)
        r["physical_qualified"] = True
        self.assertTrue(errors(r, self.native))


if __name__ == "__main__":
    unittest.main()
