import copy
import json
import unittest
from pathlib import Path

from .review import errors

ROOT = Path(__file__).resolve().parent


class MountAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "report.json").read_text())

    def mutated(self):
        return copy.deepcopy(self.data)

    def test_saved_source_bound_map(self):
        self.assertEqual(errors(self.data), [])

    def test_low_processor_cannot_be_lifted_silently(self):
        d = self.mutated()
        r = next(r for r in d["boards"] if r["id"] == "dsp_carrier")
        r["translation_xyz_mm"] = [0, 0, 7.6]
        self.assertTrue(errors(d))

    def test_unresolved_touch_controller_cannot_be_asserted_fixed(self):
        d = self.mutated()
        r = next(r for r in d["boards"] if r["id"] == "trill_craft")
        r["translation_xyz_mm"] = [0, 0, 0]
        self.assertTrue(errors(d))

    def test_omitted_envelope_rejected(self):
        d = self.mutated()
        d["envelopes"].pop()
        self.assertTrue(errors(d))

    def test_sensor_must_follow_lever(self):
        d = self.mutated()
        r = next(r for r in d["envelopes"] if r["id"] == "angle_sensor")
        r["translation_xyz_mm"] = [0, 0, 0]
        self.assertTrue(errors(d))

    def test_lever_post_cannot_stay_low(self):
        d = self.mutated()
        r = next(r for r in d["board_mounts"] if r["id"] == "lever")
        r["candidate"][3] = 7
        self.assertTrue(errors(d))

    def test_controlled_lead_projection_cannot_shrink(self):
        d = self.mutated()
        r = next(r for r in d["panel_modules"] if r["id"] == "a12_switch_electronics")
        r["lead_solder_z_mm"][1][0] += 0.5
        self.assertTrue(errors(d))

    def test_bad_source_hash_rejected(self):
        d = self.mutated()
        d["source_sha256"][next(iter(d["source_sha256"]))] = "0" * 64
        self.assertTrue(errors(d))

    def test_qualified_claim_rejected(self):
        d = self.mutated()
        d["physical_qualified"] = True
        self.assertTrue(errors(d))

    def test_fixed_lever_new_panel_witness_is_inside_stem_and_outside_slot(self):
        import math

        w = self.data["lever_group"]["fixed_lever_new_panel_analytic_interference_witness"]
        x, y, z = w["world_point_mm"]
        a = math.radians(w["angle_degrees"])
        self.assertAlmostEqual((z - 24) / math.cos(a), w["local_stem_point_mm"][2])
        self.assertLess(w["local_stem_point_mm"][2], 24)
        self.assertGreater(y, 95)
        self.assertGreater(z, 43.6)
        self.assertLess(z, 45.6)
        self.assertEqual(x, 316)


if __name__ == "__main__":
    unittest.main()
