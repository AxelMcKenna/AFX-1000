"""Pin-role mutations, datasheet-condition safeguards and preserved current allocations."""

import copy
import unittest

from . import analyze, validate


class PowerProvenance(unittest.TestCase):
    def test_actual_export_BOM_PCB_and_source_binding(self):
        self.assertEqual(validate.packet_errors(), [])
        self.assertEqual(validate.seal_errors(), [])

    def test_supply_and_sink_are_distinct_native_paths(self):
        led = analyze.captured_board("led_driver", "E20")
        carrier = analyze.captured_board("processor_carrier", "E19")
        self.assertEqual(analyze.role_errors(led, carrier), [])
        led = copy.deepcopy(led)
        led[1]["U1"]["32"] = "V3V3_IO"
        self.assertIn("exported: TLC supply domain changed", analyze.role_errors(led, carrier))

    def test_LED_branch_must_bypass_Seed_resistor(self):
        led = analyze.captured_board("led_driver", "E20")
        carrier = copy.deepcopy(analyze.captured_board("processor_carrier", "E19"))
        carrier[3]["J11"]["2"] = "SEED_VIN"
        self.assertTrue(analyze.role_errors(led, carrier))

    def test_90mA_max_test_conditions_are_not_silently_transferred(self):
        actual = dict(RIREF_ohm=16500, BLANK=0, VOUT_v=1, GSn="FFFh", SIN_SCLK_XLAT=0, VCC_v=5, TA_c=40)
        self.assertFalse(analyze.ICC4_conditions_match(actual))
        actual["RIREF_ohm"] = 1600
        self.assertTrue(analyze.ICC4_conditions_match(actual))
        actual["SIN_SCLK_XLAT"] = "toggling"
        self.assertFalse(analyze.ICC4_conditions_match(actual))

    def test_allocations_are_retained_with_traceable_provenance(self):
        a = analyze.read(analyze.OUT / "analysis.json")
        self.assertAlmostEqual(a["retained_current_allocations_a"]["LED_5v_total"], 0.764)
        self.assertAlmostEqual(a["retained_current_allocations_a"]["LED_logic_label"], 4 * 0.09 + 0.02)
        self.assertAlmostEqual(a["retained_current_allocations_a"]["LED_sink96"], 96 * 0.004)
        self.assertEqual(a["provenance"]["E19_passive_filter_screen_assumption_a"], 0.5)
        self.assertEqual(a["provenance"]["E14_seed_and_its_3v3_allocation_a"], 0.6)
        self.assertEqual(a["provenance"]["P02_seed_allocation_a"], 1)
        bad = copy.deepcopy(a)
        bad["retained_current_allocations_a"]["LED_ICC_four"] *= 0.1
        self.assertIn("Reserved source/current target silently changed", validate.errors(bad))

    def test_USB_configuration_and_current_provisions_are_not_vendor_upper(self):
        a = analyze.read(analyze.OUT / "analysis.json")
        self.assertIsNone(a["module_input_max_current_from_reviewed_primary_a"])
        self.assertIsNone(a["module_3v3_output_max_current_from_reviewed_primary_a"])
        bad = copy.deepcopy(a)
        bad["module_input_max_current_from_reviewed_primary_a"] = 0.5
        self.assertIn("Invented module current/capacity bound", validate.errors(bad))

    def test_nominal_sink_and_partial_misc_never_qualify_maximum(self):
        a = analyze.read(analyze.OUT / "analysis.json")
        self.assertAlmostEqual(a["nominal_sink_a"], 41 * 1.2 / 16500)
        self.assertFalse(a["sink4mA_allocation_is_manufacturer_guaranteed_at_actual_setting"])
        self.assertFalse(a["internal_IREF_resistors_added_to_ICC_again"])
        bad = copy.deepcopy(a)
        bad["E20_misc20mA_verified_against_all_components_states"] = True
        self.assertIn("Partial screen represented as complete proof", validate.errors(bad))

    def test_unlisted_children_and_changed_seal_stay_explicit(self):
        a = analyze.read(analyze.OUT / "analysis.json")
        self.assertIn("SDcard", a["partially_omitted_child_names_from_P02_75mA_diagnostic"])
        self.assertFalse(a["missing_child_names_are_proof_Seed1A_envelope_exceeded"])
        seal = analyze.read(analyze.ROOT / "handoff.json")
        seal["sha256"][next(iter(seal["sha256"]))] = "0" * 64
        self.assertTrue(validate.seal_errors(seal))


if __name__ == "__main__":
    unittest.main()
