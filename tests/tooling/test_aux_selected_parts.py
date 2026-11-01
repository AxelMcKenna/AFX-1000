"""Exact AUX-cell body bounds must override generic case projections."""

import unittest

from hardware.cad.a12.positive_links.selected_parts import requirement
from hardware.cad.a12.repaired import height, validate_changed_parts


class ExactAuxParts(unittest.TestCase):
    CASES = [
        ("C3225X7R1E106K250AC", "C_1210_3225Metric", [3.6, 2.8, 2.8], 2.9, "TDK"),
        ("C2012X7S2A105K125AE", "C_0805_2012Metric", [2.45, 1.5, 1.5], 1.6, "TDK"),
        ("C0603C103J3GACTU", "C_0603_1608Metric", [1.75, 0.95, 0.9], 1.0, "KEMET"),
    ]

    def test_exact_maximum_including_asymmetric_soft_termination(self):
        for mpn, case, dimensions, projection, manufacturer in self.CASES:
            with self.subTest(mpn=mpn):
                row = requirement("Capacitor_SMD:" + case, mpn)
                self.assertEqual(row["manufacturer_body_maximum_mm"], dimensions)
                self.assertEqual(row["manufacturer"], manufacturer)
                self.assertAlmostEqual(row["assembled_projection_requirement_mm"], projection)
                self.assertEqual(row["project_seating_allocation_mm"], 0.1)
                self.assertFalse(row["physical_verified"])
                actual, basis = height("Capacitor_SMD:" + case, "C106", mpn)
                self.assertAlmostEqual(actual, projection)
                self.assertIn("PROJECT seat", basis)

    def test_footprint_and_mpn_mutations_cannot_reuse_selected_geometry(self):
        for mpn, case, _, _, _ in self.CASES:
            with self.assertRaisesRegex(ValueError, "footprint mismatch"):
                requirement("Capacitor_SMD:C_0402_1005Metric", mpn)
            self.assertIsNone(requirement("Capacitor_SMD:" + case, mpn + "BAD"))
            self.assertIsNone(requirement("Capacitor_SMD:" + case, "X" + mpn))

    def test_kemet_provenance_is_not_a_tdk_url_or_wrong_thickness_code(self):
        row = requirement("Capacitor_SMD:C_0603_1608Metric", "C0603C103J3GACTU")
        self.assertIn("content.kemet.com", row["primary_source"])
        self.assertIn("103/25V=CG", row["primary_source_locations"])
        self.assertIn("Table2A", row["primary_source_locations"])

    def test_caller_mutation_cannot_shrink_subsequent_envelope(self):
        row = requirement("Capacitor_SMD:C_1210_3225Metric", "C3225X7R1E106K250AC")
        row["manufacturer_body_maximum_mm"][2] = 0.1
        fresh = requirement("Capacitor_SMD:C_1210_3225Metric", "C3225X7R1E106K250AC")
        self.assertEqual(fresh["manufacturer_body_maximum_mm"][2], 2.8)
        self.assertAlmostEqual(fresh["assembled_projection_requirement_mm"], 2.9)

    def test_candidate_cannot_inherit_generic_height_for_an_unresolved_new_part(self):
        part = {"part": "10uF 25V unselected", "footprint": "Capacitor_SMD:C_1210_3225Metric"}
        with self.assertRaisesRegex(AssertionError, "independent exact geometry"):
            validate_changed_parts({"C106": part}, {}, [])

    def test_candidate_cannot_mix_selected_mpn_with_another_native_part(self):
        part = {"part": "TDK C2012X7S2A105K125AE", "footprint": "Capacitor_SMD:C_0805_2012Metric"}
        selection = {"refs": ["C113"], "mpn": "C2012X7R1H225K125AC", "native_footprint": part["footprint"]}
        with self.assertRaisesRegex(AssertionError, "selection MPN mismatch"):
            validate_changed_parts({"C113": part}, {}, [selection])
        selection["mpn"] = "C2012X7S2A105K125AE"
        validate_changed_parts({"C113": part}, {}, [selection])


if __name__ == "__main__":
    unittest.main()
