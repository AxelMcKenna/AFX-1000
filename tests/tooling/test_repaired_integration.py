"""Mechanical projection cases that native same-face courtyards cannot cover."""

import unittest

from hardware.cad.a12.repaired import height, same_board_intersections


class AssemblyEnvelopeIntersections(unittest.TestCase):
    def test_selected_capacitors_override_generic_case_height(self):
        cases = [
            ("C1005X7R1H104K050BB", "C_0402_1005Metric", 0.65),
            ("C2012X7R1H225K125AC", "C_0805_2012Metric", 1.55),
            ("C2012X7R1E475K125AB", "C_0805_2012Metric", 1.55),
        ]
        for mpn, package, projection in cases:
            with self.subTest(mpn=mpn):
                actual, basis = height("Capacitor_SMD:" + package, "C72", mpn)
                self.assertAlmostEqual(actual, projection)
                self.assertIn("PROJECT seat", basis)
                self.assertIn(mpn, basis)

    def test_selected_part_cannot_silently_use_a_wrong_footprint(self):
        with self.assertRaisesRegex(ValueError, "footprint mismatch"):
            height("Capacitor_SMD:C_0402_1005Metric", "C202", "C2012X7R1H225K125AC")
        with self.assertRaisesRegex(ValueError, "No assembled-height"):
            height("Capacitor_SMD:C_0402_1005Metric", "C72", "unselected")

    def test_through_lead_can_hit_a_different_backside_body(self):
        tail = ["P03_C1_tail_1", 4, 4, 3.5, 2.8, 2.8, 1.5]
        body = ["P03_R2", 4.5, 4.5, 3.1, 1, 1, 1.4]
        self.assertEqual(same_board_intersections([tail, body], []), [[tail[0], body[0]]])
        body[0] = "P03_C1_tail_2"
        self.assertEqual(same_board_intersections([tail, body], []), [])

    def test_capacitor_corner_box_is_not_a_cylindrical_collision(self):
        capacitor = ["E28_C1", 10, 10, 5, 4, 10]
        box = ["E28_R1", 11.6, 11.6, 6, 0.2, 0.2, 1]
        self.assertEqual(same_board_intersections([box], [capacitor]), [])
        box[1:3] = [11.3, 11.3]
        self.assertEqual(same_board_intersections([box], [capacitor]), [[box[0], capacitor[0]]])

    def test_board_identity_and_real_vertical_gap_are_preserved(self):
        boxes = [
            ["P03_R1", 0, 0, 3, 2, 2, 1],
            ["P03_R2", 0, 0, 4.1, 2, 2, 1],
            ["E28_R3", 0, 0, 3, 2, 2, 1],
        ]
        self.assertEqual(same_board_intersections(boxes, []), [])


if __name__ == "__main__":
    unittest.main()
