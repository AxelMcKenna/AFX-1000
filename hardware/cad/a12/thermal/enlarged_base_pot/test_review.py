"""CP01 mutations cover real saved meshes and sealed capture/replay guards."""

import copy
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .assembly import NS
from .audit import assembly_errors, errors, model_errors
from .replay import prepare_rebind
from .stage import OUT, ROOT, closure, guard_capture, sha
from .verify import guard_output, row_errors


class CombinedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((OUT / "verification.json").read_text())
        cls.spec = json.loads((OUT / "cases.json").read_text())
        cls.cfg = json.loads((OUT / "config.json").read_text())
        cls.err = json.loads((ROOT / "EB01-erratum.json").read_text())

    def test_actual_whole_packet_reintegrates(self):
        self.assertEqual(errors(), [])

    def test_sealed_capture_refused_before_any_writes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "handoff.json").write_text("{}")
            before = sha(p / "handoff.json")
            with self.assertRaises(RuntimeError):
                guard_capture(p)
            self.assertEqual(sha(p / "handoff.json"), before)
            self.assertEqual({q.name for q in p.iterdir()}, {"handoff.json"})

    def test_unsealed_existing_capture_also_not_recaptured(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "capture.json").write_text("{}")
            with self.assertRaises(RuntimeError):
                guard_capture(p)

    def test_native_output_cannot_overwrite_sealed_packet(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "handoff.json").write_text("{}")
            with self.assertRaises(RuntimeError):
                guard_output(p / "generated", p)

    def test_existing_replay_receipt_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "verification.json").write_text("{}")
            with self.assertRaises(RuntimeError):
                guard_output(p)

    def test_rebind_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                prepare_rebind(td)

    def test_captured_rebind_is_closed_and_preserves_originals(self):
        c = json.loads((ROOT / "capture.json").read_text())
        before = {n: sha(ROOT / n) for n in c["derived_context_sha256"]}
        with tempfile.TemporaryDirectory() as td:
            dest = prepare_rebind(Path(td) / "fresh")
            for p in [dest / "context-derived.scad", *(dest / "context").rglob("*.scad")]:
                self.assertTrue(all(q.is_relative_to(dest) for q in closure(p)))
        self.assertEqual(before, {n: sha(ROOT / n) for n in before})

    def test_old_full_available_thread_gauge_is_rejected(self):
        model = (
            (OUT / "context-derived.scad")
            .read_text()
            .replace("-12.00002])cylinder(d=3.02,h=5.80004", "-16.2])cylinder(d=3.02,h=10.00002")
        )
        self.assertTrue(model_errors(model, self.cfg, self.err))

    def test_old_panel_bore_is_rejected(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["openings"][0][4:6] = [9.3, 9.3]
        self.assertTrue(model_errors((OUT / "context-derived.scad").read_text(), cfg, self.err))

    def test_absent_new_knob_part_does_not_pass(self):
        n = "ps_knob_0"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / (n + ".log")).write_text("Status: NoError\n")
            self.assertTrue(row_errors(n, self.r["cases"][n], self.spec[n], p))

    def test_forged_empty_cannot_hide_actual_collision_mesh(self):
        n = "cp_body_base_all_collision"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            shutil.copyfile(OUT / "cp_body_interface_positive_control.stl", p / (n + ".stl"))
            (p / (n + ".log")).write_text("Current top level object is empty.\n")
            self.assertTrue(row_errors(n, dict(returncode=1, statistics=None), self.spec[n], p))

    def test_forged_native_volume_cannot_replace_real_mesh(self):
        n = "ps_panel_geometry"
        row = copy.deepcopy(self.r["cases"][n])
        row["statistics"]["volume_mm3"] += 1
        self.assertTrue(row_errors(n, row, self.spec[n], OUT))

    def test_coordinate_deleted_from_complete_review_is_rejected(self):
        source = OUT / "CP01-whole-unit-component-review.3mf"
        a = json.loads((OUT / "assembly-manifest.json").read_text())
        with zipfile.ZipFile(source) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        model = ET.fromstring(entries["3D/3dmodel.model"])
        resources = model.find(f"{{{NS}}}resources")
        resources.remove(resources.find(f"{{{NS}}}object"))
        entries["3D/3dmodel.model"] = ET.tostring(model)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "missing.3mf"
            with zipfile.ZipFile(target, "w") as z:
                for n, b in entries.items():
                    z.writestr(n, b)
            self.assertTrue(assembly_errors(a, target))


if __name__ == "__main__":
    unittest.main()
