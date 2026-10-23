"""Mounting contact recognition must never hide a real CAD penetration."""

import tempfile
import unittest
from pathlib import Path

try:
    import trimesh
except ImportError:
    trimesh = None

from hardware.cad.render import check_mounting_faces


@unittest.skipUnless(trimesh is not None, "Requires hardware/cad/requirements.txt")
class MountingContactTests(unittest.TestCase):
    region = [("spacer_landing", 113, 64, 8.1, 5.5)]

    def inspect(self, mesh):
        with tempfile.TemporaryDirectory(prefix="rmx-contact-test-") as temp:
            path = Path(temp) / "intersection.stl"
            mesh.export(path)
            return check_mounting_faces(path, self.region)

    @staticmethod
    def contact(x=113, z=8.1):
        return trimesh.Trimesh(
            vertices=[(x - 1, 63, z), (x + 1, 63, z), (x + 1, 65, z), (x - 1, 65, z)],
            faces=[(0, 1, 2), (0, 2, 3)],
            process=False,
        )

    def test_nominal_mounting_face_survives_stl_rounding(self):
        report = self.inspect(self.contact())
        self.assertEqual(report["contact_faces"], ["spacer_landing"])
        self.assertLess(report["maximum_plane_deviation_mm"], 1e-5)

    def test_positive_depth_penetration_is_rejected(self):
        box = trimesh.creation.box(extents=(1, 1, 0.05))
        box.apply_translation((113, 64, 8.125))
        with self.assertRaises(RuntimeError):
            self.inspect(box)

    def test_plane_contact_outside_fixing_footprint_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.inspect(self.contact(x=125))

    def test_contact_at_an_unapproved_height_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.inspect(self.contact(z=8.101))

    def test_real_penetration_is_rejected_alongside_a_valid_contact(self):
        box = trimesh.creation.box(extents=(1, 1, 0.05))
        box.apply_translation((113, 64, 8.125))
        with self.assertRaises(RuntimeError):
            self.inspect(trimesh.util.concatenate([self.contact(), box]))


if __name__ == "__main__":
    unittest.main()
