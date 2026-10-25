"""Fit-kit coverage, pending measurements and strict contact/source evidence."""

import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a11.generate import schedule
from hardware.cad.a11_fitkit import build

try:
    import trimesh
except ImportError:
    trimesh = None


class FitKitContractTests(unittest.TestCase):
    def test_stations_cover_every_original_holder_pattern_and_actual_sector(self):
        buttons, _ = schedule()
        chosen = [b for b in buttons if b[0] in build.STATIONS]

        def pattern(b):
            return tuple(tuple(p) for p in b[8])

        self.assertEqual(len(chosen), 5)
        self.assertEqual({pattern(b) for b in chosen}, {pattern(b) for b in buttons})
        self.assertEqual(sum(b[1] == "sector" for b in chosen), 1)

    def test_quantity_inventory_includes_each_station_and_knob_variant(self):
        parts = build.inventory()
        self.assertEqual(len(parts), 30)
        self.assertEqual(sum(p["quantity"] for p in parts), 38)
        self.assertEqual(len({p["name"] for p in parts}), len(parts))
        for station in build.STATIONS:
            self.assertEqual(
                {p["part"] for p in parts if p["name"].startswith(station + "-")},
                {"key", "holder", "panel", "guide"},
            )
        self.assertEqual(
            {p["name"] for p in parts if p["part"] == "knob"},
            {"knob-16x13", "knob-17x15", "knob-29x18", "knob-32x18"},
        )
        self.assertEqual(next(p["quantity"] for p in parts if p["part"] == "clip"), 8)

    def test_measurements_are_unperformed_and_hardware_quantities_match(self):
        with (build.ROOT / "MEASUREMENTS.csv").open(newline="") as stream:
            measurements = list(csv.DictReader(stream))
        self.assertEqual(len(measurements), 46)
        self.assertTrue(
            all(r["Result"] == "PENDING" and not r["Measured"] and not r["Reviewer"] for r in measurements)
        )
        with (build.ROOT / "PURCHASED.csv").open(newline="") as stream:
            purchased = {r["Item"]: int(r["Quantity_for_trial"]) for r in csv.DictReader(stream)}
        self.assertEqual(purchased["Tactile switch"], 5)
        self.assertEqual(purchased["M2 countersunk holder screw"], 10)
        self.assertEqual(purchased["Button return spring"], 5)

    def test_source_fingerprint_rejects_content_changes_even_with_same_name(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            path = repo / "fixture.scad"
            path.write_text("original geometry")
            record = {"source_sha256": {"fixture.scad": hashlib.sha256(path.read_bytes()).hexdigest()}}
            build.verify_sources(record, repo)
            path.write_text("changed geometry")
            with self.assertRaisesRegex(AssertionError, "Stale fit-kit source"):
                build.verify_sources(record, repo)


@unittest.skipUnless(trimesh is not None, "Requires A11 CAD Python dependencies")
class FitKitContactTests(unittest.TestCase):
    def inspect(self, mesh):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contact.stl"
            mesh.export(path)
            return build.inspect_contact(path, -1.4, [(-2.1, -2.1, 4.2, 4.2)])

    @staticmethod
    def plane(x=0, z=-1.4):
        return trimesh.Trimesh(
            vertices=[(x - 1, -1, z), (x + 1, -1, z), (x + 1, 1, z), (x - 1, 1, z)],
            faces=[(0, 1, 2), (0, 2, 3)],
            process=False,
        )

    def test_only_named_zero_depth_seats_are_accepted(self):
        record = self.inspect(self.plane())
        self.assertEqual(record["result"], "intended planar seating only")
        self.assertLessEqual(record["maximum_plane_deviation_mm"], 1e-5)

    def test_positive_depth_or_displaced_planar_contact_is_rejected(self):
        solid = trimesh.creation.box(extents=(1, 1, 0.001))
        solid.apply_translation((0, 0, -1.4))
        for mesh in [solid, self.plane(x=8), self.plane(z=-1.399)]:
            with self.assertRaises(AssertionError):
                self.inspect(mesh)


if __name__ == "__main__":
    unittest.main()
