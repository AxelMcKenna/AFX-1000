"""Portable actual-evidence checks and meaningful qualification mutations."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from . import assembly, base_brep, drawing, seated_stage, stage
from .audit import assembly_errors, base_report_errors, design_errors, errors, guard_errors, header_errors
from .mating import CONTROLS, EMPTY
from .pressure_rejection import calculate, report
from .seated_stage import EXTRA
from .stage import OUT, ROOT
from .verify import row_errors, run, specs


class Review(unittest.TestCase):
    def test_complete_saved_actual_packet(self):
        self.assertEqual(errors(), [])

    def test_old4p2_minimum_fan_bore_is_rejected(self):
        d = json.loads((OUT / "analysis.json").read_text())
        d["fan"]["hole_min"] = 4.2
        self.assertIn("Sunon-minimum-hole-fact-lost", design_errors(d))

    def test_nominal_shim_cannot_ignore_actual_frame_thickness(self):
        d = json.loads((OUT / "analysis.json").read_text())
        d["fan"]["nominal_CAD_matched_shim"] = 2
        self.assertIn("unmatched-fan-shim-stack", design_errors(d))

    def test_missing_actual_wholepin_removal_is_rejected(self):
        d = json.loads((OUT / "analysis.json").read_text())
        d["pins"]["kept_centres"].append(d["pins"]["removed_centres"][0])
        self.assertIn("design-requirement-changed:pins", design_errors(d))

    def test_area_reduction_below_budget_is_not_a_pass(self):
        d = json.loads((OUT / "analysis.json").read_text())
        d["inlet"]["nominal_total_net_mm2"] = 2499
        self.assertIn("insufficient-declared-net-area", design_errors(d))

    def test_cad_does_not_establish_flow_or_physical_pass(self):
        d = json.loads((OUT / "analysis.json").read_text())
        d["actual_flow_split_verified"] = True
        d["physical_qualified"] = True
        result = design_errors(d)
        self.assertIn("unsupported-approval:actual_flow_split_verified", result)
        self.assertIn("unsupported-approval:physical_qualified", result)

    def test_missing_required_native_case_is_rejected(self):
        p = json.loads((OUT / "current-native/verification.json").read_text())
        p["cases"].pop("feedthrough_fan_collision")
        self.assertIn("missing/reordered-native-coverage", header_errors(p, specs(), "ap_case"))

    def test_wrong_actual_selector_is_rejected(self):
        p = json.loads((OUT / "current-native/verification.json").read_text())
        row = p["cases"]["floating_fan_hole_collision"]
        row["command"][row["command"].index('ap_case="floating_fan_hole_collision"')] = (
            'ap_case="new_pin_void_collision"'
        )
        self.assertIn(
            "wrong-actual-native-selector:floating_fan_hole_collision", header_errors(p, specs(), "ap_case")
        )

    def test_declared_empty_with_actual_collision_mesh_is_rejected(self):
        p = json.loads((OUT / "current-native/verification.json").read_text())
        n = "new_pin_void_collision"
        row = copy.deepcopy(p["cases"][n])
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / (n + ".log")).write_text("Current top level object is empty.")
            (folder / (n + ".stl")).write_bytes(
                (OUT / "current-native/old_plate_blockage_control.stl").read_bytes()
            )
            row.update(returncode=1, statistics=None)
            self.assertIn("actual-nonempty-or-failed-execution", row_errors(n, row, specs()[n], folder))

    def test_missing_required_actual_part_is_rejected(self):
        p = json.loads((OUT / "current-native/verification.json").read_text())
        n = "base_geometry"
        row = copy.deepcopy(p["cases"][n])
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / (n + ".log")).write_text("Current top level object is empty.")
            row.update(returncode=1, statistics=None)
            self.assertIn("missing-actual-required-solid", row_errors(n, row, specs()[n], folder))

    def test_boolean_NoError_is_still_required(self):
        p = json.loads((OUT / "current-native/verification.json").read_text())
        n = "base_geometry"
        row = p["cases"][n]
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / (n + ".log")).write_text("Top level object is a 3D object (PolySet)")
            (folder / (n + ".stl")).write_bytes((OUT / "current-native/base_geometry.stl").read_bytes())
            self.assertIn(
                "missing-NoError-or-named-certified-primitive", row_errors(n, row, specs()[n], folder)
            )

    def test_twenty_micron_guard_is_not_twenty_nanometres(self):
        c = json.loads((OUT / "mating-seat-contract.json").read_text())
        g = (ROOT / "mating_guards.scad").read_text().replace("mg=.00002;", "mg=.02;")
        self.assertIn(
            "wrong-numeric-seat-guard", guard_errors(c, g, (OUT / "mating-seated.scad").read_text())
        )

    def test_positive_controls_must_use_the_same_guard(self):
        c = json.loads((OUT / "mating-seat-contract.json").read_text())
        s = (OUT / "mating-seated.scad").read_text()
        line = next(line for line in s.splitlines() if line.startswith('if(mate_seated_case=="M3_directseal_overlap_control")'))
        s = s.replace(line, line.replace('mate_guard_for("M3_hardware_nominal_mates");', ""))
        self.assertTrue(
            any(
                "raw-branch-or-guard-control-changed" in e
                for e in guard_errors(c, (ROOT / "mating_guards.scad").read_text(), s)
            )
        )

    def test_radial_counterexamples_cannot_be_omitted(self):
        p = json.loads((OUT / "mating-seated/verification.json").read_text())
        p["cases"].pop("FIP_radial_overlap_control")
        definitions = {
            n: dict(role="empty" if n in EMPTY else "control" if n in CONTROLS else "witness")
            for n in EMPTY + CONTROLS + EXTRA
        }
        self.assertIn("missing/reordered-native-coverage", header_errors(p, definitions, "mate_seated_case"))

    def test_complete_assembly_requires_every_scene_family(self):
        m = json.loads((OUT / "assembly-manifest.json").read_text())
        m["objects"].pop("assembly_TIM_shims")
        self.assertIn("missing-assembly-family", assembly_errors(m))

    def test_one_missing_pin_cannot_hide_in_cad_volume(self):
        d = json.loads((OUT / "base-BREP-verification.json").read_text())
        d["exact_curve_new_volume_mm3"] += 108
        self.assertIn("base-mass-balance-mismatch", base_report_errors(d))

    def test_sources_and_existing_outputs_cannot_be_recaptured(self):
        for function in [stage.capture, assembly.build, base_brep.build, drawing.build, seated_stage.build]:
            with self.assertRaises(RuntimeError):
                function()
        with self.assertRaises(RuntimeError):
            run("not-a-runner", OUT / "current-native")

    def test_meter_area_cannot_be_promoted_as_actual_flow(self):
        d = report()
        self.assertTrue(d["nominal125_base_target_rejected"])
        self.assertFalse(d["airflow_target_met"])
        self.assertGreater(d["meter125_excess_before_other_base_losses_Pa"], 6)
        rho = d["inputs"]["density_kg_m3"]
        self.assertAlmostEqual(calculate(250, 1.2, rho, .6), calculate(125, 1.2, rho, .6) / 4)


if __name__ == "__main__":
    unittest.main()
