"""NP01 portable analytical and mutation regressions; no KiCad downloads."""

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection import audit, lifetime, selection, verify

ROOT = Path(__file__).resolve().parent


class PassiveSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / "analyses/analysis.json").read_text())
        cls.rows = {p["ref"]: p for p in cls.d["selections"]["rows"]}

    def test_saved_input_native_and_seal_integrity(self):
        self.assertEqual(verify.saved_errors(), [])
        if (ROOT / "handoff.json").exists():
            self.assertEqual(verify.verify_handoff(), [])

    def test_actual_inventory_has_no_dropped_passive(self):
        parts = json.loads((ROOT / "sources/NF261/components.json").read_text())
        self.assertEqual(set(self.rows), {p["ref"] for p in parts if p["ref"].startswith(("R", "C"))})
        self.assertEqual(len(self.rows), 196)
        d = copy.deepcopy(self.d)
        d["selections"]["rows"] = [p for p in d["selections"]["rows"] if p["ref"] != "R55"]
        self.assertIn("Incomplete or duplicate passive inventory", audit.report_errors(d))

    def test_catalog_range_boundaries_and_low_ohm_package(self):
        self.assertEqual(selection.precision_candidate(500)[3], 2)
        self.assertEqual(selection.precision_candidate(20000)[3], 2)
        self.assertEqual(selection.precision_candidate(30400)[3], 5)
        self.assertEqual(selection.precision_candidate(160000)[3], 5)
        self.assertEqual(selection.precision_candidate(35.7)[1], "TNPU0603")
        with self.assertRaises(ValueError):
            selection.precision_candidate(23)
        d = copy.deepcopy(self.d)
        next(x for x in d["selections"]["rows"] if x["ref"] == "R23")["TCR_ppm_per_K"] = 2
        self.assertTrue(any("outside checked range" in s for s in audit.report_errors(d)))

    def test_initial_tolerance_not_complete_lifetime(self):
        precise = [r for r in self.rows.values() if "planning_error_scenarios" in r]
        self.assertEqual(len(precise), 29)
        self.assertTrue(
            all(not s["complete_0p1pct_met"] for r in precise for s in r["planning_error_scenarios"])
        )
        self.assertTrue(
            all(r["planning_error_scenarios"][1]["complete_0p5pct_planning_met"] for r in precise)
        )
        self.assertGreater(selection.scenario(35.7, 0.0005, 5, 225000)["total_fraction"], 0.005)
        # Omitting the absolute-ohm terms materially understates tiny trim drift.
        low = selection.scenario(35.7, 0.0005, 5, 8000)["total_fraction"]
        high = selection.scenario(100000, 0.0005, 5, 8000)["total_fraction"]
        self.assertGreater(low - high, 0.001)

    def test_zero_error_monitor_matches_closed_form(self):
        p = {
            "existing_protect_reference_complete_error_requirement_fraction": 0,
            "opamp_offset_plus_drift_receiving_requirement_v": 0,
            "opamp_input_bias_complete_receiving_requirement_a": 0,
            "comparator_input_bias_full_temperature_table_a": 0,
            "comparator_offset_full_temperature_table_v": 0,
        }
        lo, hi = audit.monitor_trip(160000, 10000, [8660, 35.7], 100000, 0, p)
        nominal = 1.25 / (10000 / 160000) / (1 + (8660 + 35.7) / 100000)
        self.assertAlmostEqual(lo, nominal, places=12)
        self.assertAlmostEqual(hi, nominal, places=12)

    def test_monitor_bounds_enclose_independent_analytic_corners(self):
        p = {
            "existing_protect_reference_complete_error_requirement_fraction": 0,
            "opamp_offset_plus_drift_receiving_requirement_v": 0,
            "opamp_input_bias_complete_receiving_requirement_a": 0,
            "comparator_input_bias_full_temperature_table_a": 0,
            "comparator_offset_full_temperature_table_v": 0,
        }
        e = 0.005
        lo, hi = audit.monitor_trip(160000, 10000, [8660, 35.7], 100000, e, p)
        # Exact monotone expression: (ref*Ri/Rfb)/(1+Rt/Rb).
        expected_lo = (
            1.25 * 160000 * (1 - e) / (10000 * (1 + e)) / (1 + 8695.7 * (1 + e) / (100000 * (1 - e)))
        )
        expected_hi = (
            1.25 * 160000 * (1 + e) / (10000 * (1 - e)) / (1 + 8695.7 * (1 - e) / (100000 * (1 + e)))
        )
        self.assertAlmostEqual(lo, expected_lo, places=12)
        self.assertAlmostEqual(hi, expected_hi, places=12)
        d = copy.deepcopy(self.d)
        d["monitor_scenarios"]["results"]["N19_protected_UV"]["0.005"] = [18.4, 18.5]
        self.assertTrue(any("nonconservative" in s for s in audit.report_errors(d)))

    def test_native_old_lands_not_package_label_assumptions(self):
        fps = audit.native_footprints(ROOT / "sources/NF233-physical/negative_startup_ready.kicad_pcb")
        self.assertIn("0805", fps["C1"]["footprint"])
        self.assertIn("1206", self.rows["C1"]["old_footprint"])
        shunt = audit.pad_geometry(fps["R69"])
        self.assertAlmostEqual(shunt["gap_mm"], 4.7)
        wsl = audit.LANDS["WSL2512_7m_to500m"]
        self.assertAlmostEqual(2 * wsl["center_mm"] - wsl["size_mm"][0], 4.06)
        d = copy.deepcopy(self.d)
        next(x for x in d["land_comparison"] if x["ref"] == "R69")["matches_recommended_pattern_exactly"] = (
            True
        )
        self.assertTrue(any("falsely accepted" in s for s in audit.report_errors(d)))

    def test_real_heights_include_tolerance_and_project_seat(self):
        self.assertAlmostEqual(self.rows["C3"]["body_plus_seat_max_mm"], 1.05)
        self.assertAlmostEqual(self.rows["C1"]["body_plus_seat_max_mm"], 1.45)
        self.assertAlmostEqual(self.rows["C97"]["body_plus_seat_max_mm"], 1.9)
        self.assertIsNone(self.rows["C26"]["body_max_mm"])
        d = copy.deepcopy(self.d)
        next(x for x in d["selections"]["rows"] if x["ref"] == "C3")["body_plus_seat_max_mm"] = 1
        self.assertTrue(any("incomplete height" in s for s in audit.report_errors(d)))

    def test_new_UV_trim_complete_error_and_real_alternative(self):
        d = lifetime.analysis()
        self.assertFalse(d["ordinary_TNPW"]["R93"]["8000"]["complete0p5_planning_met"])
        self.assertLess(d["ordinary_TNPW"]["R93"]["1000"]["total_fraction"], 0.005)
        self.assertTrue(d["R93_concrete_alternative"]["planning_8000h"]["complete_0p5pct_planning_met"])
        self.assertFalse(d["R93_concrete_alternative"]["drop_in"])
        self.assertFalse(d["CRCW402_1000h"]["complete3pct_planning_met"])
        self.assertTrue(d["PRG402_1000h_option"]["complete3pct_planning_met"])
        self.assertFalse(d["production_adopted"])

    def test_feed_power_max_is_both_low_corner_and_derating_matters(self):
        cases = audit.dc_power_screens()
        maximum = cases["cases"][2]["watts_per_part"]
        self.assertAlmostEqual(maximum, 26.4**2 / (4 * 402 * 0.97), places=14)
        for i in range(101):
            r1 = 402 * (0.97 + 0.06 * i / 100)
            for j in range(101):
                r2 = 402 * (0.97 + 0.06 * j / 100)
                self.assertLessEqual(26.4**2 * r1 / (r1 + r2) ** 2, maximum + 1e-14)
        self.assertAlmostEqual(cases["shunts"][0]["power_at85_W"], 0.885 * 0.85)
        self.assertAlmostEqual(audit.available_power(0.14, 125, 125), 0)
        self.assertFalse(any(not math.isfinite(c["watts_per_part"]) for c in cases["cases"]))

    def test_failed_unsupported_qualification_is_rejected(self):
        for flag in ["physical_qualified", "electrical_qualified", "fabrication_released"]:
            d = copy.deepcopy(self.d)
            d[flag] = True
            self.assertIn("Unsupported qualification", audit.report_errors(d))
        d = copy.deepcopy(self.d)
        d["selections"]["rows"][0]["selected_for_production"] = True
        self.assertTrue(any("unsupported adoption" in s for s in audit.report_errors(d)))

    def test_handoff_cannot_promote_a_catalog_proposal(self):
        d = dict(
            complete_0p1pct_closed=False,
            production_selection_adopted=False,
            physical_qualified=False,
            electrical_qualified=False,
            fabrication_released=False,
            current_parent_electrical_board_claim=False,
            passive_refs=196,
            actual_native_land_candidates=9,
        )
        self.assertEqual(verify.handoff_contract_errors(d), [])
        for key in ["physical_qualified", "production_selection_adopted", "complete_0p1pct_closed"]:
            changed = dict(d, **{key: True})
            self.assertIn(f"Unsupported handoff contract: {key}", verify.handoff_contract_errors(changed))

    def test_replay_is_from_captured_inputs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="np01-replay-") as tmp:
            out = Path(tmp) / "selections"
            selection.build(out)
            replay = json.loads((out / "selections.json").read_text())
            self.assertEqual(replay, self.d["selections"])
            with self.assertRaises(RuntimeError):
                selection.build(out)


if __name__ == "__main__":
    unittest.main()
