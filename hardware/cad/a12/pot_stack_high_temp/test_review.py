"""Portable saved-native/source and independent tolerance mutations."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from .audit import contract_errors, control_bounds_errors, errors, native_errors
from .contract import report
from .stage import OUT, ROOT, capture
from .verify import errors as row_errors
from .verify import specifications
from .webs import aperture_gap, poly_gap


class Review(unittest.TestCase):
    def test_complete_actual_packet(self):
        self.assertEqual(errors(), [])

    def test_old_axis_rejected(self):
        d = report()
        d["receiving_requirements_not_manufacturer_guarantees"]["grub_axis_local"] = 3
        self.assertIn("grub-gauge-outside-allocated-flat", contract_errors(d))

    def test_old_depth_rejected_as_clearance_requirement(self):
        d = report()
        d["receiving_requirements_not_manufacturer_guarantees"]["blind_bore_depth"] = 10
        self.assertIn("less-than-required-tip-clearance", contract_errors(d))

    def test_shaft_length_not_from_panel_top(self):
        d = report()
        d["receiving_requirements_not_manufacturer_guarantees"]["shoulder_z"] = [45.5,45.7]
        self.assertIn("declared-axial-corner-does-not-match", contract_errors(d))

    def test_narrow_lug_pocket_rejected(self):
        d = report()
        d["receiving_requirements_not_manufacturer_guarantees"]["blind_lug_pocket_width"] = 2.2
        self.assertIn("lug-pocket-insufficient", contract_errors(d))

    def test_shallow_lug_pocket_rejected(self):
        d = report()
        d["receiving_requirements_not_manufacturer_guarantees"]["pocket_z"][1] = 44.3
        self.assertIn("lug-pocket-too-shallow", contract_errors(d))

    def test_claimed_supplier_or_physical_pass_rejected(self):
        d = report()
        d["source_facts"]["temperature_c"] = [-10,85]
        d["physical_qualified"] = True
        self.assertIn("manufacturer-constraint-lost", contract_errors(d))
        self.assertIn("unsupported-approval:physical_qualified", contract_errors(d))

    def test_coverage_missing_pair_rejected(self):
        d = json.loads((OUT / "full/verification.json").read_text())
        d["cases"].pop("hardware_8_family_4")
        self.assertIn("incomplete-or-reordered-native-coverage", native_errors(d, OUT / "full"))

    def test_wrong_native_family_rejected(self):
        d = json.loads((OUT / "full/verification.json").read_text())
        row = d["cases"]["hardware_5_family_4"]
        row["command"][row["command"].index("ht_family=4")] = "ht_family=3"
        self.assertIn("wrong-native-selector:hardware_5_family_4", native_errors(d, OUT / "full"))

    def test_forged_empty_with_actual_collision_mesh_rejected(self):
        d = json.loads((OUT / "full/verification.json").read_text())
        n = "new_panel_lug_collision"
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / (n + ".log")).write_text("Current top level object is empty.")
            (folder / (n + ".stl")).write_bytes((OUT / "full/old_panel_lug_collision_witness.stl").read_bytes())
            row = copy.deepcopy(d["cases"][n])
            row.update(returncode=1, statistics=None)
            self.assertIn("not-actual-empty", row_errors(n, row, specifications()[n], folder))

    def test_missing_required_part_rejected(self):
        d = json.loads((OUT / "full/verification.json").read_text())
        n = "substrate_geometry"
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / (n + ".log")).write_text("Current top level object is empty.")
            row = copy.deepcopy(d["cases"][n])
            row.update(returncode=1, statistics=None)
            self.assertIn("missing-actual-solid", row_errors(n, row, specifications()[n], folder))

    def test_existing_capture_refused(self):
        self.assertTrue((ROOT / "model").exists())
        with self.assertRaises(RuntimeError):
            capture()

    def test_sector_bounding_box_is_not_actual_aperture(self):
        sector=["scene_0","sector",244,78,35.6,51.4,208.7,230.5]
        self.assertGreater(aperture_gap([242.8,83.1,245.2,84.9],sector),25)

    def test_crossing_edges_without_contained_vertices(self):
        self.assertEqual(poly_gap([[-3,-1],[3,-1],[3,1],[-3,1]],[[-1,-3],[1,-3],[1,3],[-1,3]]),0)

    def test_equal_volume_control_from_wrong_pot_rejected(self):
        d = json.loads((OUT / "full/verification.json").read_text())
        self.assertEqual(control_bounds_errors("hardware_9_control",d["cases"]["hardware_9_control"]["statistics"]),[])
        self.assertIn("wrong-index-control-bounds:hardware_9_control",control_bounds_errors("hardware_9_control",d["cases"]["hardware_0_control"]["statistics"]))


if __name__ == "__main__":
    unittest.main()
