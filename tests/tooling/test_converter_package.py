"""Package identity and a clean symbol cannot substitute for land-pattern data."""

import json
import unittest

from hardware.electronics.converter.package_review import audit


class ConverterPackageTests(unittest.TestCase):
    def test_full_pin_and_register_documentary_audit(self):
        report = audit.audit()
        self.assertEqual(report["pin_table_entries_checked"], 49)
        self.assertEqual(report["firmware_setting_entries_checked"], 45)
        self.assertTrue(report["package_release_blocked"])
        self.assertFalse(report["footprint_assigned"])
        self.assertFalse(report["actual_codec_sai_interoperability_verified"])
        self.assertFalse(report["build_ready"])

    def test_seven_pin_header_does_not_prove_converter_pin_kelvin_sensing(self):
        report = audit.audit()
        self.assertEqual(len(report["adc_driver_header_pin_contract"]), 7)
        self.assertFalse(report["header_sensing_is_converter_pin_kelvin"])
        self.assertFalse(report["separate_force_and_sense_conductors_to_converter"])
        self.assertIn("Co-locate", report["final_system_architecture_requirement"])

    def test_a_generic_qfn_footprint_is_not_manufacturer_approval(self):
        parts = json.loads((audit.PARENT / "components.json").read_text())
        next(p for p in parts if p["ref"] == "U1")["footprint"] = "Package_DFN_QFN:QFN-48_7x7mm"
        with self.assertRaisesRegex(AssertionError, "generic QFN"):
            audit.audit(components=parts)

    def test_pin_number_or_pad_ground_change_is_rejected(self):
        for pin in ("25", "49"):
            parts = json.loads((audit.PARENT / "components.json").read_text())
            p = next(p for p in parts if p["ref"] == "U1")
            next(p for p in p["pins"] if p["number"] == pin)["net"] = "WRONG_RAIL"
            with self.subTest(pin=pin), self.assertRaises(AssertionError):
                audit.audit(components=parts)

    def test_reserved_register_bits_are_preserved(self):
        header = (audit.REPO / "hardware/firmware/Es9292.h").read_text()
        changed = header.replace("{1, 1, 0x17, 0x02}", "{1, 1, 0x1f, 0x02}")
        self.assertNotEqual(changed, header)
        with self.assertRaises(AssertionError):
            audit.audit(header=changed)

    def test_ramped_down_cannot_be_reported_as_ramped_up(self):
        header = (audit.REPO / "hardware/firmware/Es9292.h").read_text()
        with self.assertRaisesRegex(AssertionError, "ramp-up"):
            audit.audit(header=header.replace("ramp == 0x30", "ramp == 0x00"))

    def test_missing_manufacturer_geometry_cannot_be_marked_approved(self):
        contract = json.loads((audit.ROOT / "source-contract.json").read_text())
        contract["package"]["approved_for_layout"] = True
        with self.assertRaises(AssertionError):
            audit.audit(contract=contract)

    def test_independent_gpio_bytes_are_combined_without_reserved_bits(self):
        contract = json.loads((audit.ROOT / "source-contract.json").read_text())
        self.assertEqual(audit.allowed_mask(contract["register_fields"], 63, 2), 0xFFFF)
        self.assertEqual(audit.allowed_mask(contract["register_fields"], 83, 2), 0x3C00)


if __name__ == "__main__":
    unittest.main()
