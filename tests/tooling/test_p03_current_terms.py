"""Signed current and package-sharing cases independent of the native mesh."""

import unittest

from hardware.qualification.boards.p03_ground_currents import current_terms, interval_product


class SignedCurrentTerms(unittest.TestCase):
    def case(self):
        return dict(
            grid_mm=0.1,
            status="diagnostic_estimate",
            ports=["U20.9", "U20.11", "U10.3"],
            unresolved_ports={},
            ideal_dc_source_ground_sensitivity={
                "observer": dict(ohm_by_unit_ground_injection={"U20.9": 0.2, "U20.11": -0.1, "U10.3": 2})
            },
        )

    def ledger(self):
        return dict(
            dc_converter_electrodes=[dict(ref="U20", pins=["9", "11"], expression="I_in - I_out")],
            local_static_current_electrodes=[dict(ref="U10", pin="3", signed_current_a=-0.02, scope="trial")],
        )

    def test_aggregate_package_current_does_not_assume_equal_pin_sharing(self):
        result = current_terms(self.case(), self.ledger())["observer_sensitivities"]["observer"]
        terms = result["current_terms"]
        self.assertEqual(terms[0]["coefficient_interval_ohm"], [-0.1, 0.2])
        self.assertEqual(terms[0]["signed_total_current_expression_a"], "I_in - I_out")
        self.assertIsNone(terms[0]["scenario_contribution_interval_v"])
        self.assertAlmostEqual(result["local_static_terms_only_interval_v"][0], -0.04)
        self.assertFalse(result["includes_converter_or_downstream_currents"])

    def test_negative_aggregate_current_reverses_coefficient_extrema(self):
        self.assertEqual(interval_product([-0.1, 0.2], [-2, -1]), [-0.4, 0.2])
        result = interval_product([-0.1, 0.2], [-2, 3])
        self.assertAlmostEqual(result[0], -0.4)
        self.assertAlmostEqual(result[1], 0.6)

    def test_missing_native_electrode_remains_unresolved(self):
        case = self.case()
        case["ports"].remove("U20.11")
        del case["ideal_dc_source_ground_sensitivity"]["observer"]["ohm_by_unit_ground_injection"]["U20.11"]
        result = current_terms(case, self.ledger())
        self.assertEqual(result["ledger_unresolved_electrodes"], ["U20.11"])
        observer = result["observer_sensitivities"]["observer"]
        self.assertIsNone(observer["local_static_terms_only_interval_v"])
        self.assertIsNone(observer["current_terms"][0]["coefficient_interval_ohm"])


if __name__ == "__main__":
    unittest.main()
