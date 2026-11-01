"""Portable saved-geometry contracts and realistic negative mutations."""

import json
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a12.thermal.interior_airpath.audit import header_errors

from . import assembly, base_brep, channel_budget, interfaces_stage, review_exports, stage
from .audit import assembly_errors, base_errors, errors, guard_errors, pin_errors, raw_contact_errors
from .channel_budget import section_bound, source_errors
from .seated_stage import CONTROL_GUARD
from .stage import OUT, ROOT
from .verify import row_errors, run, specs


class Review(unittest.TestCase):
    def test_actual_saved_native_and_source_evidence(self):
        self.assertEqual(errors(),[])

    def test_restoring_original_short_rear_gap_is_rejected(self):
        d=json.loads((OUT/"analysis.json").read_text())
        d["rear_wall_Y"]=[142,144]
        self.assertIn("wrong-actual-rear-gap",source_errors((OUT/"checks.scad").read_text(),d))

    def test_omitted_intruding_feedthrough_cannot_pass_source_contract(self):
        d=json.loads((OUT/"analysis.json").read_text())
        source=(OUT/"checks.scad").read_text().replace("translate([0,0,2])cylinder(d=6,h=.6,$fn=96)","")
        self.assertTrue(any("source-construction-missing" in e for e in source_errors(source,d)))

    def test_continuous_section_bounds_subtract_hardware(self):
        a=section_bound(5.95)
        self.assertLess(a["right_uniform_lower_bound_mm2"],a["left_uniform_lower_bound_mm2"])
        self.assertLess(a["right_uniform_lower_bound_mm2"],a["gross_mm2"]-30)
        self.assertGreater(a["right_uniform_lower_bound_mm2"],200)
        self.assertLess(section_bound(.95)["right_uniform_lower_bound_mm2"],5)

    def test_omitted_whole_pin_removal_cannot_pass(self):
        d=json.loads((OUT/"analysis.json").read_text())
        wrong=d["kept_pins"]+[d["additional_whole_removed"][0]]
        self.assertIn("wrong-actual-whole-pin-field",pin_errors(d,wrong))

    def test_missing_actual_native_approach_check_rejected(self):
        d=json.loads((OUT/"current-native/verification.json").read_text())
        d["cases"].pop("lower_approach_clear_core_collision")
        self.assertIn("missing/reordered-native-coverage",header_errors(d,specs(),"ap_case"))

    def test_nonempty_stl_cannot_be_forged_as_empty(self):
        name="meter_fan_collision"
        d=json.loads((OUT/"current-native/verification.json").read_text())["cases"][name]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/(name+".log")).write_text("Current top level object is empty.")
            (p/(name+".stl")).write_bytes((OUT/"current-native/new_meter_border_control.stl").read_bytes())
            d.update(returncode=1,statistics=None)
            self.assertIn("actual-nonempty-or-failed-execution",row_errors(name,d,specs()[name],p))

    def test_absent_base_cannot_be_promoted_as_part(self):
        name="base_geometry"
        d=json.loads((OUT/"current-native/verification.json").read_text())["cases"][name]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/(name+".log")).write_text("Current top level object is empty.")
            d.update(returncode=1,statistics=None)
            self.assertIn("missing-actual-required-solid",row_errors(name,d,specs()[name],p))

    def test_noerror_still_required_for_boolean_part(self):
        name="base_geometry"
        d=json.loads((OUT/"current-native/verification.json").read_text())["cases"][name]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/(name+".log")).write_text("Top level object is a 3D object (PolySet)")
            (p/(name+".stl")).write_bytes((OUT/"current-native/base_geometry.stl").read_bytes())
            self.assertIn("missing-NoError-or-named-certified-primitive",row_errors(name,d,specs()[name],p))

    def test_changed_one_pin_volume_rejected(self):
        d=json.loads((OUT/"base-BREP-verification.json").read_text())
        d["actual_volume_mm3"]+=108
        self.assertIn("wrong-whole-pin-only-volume",base_errors(d))

    def test_whole_assembly_requires_actual_feedthroughs(self):
        d=json.loads((OUT/"assembly-manifest.json").read_text())
        d["objects"].pop("feedthrough_receiving_geometry")
        self.assertIn("missing-complete-review-family",assembly_errors(d))

    def test_twenty_micron_guard_is_not_twenty_nanometres(self):
        c=json.loads((OUT/"mating-seat-contract.json").read_text())
        g=(ROOT/"mating_guards.scad").read_text().replace("mg=.00002;","mg=.02;")
        self.assertIn("wrong-seat-guard-scale",guard_errors(c,g,(OUT/"mating-seated.scad").read_text(),(ROOT/"mating.scad").read_text()))

    def test_control_must_apply_same_translated_seat_guard(self):
        c=json.loads((OUT/"mating-seat-contract.json").read_text())
        fixture=(OUT/"mating-seated.scad").read_text()
        line=next(l for l in fixture.splitlines() if l.startswith('if(mate_seated_case=="M2_directseal_overlap_control")'))
        fixture=fixture.replace(line,line.replace('mate_guard_for('+json.dumps(CONTROL_GUARD["M2_directseal_overlap_control"])+');',""))
        self.assertIn("raw-branch-or-same-guard-control-changed:M2_directseal_overlap_control",guard_errors(c,(ROOT/"mating_guards.scad").read_text(),fixture,(ROOT/"mating.scad").read_text()))

    def test_area_does_not_claim_installed_flow(self):
        d=channel_budget.report()
        self.assertFalse(d["installed_flow_verified"])
        self.assertFalse(d["physical_qualified"])
        self.assertGreater(d["pressure_sensitivity"]["remaining_for_ALL_base_approach_pins_turns_and_outlet_Pa"],3)
        self.assertTrue(d["pressure_sensitivity"]["these_K_values_are_sensitivities_not_guaranteed_bounds"])

    def test_saved_facet_certification_must_match_actual_mesh(self):
        s=json.loads((OUT/"raw-mating-surface-audit.json").read_text())
        d=json.loads((OUT/"raw-mating-bolt-domain-audit.json").read_text())
        s["cases"]["feedthrough_wall"]["classes"]["named-plane"]+=1
        self.assertIn("raw-contact-classification-not-actual:feedthrough_wall",raw_contact_errors(s,d))

    def test_existing_source_outputs_never_recaptured(self):
        for function in [stage.capture,assembly.build,base_brep.build,channel_budget.build,interfaces_stage.build,review_exports.build]:
            with self.assertRaises(RuntimeError):
                function()
        with self.assertRaises(RuntimeError):
            run("not-a-runner",OUT/"current-native")


if __name__=="__main__":
    unittest.main()
