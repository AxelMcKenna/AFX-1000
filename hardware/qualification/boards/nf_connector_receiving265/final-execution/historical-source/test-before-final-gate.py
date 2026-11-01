"""Portable source, pad, mesh, guard and interface-mutation checks."""

import copy
import json
import math
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from hardware.qualification.boards.nf_connector_receiving265 import (
    audit,
    facet_audit,
    proposal,
    revision2,
    verify_mechanics,
)

ROOT = Path(__file__).resolve().parent


class Receiving265(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ports = json.loads((ROOT / "ports-v2.json").read_text())
        cls.native = ROOT / "mechanical-v2/native-run1"
        cls.guards = ROOT / "mechanical-v2/native-guards"

    def test_all_captured_sources_actual_artifacts_and_native_pins(self):
        self.assertEqual(audit.checks(), [])

    def test_actual265_NC_and_output_only_contract_reject_wrong_net(self):
        parts = json.loads((ROOT / "inputs/NF265/components.json").read_text())
        nets = proposal.native_net_contract(parts)
        self.assertIsNone(nets["J1"]["4"])
        self.assertEqual(nets["J1"]["7"], "ABS_AUX_FAULT")
        self.assertEqual(nets["J6"]["2"], "MODULE_INPUT_GND")
        changed = copy.deepcopy(parts)
        next(p for p in next(q for q in changed if q["ref"] == "J1")["pins"] if p["number"] == "7")["net"] = (
            "RESET_REQUEST"
        )
        with self.assertRaises(ValueError):
            proposal.native_net_contract(changed)

    def test_overlay_moves_only_real_J4_and_real_holes(self):
        self.assertEqual(revision2.revised(), self.ports)
        old = json.loads((ROOT / "ports.json").read_text())
        a = {p["ref"]: p for p in old["ports"]}
        b = {p["ref"]: p for p in self.ports["ports"]}
        self.assertEqual(a["J4"]["anchor_mm"], [78, 21])
        self.assertEqual(b["J4"]["anchor_mm"], [79, 21])
        self.assertTrue(all(a[r] == b[r] for r in a if r != "J4"))
        self.assertTrue(
            all(
                h["drill_mm"] == 2.6 and h["finished_minimum_diameter_receiving_mm"] == 2.5
                for h in self.ports["force_shared_strain_candidate"]["PCB_mount_holes"]
            )
        )

    def test_serialized_source_pad_geometry_and_electrical_maps(self):
        actual = audit.current_physical_pads()
        self.assertEqual(sum(len(actual[r]) for r in ["J1", "J2", "J3", "J4", "J5", "J6"]), 40)
        self.assertEqual(actual["J1"]["1"]["at_mm"], [5, 17.5])
        self.assertEqual(actual["J1"]["30"]["at_mm"], [33, 19.5])
        self.assertEqual(actual["J4"]["1"]["at_mm"], [79, 21])
        self.assertEqual(actual["J4"]["2"]["at_mm"], [84, 21])
        self.assertEqual(actual["J6"]["2"]["at_mm"], [125.5, 17.5])
        self.assertEqual(actual["J4"]["1"]["drill_mm"], 2.2)

    def test_real_native_copper_intrusions_rejected(self):
        base = json.loads((ROOT / "prototype-v3/drc.json").read_text())
        self.assertEqual(base["violations"], [])
        self.assertEqual(base["unconnected_items"], [])
        for name, kind in [
            ("foreign_copper_inside_NPTH", "hole_clearance"),
            ("foreign_copper_in_strain_annulus", "items_not_allowed"),
        ]:
            d = json.loads((ROOT / "prototype-v3" / (name + "-drc.json")).read_text())
            self.assertTrue(any(v["type"] == kind and v["severity"] == "error" for v in d["violations"]))

    def test_required_manufacturing_parts_are_closed_oriented_single_solids(self):
        d = json.loads((self.native / "verification.json").read_text())
        for name in ["base_part", "cap_part"]:
            r = d["cases"][name]
            self.assertEqual(audit.native_row_errors(name, r, self.native, "part"), [])
            m = verify_mechanics.mesh(self.native / (name + ".stl"))
            self.assertEqual(m["zero_area_triangles"], 0)
            self.assertEqual(m["connected_components"], 1)
            self.assertGreater(m["volume_mm3"], 0)

    def test_missing_required_solid_is_never_accepted(self):
        row = json.loads((self.native / "verification.json").read_text())["cases"]["base_part"]
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            shutil.copy(self.native / "base_part.log", p / "base_part.log")
            self.assertTrue(
                any(
                    "missing required nonempty STL" in e
                    for e in audit.native_row_errors("base_part", row, p, "part")
                )
            )

    def test_nonempty_actual_collision_cannot_be_forged_to_empty(self):
        name = "front_seats_guarded"
        row = copy.deepcopy(json.loads((self.guards / "verification.json").read_text())["cases"][name])
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            shutil.copy(self.guards / (name + ".log"), p / (name + ".log"))
            shutil.copy(self.native / "base_part.stl", p / (name + ".stl"))
            row["passed"] = True
            row["returncode"] = 1
            row["STL_sha256"] = None
            self.assertTrue(
                any("not actual strict empty" in e for e in audit.native_row_errors(name, row, p, "empty"))
            )

    def test_flipped_real_STL_triangle_is_rejected_by_oriented_edge_gate(self):
        source = self.native / "cap_part.stl"
        data = bytearray(source.read_bytes())
        row = list(struct.unpack_from("<12fH", data, 84))
        row[6:9], row[9:12] = row[9:12], row[6:9]
        struct.pack_into("<12fH", data, 84, *row)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "flipped.stl"
            p.write_bytes(data)
            self.assertFalse(verify_mechanics.mesh(p)["valid"])

    def test_one_convex_mask_per_triangle_rejects_gap_bridge(self):
        masks = facet_audit.masks("own_PCB_seats")
        tri = [(5, 18, 0), (60, 30, 0), (124, 18, 0)]
        self.assertTrue(all(any(facet_audit.vertex_inside(p, m) for m in masks) for p in tri))
        self.assertFalse(any(all(facet_audit.vertex_inside(p, m) for p in tri) for m in masks))
        d = json.loads((ROOT / "mechanical-v2/facet-boundary-audit.json").read_text())
        self.assertEqual(sum(x["triangles"] for x in d["cases"].values()), 9268)
        self.assertTrue(all(x["each_entire_triangle_inside_one_convex_mask"] for x in d["cases"].values()))

    def test_raw_failures_retained_and_five_thousand_nm_controls_survive(self):
        raw = json.loads((self.native / "verification.json").read_text())
        self.assertEqual(sum(bool(x["passed"]) for x in raw["cases"].values()), 14)
        self.assertFalse(raw["local_modeled_candidate_clear"])
        new = json.loads((self.guards / "verification.json").read_text())
        self.assertEqual(len(new["cases"]), 9)
        for name, row in new["cases"].items():
            self.assertEqual(audit.native_row_errors(name, row, self.guards, verify_guards_role(name)), [])
            if row["role"] == "control":
                self.assertGreater(row["mesh"]["volume_mm3"], 9e-6)

    def test_matched_thread_and_bore_receiving_arithmetic(self):
        d = json.loads((ROOT / "mechanical-v2/datums.json").read_text())
        h = d["hardware"]
        self.assertAlmostEqual(5 - 1.6 - 0.35, h["nominal_mount_thread_engagement_mm"])
        self.assertAlmostEqual(6 - 3.5 - 0.35, h["nominal_cap_thread_engagement_mm"])
        self.assertAlmostEqual((2.5 - 2) / 2 - 0.2 - 0.005, 0.045)
        self.assertLess((2.3 - 2) / 2 - 0.2 - 0.005, 0)
        self.assertAlmostEqual((2.1 - 1.4) / 2 - 0.3 - 0.005, 0.045)
        self.assertLess((1 - 1.4) / 2, 0)
        self.assertFalse(h["received_thread_engagement_torque_creep_and_repeated_service_qualified"])

    def test_29_actual_live_wire_isometry_and_continuous_cert_subset(self):
        d = json.loads((ROOT / "control-fanout.json").read_text())
        self.assertEqual(len(d["routes"]), 29)
        self.assertEqual(len(d["certificates"]), 406)
        self.assertNotIn(4, {r["circuit"] for r in d["routes"]})
        self.assertTrue(all(c["certified"] for c in d["certificates"].values()))
        self.assertGreaterEqual(d["radius_mm"], d["required_manufacturer_Rmin_mm"])
        p = d["routes"][0]["native_points_uvw_mm"]
        q = d["routes"][0]["world_points_mm"]

        def dist(a, b):
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

        self.assertAlmostEqual(dist(p[0], p[-1]), dist(q[0], q[-1]), places=12)
        self.assertFalse(d["actual_mate_wire_exit_plane_and_crimp_alignment_measured"])

    def test_analytical_BREP_matches_polygonal_native_part_with_declared_facet_error(self):
        d = json.loads((ROOT / "mechanical-v2/BREP/BREP.json").read_text())
        for name, p in d["parts"].items():
            self.assertTrue(p["valid"])
            self.assertEqual(p["solids"], 1)
            native = verify_mechanics.mesh(self.native / (name + "_part.stl"))
            self.assertLess(abs(native["volume_mm3"] - p["volume_mm3"]) / p["volume_mm3"], 1e-4)
        self.assertFalse(d["physical_qualified"])


def verify_guards_role(name):
    return "control" if name.endswith("_control") else "empty"


if __name__ == "__main__":
    unittest.main()
