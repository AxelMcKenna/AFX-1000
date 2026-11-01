"""Portable saved-evidence and fail-closed mutation tests; no solver required."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from . import audit
from .capture import ROOT
from .escape_certificate import separation


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = ROOT / "generated"
        cls.model = json.loads((out / "coherent-receiving-model.json").read_text())
        cls.interface = json.loads((out / "interface-final.json").read_text())
        cls.delta = json.loads((out / "FPCClosed-C7-delta.json").read_text())
        cls.proof = json.loads((out / "native-mount5/verification.json").read_text())

    def test_actual_saved_evidence(self):
        result = audit.run()
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["all_receiving_interfaces_clear"])
        self.assertEqual(result["reports"]["robust_rear"]["effective_valid"], 32)
        self.assertEqual(result["reports"]["mounting"]["effective_valid"], 30)
        self.assertEqual(result["reports"]["wire_exits"]["effective_valid"], 9)

    def check_model_mutation(self, field, value, expected):
        d = copy.deepcopy(self.model)
        d[field] = value
        self.assertIn(expected, audit.model_errors(d, self.interface, self.delta))

    def test_missing_component_rejected(self):
        self.check_model_mutation(
            "component_records", self.model["component_records"][:-1], "incomplete-source-geometry"
        )

    def test_improper_frame_rejected(self):
        d = copy.deepcopy(self.model)
        d["boards"][0]["local_to_world_matrix"][1][2] = 1
        self.assertIn("wrong-frame", audit.model_errors(d, self.interface, self.delta))

    def test_old_rear_requirement_rejected(self):
        self.check_model_mutation("rear_THT_requirement_mm", 1.0, "wrong-rear-receiver")

    def test_rear_part_at_seat_rejected(self):
        d = copy.deepcopy(self.model)
        d["rear_tail_maximum_Z_mm"]["NF233_U1.1"] = 41.6
        self.assertIn("rear-parts-enter-upper-seat", audit.model_errors(d, self.interface, self.delta))

    def test_wrong_C7_height_rejected(self):
        d = copy.deepcopy(self.delta)
        d["new_body_projection_max_mm"] = 0.95
        self.assertIn("wrong-C7-delta", audit.model_errors(self.model, self.interface, d))

    def test_C7_protrusion_rejected(self):
        d = copy.deepcopy(self.delta)
        d["new_native_courtyard_mm"][0] = d["old_native_courtyard_mm"][0] - 0.01
        self.assertIn("C7-not-contained", audit.model_errors(self.model, self.interface, d))

    def test_unsupported_insulation_and_release_rejected(self):
        d = copy.deepcopy(self.interface)
        d["PCB_soldermask_insulation_credit"] = True
        d["physical_qualified"] = True
        errors = audit.model_errors(self.model, d, self.delta)
        self.assertIn("unsupported-insulation-credit", errors)
        self.assertIn("unsupported-release-flag", errors)

    def test_moved_clip_and_larger_guard_rejected(self):
        d = copy.deepcopy(self.interface)
        d["mounting"][0]["world_X"] += 1
        d["nominal_test_only_contact_guard_mm"] = 0.05
        errors = audit.model_errors(self.model, d, self.delta)
        self.assertIn("wrong-mount-datums", errors)
        self.assertIn("changed-guard-or-margin", errors)

    def test_missing_actual_required_part_rejected(self):
        n = "keeper_0"
        row = self.proof["cases"][n]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            shutil.copyfile(ROOT / "generated/native-mount5" / f"{n}.log", p / f"{n}.log")
            self.assertIn("missing-required-solid", audit.row_errors(n, row, {"role": "part"}, p))

    def test_real_collision_STL_cannot_be_forged_empty(self):
        n = "forged_collision"
        row = dict(role="empty", returncode=1, statistics=None)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / f"{n}.log").write_text("Current top level object is empty.\n")
            shutil.copyfile(ROOT / "generated/native-mount5/toe_positive_control.stl", p / f"{n}.stl")
            self.assertIn(
                "nonempty-collision-or-failed-execution", audit.row_errors(n, row, {"role": "empty"}, p)
            )

    def test_failed_execution_is_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "x.log").write_text("Container terminated137\n")
            self.assertIn(
                "nonempty-collision-or-failed-execution",
                audit.row_errors(
                    "x", dict(role="empty", returncode=137, statistics=None), {"role": "empty"}, p
                ),
            )

    def test_required_part_cannot_change_role(self):
        n = "toe_positive_control"
        row = copy.deepcopy(self.proof["cases"][n])
        row["role"] = "review"
        errors = audit.row_errors(
            n, row, {"role": "control", "expected_volume": 0.008}, ROOT / "generated/native-mount5"
        )
        self.assertIn("wrong-role", errors)

    def test_wrong_control_volume_detected(self):
        n = "toe_positive_control"
        errors = audit.row_errors(
            n,
            self.proof["cases"][n],
            {"role": "control", "expected_volume": 0.08},
            ROOT / "generated/native-mount5",
        )
        self.assertIn("wrong-control-volume", errors)

    def test_wrong_actual_statistics_detected(self):
        n = "toe_positive_control"
        row = copy.deepcopy(self.proof["cases"][n])
        row["statistics"]["volume_mm3"] = 0.08
        self.assertIn(
            "actual-STL-disagrees-with-row",
            audit.row_errors(n, row, {"role": "control"}, ROOT / "generated/native-mount5"),
        )

    def test_generic_PolySet_not_accepted(self):
        n = "toe_positive_control"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            shutil.copyfile(ROOT / "generated/native-mount5" / f"{n}.stl", p / f"{n}.stl")
            (p / f"{n}.log").write_text("Top level object is a 3D object (PolySet)\n")
            self.assertIn(
                "missing-NoError-or-named-primitive",
                audit.row_errors(n, self.proof["cases"][n], {"role": "control"}, p),
            )

    def test_stale_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x"
            p.write_text("a")
            h = audit.sha(p)
            p.write_text("b")
            self.assertEqual(audit.hash_errors({str(p): h}), [str(p)])

    def test_replay_cannot_overwrite_sealed_source(self):
        from .replay import destination

        with self.assertRaises(RuntimeError):
            destination(ROOT / "generated/new-output")

    def test_replay_cannot_reuse_existing_output(self):
        from .replay import destination

        with self.assertRaises(RuntimeError):
            destination(ROOT.parent)

    def test_continuous_local_wire_pair_and_contact_mutation(self):
        routes = json.loads((ROOT / "fpc_escape_variant2/contract.json").read_text())["routes"]
        cert = json.loads((ROOT / "fpc_escape_variant2/pair-certificate.json").read_text())
        self.assertTrue(
            separation(routes[0], routes[1], cert["required_pair_centerline_distance_mm"])["certified"]
        )
        self.assertFalse(
            separation(routes[0], routes[0], cert["required_pair_centerline_distance_mm"])["certified"]
        )

    def test_actual_closed_FPC_geometry_and_pinmap_delta(self):
        from .fpc_closed_delta import canonical, courtyard, packet

        a, an = packet(ROOT / "inputs/FPC84/fan_power_health.kicad_pcb")
        b, bn = packet(ROOT / "inputs/FPCClosed/fan_power_health.kicad_pcb")
        self.assertEqual(an, bn)
        self.assertEqual(set(a), set(b))
        self.assertEqual(len(a), 84)
        self.assertEqual([n for n in a if canonical(a[n]) != canonical(b[n])], ["C7"])
        old, new = courtyard(a["C7"], "F.CrtYd"), courtyard(b["C7"], "F.CrtYd")
        self.assertTrue(all(new[i] >= old[i] for i in [0, 1]) and all(new[i] <= old[i] for i in [2, 3]))


if __name__ == "__main__":
    unittest.main()
