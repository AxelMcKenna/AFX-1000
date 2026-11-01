"""Source/load acceptance must expose failures even when native DRC is clean."""

import copy
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.power_supply.qualification import analysis as q


class PowerSupplyQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, cls.pins = netlist(q.OUT / "netlist.xml")
        cls.report = q.analyze()

    def test_actual_parts_determine_digital_corner_and_source_failure(self):
        self.assertEqual(q.resistor(self.parts, "R10") + q.resistor(self.parts, "R51"), 10510)
        d = self.report["digital"]
        self.assertAlmostEqual(d["full_minus40_to_150c_dc_v"][0], 4.894113468108393)
        self.assertAlmostEqual(d["full_minus40_to_150c_dc_v"][1], 5.114242821244744)
        self.assertFalse(d["full_temperature_source_screen_passes"])

    def test_conditional_range_does_not_hide_wider_component_limits(self):
        d = self.report["digital"]
        self.assertGreater(d["conditional_0_to_85c_dc_v"][0] - 0.010, 4.9)
        self.assertLess(d["conditional_0_to_85c_dc_v"][1] + 0.010, 5.1)
        self.assertFalse(d["junction_restriction_physically_verified"])
        self.assertLess(d["full_temperature_with_excursion_v"][0], 4.9)
        self.assertGreater(d["full_temperature_with_excursion_v"][1], 5.1)

    def test_full_temperature_divider_interval_is_empty(self):
        result = q.divider_interval(2000, [0.784, 0.816])
        self.assertFalse(result["feasible"])
        self.assertGreater(result["minimum_top_ohm"], result["maximum_top_ohm"])
        self.assertAlmostEqual(result["minimum_top_ohm"], 10550.623562214609)
        self.assertAlmostEqual(result["maximum_top_ohm"], 10450.721810777439)

    def test_source_only_feasible_interval_does_not_rescue_actual_load_path(self):
        self.assertTrue(q.divider_interval(2000, [0.788, 0.812])["feasible"])
        self.assertFalse(q.divider_interval(2000, [0.788, 0.812], loss=1.801 * 0.0075)["feasible"])
        self.assertLess(self.report["digital"]["conditional_load_interval_before_wire_v"][0], 4.9)

    def test_solver_boundaries_match_independent_corner_evaluation(self):
        result = q.divider_interval(2000, [0.788, 0.812])
        lo = q.buck_interval(result["minimum_top_ohm"], 2000, [0.788, 0.812])[0]
        hi = q.buck_interval(result["maximum_top_ohm"], 2000, [0.788, 0.812])[1]
        self.assertAlmostEqual(lo - 0.010, 4.9)
        self.assertAlmostEqual(hi + 0.010, 5.1)

    def test_disabling_a_boost_is_not_input_isolation(self):
        result = q.no_enable_isolation(self.pins)
        self.assertFalse(result["shutdown_is_input_isolation"])
        self.assertTrue(all(row["passive_precharge_path_present"] for row in result["paths"]))
        bad = copy.deepcopy(self.pins)
        bad["D1"]["2"] = "RAW_N_SW"
        with self.assertRaises(AssertionError):
            q.no_enable_isolation(bad)

    def test_negative_exposed_pad_cannot_be_grounded(self):
        tree = read_sexpr((q.SUPPLY / "routing/power_supply.kicad_pcb").read_text())
        q.critical_pins(tree)
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "U10"] for p in children(f, "property"))
        )
        pad = next(p for p in children(fp, "pad") if str(p[1]) == "11")
        first(pad, "net")[-1] = "/AGND"
        with self.assertRaises(AssertionError):
            q.critical_pins(tree)

    def test_original_allocated_startup_pass_does_not_cover_new_digital_reserve(self):
        profiles = self.report["input_profiles"]
        self.assertTrue(profiles["1.8"]["conditional_startup_screen_passes"])
        self.assertTrue(profiles["2.4"]["steady_screen_passes"])
        self.assertFalse(profiles["2.4"]["conditional_startup_screen_passes"])
        self.assertFalse(profiles["2.4"]["late_closure_current_bounded"])
        self.assertGreater(
            profiles["2.4"]["combined_input_a"], profiles["2.4"]["guard_minimum_limit_allocation_a"]
        )

    def test_hypothetical_copper_is_not_a_fabricator_stackup(self):
        self.assertFalse(self.report["actual_stackup_present"])
        for path, row in self.report["single_path_trace_only_hypotheses"].items():
            r35 = row["resistance_and_drop_by_hypothetical_finished_copper"]["35"][
                "trace_only_resistance_ohm"
            ]
            r70 = row["resistance_and_drop_by_hypothetical_finished_copper"]["70"][
                "trace_only_resistance_ohm"
            ]
            self.assertAlmostEqual(r35, 2 * r70)
            self.assertFalse(row["fabricated_resistance_or_ampacity_qualified"])
            self.assertFalse(row["vias_pad_spreading_connectors_and_returns_included"])

    def test_known_failures_and_unknown_gates_are_distinct(self):
        findings = {r["id"]: r for r in self.report["findings"]}
        for name in ["PSU-01", "PSU-02", "PSU-03"]:
            self.assertEqual(findings[name]["status"], "failed")
        self.assertTrue(any(f["status"] == "blocked" for f in findings.values()))
        self.assertTrue(self.report["analytical_acceptance_failed"])
        self.assertFalse(self.report["p02_is_implemented_on_this_board"])
        self.assertFalse(self.report["electrical_performance_qualified"])
        self.assertFalse(self.report["build_ready"])


if __name__ == "__main__":
    unittest.main()
