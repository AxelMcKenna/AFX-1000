"""FI01 source/part/recovery mutations, portable without a native CAD engine."""

import copy
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import closure, guard_capture

from .assembly import NS
from .audit import component_errors, errors, pin_stack_errors, runtime_claim_errors
from .coverage import recovery_contract_errors
from .replay import prepare_rebind
from .stage import OUT, ROOT, sha
from .verify import guard_output, row_errors


class FI01Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = json.loads((OUT / "verification.json").read_text())
        cls.retry = json.loads((OUT / "retry-ps-hardware/verification.json").read_text())
        cls.split = json.loads((OUT / "hardware-split-v2/verification.json").read_text())
        cls.plan = json.loads((OUT / "hardware-split-plan-v2.json").read_text())
        cls.model = (OUT / "context-derived.scad").read_text()
        cls.pins = json.loads((OUT / "pin-datum.json").read_text())
        cls.stack = json.loads((ROOT / "FI01-stack.json").read_text())
        cls.specs = json.loads((OUT / "cases.json").read_text())

    def contract(self, main=None, retry=None, split=None, plan=None):
        return recovery_contract_errors(
            main or self.main, retry or self.retry, split or self.split, plan or self.plan, self.model
        )

    def test_whole_actual_packet_reintegrates(self):
        self.assertEqual(errors(), [])

    def test_one_missing_actual_pair_is_not_complete(self):
        s = copy.deepcopy(self.split)
        s["cases"].pop("pot03_family3")
        self.assertTrue(self.contract(split=s))

    def test_one_missing_positive_index_control_is_not_complete(self):
        s = copy.deepcopy(self.split)
        s["cases"].pop("pot09_family6")
        self.assertTrue(self.contract(split=s))

    def test_obstacle_family_cannot_be_dropped(self):
        p = copy.deepcopy(self.plan)
        p["obstacle_family_expressions_exact"].pop()
        self.assertTrue(self.contract(plan=p))

    def test_own_pot_rule_cannot_be_quietly_changed(self):
        p = copy.deepcopy(self.plan)
        p["obstacle_family_expressions_exact"][1] = "ps_body()"
        self.assertTrue(self.contract(plan=p))

    def test_source_point_controls_must_be_at_actual_index(self):
        s = copy.deepcopy(self.split)
        s["cases"]["pot09_family6"]["statistics"] = copy.deepcopy(s["cases"]["pot00_family6"]["statistics"])
        self.assertTrue(self.contract(split=s))

    def test_union_execution_cannot_be_relabeled_completed(self):
        s = copy.deepcopy(self.split)
        s["original_union_native_execution_completed"] = True
        self.assertTrue(self.contract(split=s))

    def test_rejected_main_cannot_get_a_top_level_pass_flag(self):
        m = copy.deepcopy(self.main)
        m["all_native_checks_clear"] = True
        self.assertTrue(runtime_claim_errors(m, self.retry))

    def test_any_additional_failure_remains_rejected(self):
        m = copy.deepcopy(self.main)
        m["cases"]["fi_actual_base_tray_collision"]["clear"] = False
        self.assertTrue(self.contract(main=m))

    def test_partial_pin_removal_or_wrong_partition_rejected(self):
        p = copy.deepcopy(self.pins)
        p["kept"][-1] = p["removed"][0]
        self.assertTrue(pin_stack_errors(p, self.stack))

    def test_old_M3x12_cannot_claim_new_engagement(self):
        s = copy.deepcopy(self.stack)
        s["screw_overall_including_countersunk_head_mm"] = 12
        self.assertTrue(pin_stack_errors(self.pins, s))

    def test_missing_actual_tray_mesh_rejected(self):
        n = "fa_tray_geometry"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / (n + ".log")).write_text("Status: NoError\n")
            self.assertTrue(row_errors(n, self.main["cases"][n], self.specs[n], p))

    def test_forged_empty_cannot_hide_real_intersection(self):
        n = "fi_actual_base_tray_collision"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            shutil.copyfile(OUT / "fi_long_foot_screw_positive_control.stl", p / (n + ".stl"))
            (p / (n + ".log")).write_text("Current top level object is empty.\n")
            self.assertTrue(row_errors(n, dict(returncode=1, statistics=None), self.specs[n], p))

    def test_sealed_capture_and_output_overwrites_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "handoff.json").write_text("{}")
            with self.assertRaises(RuntimeError):
                guard_capture(p)
            with self.assertRaises(RuntimeError):
                guard_output(p / "generated", p)

    def test_rebinding_includes_scoped_FAlibrary_and_is_readonly(self):
        before = sha(OUT / "context-derived.scad")
        with tempfile.TemporaryDirectory() as td:
            dest = prepare_rebind(Path(td) / "fresh")
            self.assertTrue((dest / "fa-scoped.scad").is_file())
            self.assertTrue(all(p.is_relative_to(dest) for p in closure(dest / "context-derived.scad")))
        self.assertEqual(before, sha(OUT / "context-derived.scad"))

    def test_thermal_credit_cannot_be_imported_from_metalwall_model(self):
        s = copy.deepcopy(self.stack)
        s["original_plastic_case_has_no_conditional_metal_wall_lid_heat_credit"] = False
        self.assertTrue(pin_stack_errors(self.pins, s))

    def test_review_assembly_cannot_omit_tray_or_any_family(self):
        manifest = json.loads((OUT / "assembly-manifest.json").read_text())
        src = OUT / "FI01-whole-unit-component-review.3mf"
        with zipfile.ZipFile(src) as z:
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
            self.assertTrue(component_errors(manifest, target))


if __name__ == "__main__":
    unittest.main()
