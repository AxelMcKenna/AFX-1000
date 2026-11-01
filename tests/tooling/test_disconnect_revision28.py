"""Independent E28 manufacturer geometry and terminal/electrode contracts."""

import copy
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.rail_disconnect.revision28.capacitor_patterns import (
    CAPS,
)
from hardware.electronics.rail_disconnect.revision28.capacitor_patterns import (
    check as check_capacitor,
)
from hardware.electronics.rail_disconnect.revision28.capacitor_patterns import (
    footprint as cap_fp,
)
from hardware.electronics.rail_disconnect.revision28.control import StaticLogic, contract, safe_inputs
from hardware.electronics.rail_disconnect.revision28.generate import STACKUP
from hardware.electronics.rail_disconnect.revision28.manufacturer import check_q5b, q5b
from hardware.electronics.rail_disconnect.revision28.positive import components
from hardware.electronics.rail_disconnect.revision28.positive_footprints import (
    aup,
    check_aup,
    check_efuse,
    check_lvc14,
    check_pw14,
    check_supervisor,
    efuse,
    lvc14,
    pw14,
    supervisor,
)
from hardware.electronics.rail_disconnect.revision28.startup import screen as startup_screen
from hardware.electronics.rail_disconnect.revision28.terminals import check_terminal, terminal
from hardware.electronics.rail_disconnect.revision28.wire_outputs import check as check_wire
from hardware.electronics.rail_disconnect.revision28.wire_outputs import footprint as wire_fp

try:
    import numpy as np

    from hardware.electronics.rail_disconnect.revision28.copper import Mesh
except ImportError:
    np = None


class ManufacturerGeometry(unittest.TestCase):
    def test_native_closure_requires_explicit_check_coverage(self):
        from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

        empty = {"violations": [], "unconnected_items": [], "schematic_parity": []}
        self.assertFalse(summarize(empty, {})["native_closed"])
        checked = dict(empty, ignored_checks=[])
        erc_checked = {"sheets": [], "ignored_checks": []}
        self.assertFalse(summarize(checked, {})["native_closed"])
        self.assertTrue(summarize(checked, erc_checked)["native_closed"])
        self.assertFalse(
            summarize(checked, {"sheets": [{"violations": [{"type": "electrical"}]}]})["native_closed"]
        )

    def test_ignored_default_rule_cannot_be_a_clean_native_pass(self):
        from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

        for key in (
            "missing_courtyard",
            "track_not_centered_on_via",
            "tuning_profile_track_geometries",
            "footprint_filters_mismatch",
            "footprint_type_mismatch",
        ):
            with self.subTest(key=key):
                raw = {
                    "violations": [],
                    "unconnected_items": [],
                    "schematic_parity": [],
                    "ignored_checks": [{"key": key}],
                }
                status = summarize(raw, {"sheets": [], "ignored_checks": []})
                self.assertFalse(status["native_closed"])
                self.assertFalse(status["all_native_rule_checks_enabled"])

    def test_ignored_ERC_category_cannot_be_a_clean_native_pass(self):
        from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

        drc = {"violations": [], "unconnected_items": [], "schematic_parity": [], "ignored_checks": []}
        for key in ("single_global_label", "four_way_junction", "simulation_model_issue", "footprint_filter"):
            with self.subTest(key=key):
                erc = {"sheets": [], "ignored_checks": [{"key": key}]}
                status = summarize(drc, erc)
                self.assertTrue(status["all_native_DRC_rule_checks_enabled"])
                self.assertFalse(status["all_native_ERC_rule_checks_enabled"])
                self.assertFalse(status["native_closed"])

    def test_outline_growth_rejects_changes_to_parts_copper_rules_and_boss_reliefs(self):
        from hardware.electronics.rail_disconnect.revision28.outline_growth_review import check_outline_only

        before = read_sexpr("""(kicad_pcb
          (gr_line (start 256 143.987119) (end 256 145.25) (stroke (width .05)) (layer "Edge.Cuts"))
          (gr_line (start 256 145.25) (end 105 145.25) (stroke (width .05)) (layer "Edge.Cuts"))
          (gr_line (start 105 145.25) (end 105 135) (stroke (width .05)) (layer "Edge.Cuts"))
          (gr_arc (start 254.4 140.5) (mid 255 142) (end 256 143.987119) (layer "Edge.Cuts"))
          (footprint "Actual" (at 120 130) (pad "1" thru_hole circle (drill 1) (net 3 "FORCE")))
          (via (at 130 140) (drill .3))
          (zone (clearance .2)))""")
        after = copy.deepcopy(before)
        for line in children(after, "gr_line"):
            for key in ("start", "end"):
                point = first(line, key)
                if float(point[2]) == 145.25:
                    point[2] = type(point[2])("154.5")
        self.assertTrue(check_outline_only(before, after)["every_other_literal_board_object_unchanged"])
        for label in ("pad-net", "via-hole", "zone-rule", "part-pose", "boss-relief", "edge-width"):
            with self.subTest(label=label):
                bad = copy.deepcopy(after)
                if label == "pad-net":
                    first(children(children(bad, "footprint")[0], "pad")[0], "net")[1] = 4
                elif label == "via-hole":
                    first(children(bad, "via")[0], "drill")[1] = 0.4
                elif label == "zone-rule":
                    first(children(bad, "zone")[0], "clearance")[1] = 0.1
                elif label == "part-pose":
                    first(children(bad, "footprint")[0], "at")[1] = 120.1
                elif label == "boss-relief":
                    first(children(bad, "gr_arc")[0], "mid")[1] = 255.1
                else:
                    first(first(children(bad, "gr_line")[0], "stroke"), "width")[1] = 0.06
                with self.assertRaises(AssertionError):
                    check_outline_only(before, bad)

    def test_schmitt_receiver_uses_primary_pw14_lands_and_pin_contract(self):
        from hardware.electronics.rail_disconnect.revision28.control import contract

        row = check_lvc14(lvc14())
        self.assertFalse(row["has_manufacturer_ioff_guarantee"])
        self.assertEqual(row["source_pdf_pages"], [38, 39, 40])
        bad = lvc14()
        first(children(bad, "pad")[0], "size")[1] = 1.475
        with self.assertRaises(AssertionError):
            check_lvc14(bad)
        parts = components()
        next(p for p in parts if p["ref"] == "U28")["part"] = "SN74LVC04APWR"
        with self.assertRaises(AssertionError):
            contract(parts)

    def test_settled_hot_loading_and_open_harness_mutations(self):
        from hardware.electronics.rail_disconnect.revision28.logic_levels import screen

        result = screen()
        self.assertTrue(result["raw_ready_conditional_corners_pass"])
        self.assertTrue(result["raw_run_open_conditional_corner_pass"])
        self.assertTrue(result["ordinary_logic_settled_loading_pass"])
        self.assertFalse(result["physical_qualified"])
        self.assertGreater(result["ready_received_high_v"], 2.15)
        for ref, value, key in (
            ("R140", "10k", "ordinary_logic_settled_loading_pass"),
            ("R142", "47k", "raw_ready_conditional_corners_pass"),
            ("R93", "100k", "raw_run_open_conditional_corner_pass"),
        ):
            parts = components()
            next(p for p in parts if p["ref"] == ref)["part"] = value
            self.assertFalse(screen(parts)[key], ref)
        self.assertFalse(screen(pullup=4700)["raw_ready_conditional_corners_pass"])

    def test_new_efuse_and_supervisor_match_their_primary_land_contracts(self):
        self.assertFalse(check_efuse(efuse())["assembler_accepted"])
        self.assertFalse(check_supervisor(supervisor())["assembler_accepted"])
        fp = efuse()
        first(children(fp, "pad")[0], "at")[2] = 0.675
        with self.assertRaises(AssertionError):
            check_efuse(fp)

    def test_aup_copper_and_pin_orientation_have_independent_contract(self):
        self.assertFalse(check_aup(aup())["assembler_accepted"])
        for mutation in ("pitch", "width", "mirror", "paste"):
            fp = aup()
            pad = children(fp, "pad")[0]
            if mutation == "pitch":
                first(pad, "at")[2] = -0.65
            elif mutation == "width":
                first(pad, "size")[1] = 1.25
            elif mutation == "mirror":
                first(pad, "at")[1] = 1.55
            else:
                first(pad, "layers").remove("F.Paste")
            with self.assertRaises(AssertionError, msg=mutation):
                check_aup(fp)

    def test_official_quad_ordering_and_low_profile_pw14_land_pattern(self):
        parts = {c["ref"]: c for c in components()}
        self.assertEqual(parts["U9"]["part"], "TLV1824DR")
        self.assertEqual(parts["U10"]["part"], "TLV1824DR")
        self.assertEqual(parts["U18"]["part"], "TLV1824PWR")
        self.assertEqual(check_pw14(pw14())["maximum_package_height_mm"], 1.2)
        fp = pw14()
        first(children(fp, "pad")[0], "size")[2] = 0.4
        with self.assertRaises(AssertionError):
            check_pw14(fp)

    def test_selected_c0g_cases_match_manufacturer_voltage_and_height_rows(self):
        for kind in CAPS:
            self.assertFalse(check_capacitor(cap_fp(kind), kind)["procurement_accepted"])
            fp = cap_fp(kind)
            first(children(fp, "pad")[0], "at")[1] = -0.95
            with self.assertRaises(AssertionError):
                check_capacitor(fp, kind)
        parts = components()
        large = [c for c in parts if c.get("manufacturer_part") == "C1210C104J5GACTU"]
        digital = [c for c in parts if c.get("manufacturer_part") == "C1206C473J5GACTU"]
        self.assertEqual(len(large), 8)
        self.assertEqual(len(digital), 4)
        self.assertTrue(all(c["maximum_package_height_mm"] == 1.4 for c in large))
        self.assertTrue(all(c["maximum_package_height_mm"] == 1.2 for c in digital))
        self.assertNotIn("J2", {c["ref"] for c in parts})

    def test_both_manufacturer_patterns_pass(self):
        for part in ("CSD18510Q5B", "CSD18540Q5B"):
            row = check_q5b(q5b(part))
            self.assertEqual(row["physical_gate"], 4)
            self.assertEqual(row["stencil_apertures"], 16)
            self.assertFalse(row["mask_and_stencil_process_approved"])

    def test_old_gap_misread_and_mirrored_gate_are_rejected(self):
        for mutation in ("width", "gate", "drain", "paste"):
            fp = q5b("CSD18540Q5B")
            pads = children(fp, "pad")
            if mutation == "width":
                first(pads[0], "size")[1] = 1.100
            elif mutation == "gate":
                pads[0][1], pads[3][1] = pads[3][1], pads[0][1]
            elif mutation == "drain":
                first(pads[5], "size")[1] = 0.700
            else:
                fp.remove(pads[-1])
            with self.assertRaises(AssertionError, msg=mutation):
                check_q5b(fp)

    def test_gate_is_physical_pin_four_at_bottom_left_not_mirrored(self):
        pads = children(q5b("CSD18510Q5B"), "pad")
        gate = [p for p in pads if p[1] == "2"]
        self.assertEqual(len(gate), 1)
        self.assertEqual(list(map(float, first(gate[0], "at")[1:])), [-2.770, 1.905])
        self.assertEqual(len([p for p in pads if p[1] == "1"]), 3)
        self.assertEqual(len([p for p in pads if p[1] == "3"]), 5)

    def test_return_terminal_is_smt_annulus_plus_real_npth(self):
        fp = terminal()
        row = check_terminal(fp)
        self.assertEqual(row["copper_od_mm"], 8.5)
        self.assertEqual(row["copper_id_mm"], 4.7)
        self.assertFalse(row["contact_resistance_measured"])
        hole = children(fp, "pad")[1]
        hole[2] = "thru_hole"
        with self.assertRaises(AssertionError):
            check_terminal(fp)

    def test_actual_force_wire_holes_are_not_generic_header_contacts(self):
        row = check_wire(wire_fp())
        self.assertEqual(row["awg"], 14)
        self.assertAlmostEqual(row["minimum_bend_radius_mm"], 18.034)
        self.assertFalse(row["source_joint_measured"])
        fp = wire_fp()
        first(children(fp, "pad")[0], "drill")[1] = 1.0
        with self.assertRaises(AssertionError):
            check_wire(fp)

    def test_first_master_stress_includes_whole_capacitance_and_load(self):
        rows = startup_screen()
        dig = next(r for r in rows if r["domain"] == "digital")
        self.assertGreater(dig["initial_pass_power_w"], 19.5)
        self.assertGreater(dig["total_pass_energy_j"], 0.24)
        self.assertTrue(dig["no_division_by_parallel_channel_count"])
        self.assertFalse(dig["thermal_soa_qualified"])
        self.assertEqual(dig["input_maximum_falling_slew_requirement_v_us"], 10)
        self.assertGreater(dig["output_slew_v_s"][1], 202)
        parts = components()
        cap = next(c for c in parts if c["ref"] == dig["native_timing_cap_ref"])
        cap["part"] = "47nF 50V X7R 5%"
        with self.assertRaises(AssertionError):
            startup_screen(parts)

    def test_candidate_stackup_is_dimensional_but_unaccepted(self):
        nominal = 6 * STACKUP["finished_copper_mm"]["nominal"] + sum(STACKUP["dielectric_nominal_mm"])
        self.assertAlmostEqual(nominal, 1.6)
        self.assertGreaterEqual(STACKUP["finished_copper_mm"]["minimum"], 0.070)
        self.assertFalse(STACKUP["manufacturing_accepted"])


class NativeControlLogic(unittest.TestCase):
    enables = (
        "E28_MASTER_ENABLE",
        "E28_DIG_FOLLOW1",
        "E28_DIG_FOLLOW2",
        "E28_DIG_FOLLOW3",
        "E28_ANA_ENABLE",
        "E28_ANA_FOLLOW",
        "E28_ANA_FOLLOW2",
    )

    def model(self):
        parts = components()
        contract(parts)
        model = StaticLogic(parts)
        model.settle(**safe_inputs())
        return model

    def running(self):
        model = self.model()
        model.settle(E28_AUX_RESET_N=1, POWER_RUN=1, P03_SOURCES_READY=1, ANA_SOURCE_OK=1, DIG_SOURCE_OK=1)
        return model

    def test_waiting_for_sources_does_not_latch_startup_off(self):
        model = self.model()
        values = model.settle(E28_AUX_RESET_N=1, POWER_RUN=1)
        self.assertFalse(values["E28_FAULT"])
        self.assertFalse(values["E28_MASTER_ENABLE"])
        values = model.settle(P03_SOURCES_READY=1, ANA_SOURCE_OK=1, DIG_SOURCE_OK=1)
        self.assertTrue(values["E28_MASTER_ENABLE"])

    def test_digital_stages_precede_analog_and_ready_needs_voltage(self):
        model = self.running()
        self.assertEqual([model.values[k] for k in self.enables], [1, 0, 0, 0, 0, 0, 0])
        for signal, expected in (
            ("DIG_PG0", [1, 1, 0, 0, 0, 0, 0]),
            ("DIG_PG1", [1, 1, 1, 0, 0, 0, 0]),
            ("DIG_PG2", [1, 1, 1, 1, 0, 0, 0]),
            ("DIG_PG3", [1, 1, 1, 1, 1, 0, 0]),
            ("ANA_PG0", [1, 1, 1, 1, 1, 1, 0]),
            ("ANA_PG1", [1, 1, 1, 1, 1, 1, 1]),
        ):
            values = model.settle(**{signal: 1})
            self.assertEqual([values[k] for k in self.enables], expected)
        values = model.settle(ANA_PG2=1)
        self.assertFalse(values["E28_OUTPUT_READY"])
        values = model.settle(ANA_OUTPUT_OK=1, DIG_OUTPUT_OK=1)
        self.assertTrue(values["E28_OUTPUT_READY"])

    def test_ov_and_source_uv_require_a_fresh_manual_run_cycle(self):
        for fault in (
            "P19_OV_OK",
            "N19_OV_OK",
            "P12_OV_OK",
            "N12_OV_OK",
            "V5_REG_OV_OK",
            "5V_DIG_OV_OK",
            "REF_LOW_OK",
            "REF_HIGH_OK",
            "ANA_SOURCE_OK",
            "DIG_SOURCE_OK",
            "P03_SOURCES_READY",
        ):
            model = self.running()
            values = model.settle(**{fault: 0})
            self.assertTrue(values["E28_FAULT"], fault)
            self.assertFalse(any(values[k] for k in self.enables), fault)
            values = model.settle(**{fault: 1})
            self.assertFalse(any(values[k] for k in self.enables), fault)
            model.settle(POWER_RUN=0)
            values = model.settle(POWER_RUN=1)
            self.assertTrue(values["E28_MASTER_ENABLE"], fault)

    def test_never_valid_output_times_out_and_later_output_uv_latches(self):
        model = self.running()
        values = model.settle(E28_TIMEOUT=1)
        self.assertTrue(values["E28_FAULT"])
        model = self.running()
        model.settle(ANA_OUTPUT_OK=1, DIG_OUTPUT_OK=1)
        values = model.settle(ANA_OUTPUT_OK=0)
        self.assertTrue(values["E28_FAULT"])

    def test_aux_mask_holds_every_enable_off_even_with_all_pg_high(self):
        model = self.running()
        values = model.settle(
            E28_AUX_RESET_N=0, DIG_PG0=1, DIG_PG1=1, DIG_PG2=1, DIG_PG3=1, ANA_PG0=1, ANA_PG1=1, ANA_PG2=1
        )
        self.assertFalse(any(values[k] for k in self.enables))

    def test_rcb_role_and_nor_pinout_mutations_are_rejected(self):
        for ref, pin, net in (("U13", "4", "V2V5_AUX"), ("U21", "1", "E28_ARMED"), ("U30", "6", "ANA_PG1")):
            parts = components()
            part = next(p for p in parts if p["ref"] == ref)
            next(p for p in part["pins"] if p["number"] == pin)["net"] = net
            with self.assertRaises(AssertionError):
                contract(parts)


@unittest.skipIf(np is None, "NumPy required for network solve")
class FiniteCopperNetworkNumerics(unittest.TestCase):
    def test_series_parallel_network_with_floating_island_conserves_current_and_energy(self):
        from hardware.electronics.rail_disconnect.revision28.copper import solve_network

        u = np.array([0, 1, 1, 3])
        v = np.array([1, 2, 2, 4])
        g = np.array([0.5, 1 / 3, 1 / 6, 100.0])
        result = solve_network(u, v, g, 5, [0], [2], details=True)
        self.assertEqual(result["status"], "diagnostic_estimate")
        self.assertAlmostEqual(result["ohm"], 4, places=10)
        self.assertEqual(result["floating_unexcited_nodes"], 2)
        self.assertLess(result["relative_residual"], 1e-9)
        phi = result["voltage"]
        current = result["current_at_one_volt"]
        self.assertAlmostEqual(np.sum(g * (phi[u] - phi[v]) ** 2) / current**2, 4, places=10)
        permutation = np.array([2, 4, 1, 0, 3])
        renamed = solve_network(permutation[u], permutation[v], g, 5, [2], [1])
        self.assertAlmostEqual(renamed["ohm"], 4, places=10)
        self.assertEqual(solve_network(u, v, g, 5, [0], [3])["status"], "mesh_disconnected")


class TerminalAttachmentGeometry(unittest.TestCase):
    def test_actual_annulus_contains_all_barrels_and_locating_hole_stays_clear(self):
        import math

        from hardware.electronics.rail_disconnect.revision28.terminal_stitching import sites

        points = sites(0, 0)
        self.assertEqual(len(points), 8)
        for p in points:
            radius = math.hypot(*p)
            self.assertGreaterEqual(radius - 0.3, 2.35)
            self.assertLessEqual(radius + 0.3, 4.25)
            self.assertGreater(radius - 0.15 - 2.1, 0.25)
        self.assertGreater(
            min(math.dist(a, b) - 0.3 for i, a in enumerate(points) for b in points[i + 1 :]), 0.25
        )


class AuxiliaryRecenterRequirements(unittest.TestCase):
    def test_recenter_has_finite_window_margins_without_qualifying_load_or_brownout(self):
        from hardware.electronics.rail_disconnect.revision28.auxiliary import screen

        result = screen()
        self.assertTrue(result["receiver_within_current_logic_band"])
        self.assertGreater(result["startup_release_guard_v"], 0.02)
        self.assertGreater(result["u20_mr_static_high_margin_v"], 0.07)
        self.assertGreater(min(r["minimum_asserted_margin_v"] for r in result["reference_window"]), 0.03)
        self.assertFalse(result["complete_aux_load_ledger_closed"])
        self.assertFalse(result["physical_qualified"])
        self.assertFalse(
            result["partial_power"]["supervisor_propagation_and_actual_gate_turnoff_waveforms_measured"]
        )

    def test_oversupply_and_reference_ratio_mutation_do_not_pass_voltage_contract(self):
        from hardware.electronics.rail_disconnect.revision28.auxiliary import screen

        over = screen(receiver_interval=(2.5, 2.9))
        self.assertFalse(over["receiver_within_current_logic_band"])
        self.assertLess(over["reference_window"][0]["minimum_asserted_margin_v"], 0)
        parts = components()
        top = next(
            p
            for p in parts
            if p["ref"].startswith("R") and {x["net"] for x in p["pins"]} == {"V2V5_AUX", "REF_LOW_AUX"}
        )
        top["part"] = "1.24k 0.01% 5ppm"
        bad = screen(parts)
        self.assertLess(bad["reference_window"][0]["minimum_asserted_margin_v"], 0)


@unittest.skipIf(np is None, "NumPy required for actual native pad geometry")
class LocalizedInverterFeedback(unittest.TestCase):
    def test_feedback_lands_and_native_front_traces_stay_at_the_actual_opamp(self):
        import math

        from hardware.electronics.rail_disconnect.revision26.router import Router
        from hardware.electronics.rail_disconnect.revision28.manufacturer import ROOT

        tree = read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text())
        router = Router(tree)

        def pad(ref, pin):
            return next(p for p in router.by_ref[ref] if p["pin"] == str(pin))

        for op, ref, pin in ((1, "R51", 1), (2, "R51", 2), (6, "R54", 2), (7, "R54", 1)):
            source, target = pad("U8", op), pad(ref, pin)
            self.assertEqual(source["net"], target["net"])
            self.assertLess(math.dist(source["xy"], target["xy"]), 4)

            def physical_segment(node):
                points = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in ("start", "end")]
                return (
                    str(first(node, "layer")[1]) == "F.Cu"
                    and math.dist(points[0], source["xy"]) < 1e-6
                    and math.dist(points[1], target["xy"]) < 1e-6
                )

            self.assertTrue(any(physical_segment(node) for node in children(tree, "segment")))


class RetainedBipolarStartup(unittest.TestCase):
    def test_actual_protected_bulk_and_hard_off_pairs_are_audited_without_inrush_pass(self):
        from hardware.electronics.rail_disconnect.revision28.bipolar_startup import audit

        result = audit()
        self.assertFalse(result["build_ready"])
        self.assertEqual([r["rail"] for r in result["rows"]], ["P19", "N19", "P12", "N12"])
        self.assertEqual(
            [r["local_bulk_max_f"] for r in result["rows"]], [0.0018, 0.0018, 0.000264, 0.000264]
        )
        self.assertTrue(all(not r["current_or_slew_limit_present"] for r in result["rows"]))
        self.assertTrue(all(r["guaranteed_bulk_charge_time_s"] is None for r in result["rows"]))
        self.assertFalse(result["retained_fet_limits"]["hot_gate_leakage_guaranteed"])
        self.assertFalse(result["repair_proposal"]["additional_drop_budget_accepted"])

    def test_bulk_upstream_or_logical_gate_swap_cannot_satisfy_retained_contract(self):
        from hardware.electronics.rail_disconnect.revision28.bipolar_startup import audit

        for ref, pin, net in (("C4", "1", "P19_SRC"), ("Q1", "2", "P19_COMMON")):
            parts = components()
            part = next(p for p in parts if p["ref"] == ref)
            next(p for p in part["pins"] if p["number"] == pin)["net"] = net
            with self.assertRaises(AssertionError):
                audit(parts)


class CompleteNativeContracts(unittest.TestCase):
    @staticmethod
    def fixture():
        return read_sexpr("""(kicad_pcb (general (thickness 1.6))
          (layers (0 "F.Cu" signal) (31 "B.Cu" signal))
          (setup (pad_to_mask_clearance .05))
          (footprint "TEST" (layer "F.Cu") (at 110 110)
            (property "Reference" "U1") (property "Value" "DEVICE")
            (fp_rect (start -2 -1) (end 2 1) (layer "F.CrtYd") (width .05))
            (pad "1" smd custom (at -1 0) (size 1.2 .6)
              (layers "F.Cu" "F.Mask" "F.Paste") (net "/SIG")
              (solder_mask_margin .05) (solder_paste_margin_ratio -.1)
              (primitives (gr_poly (pts (xy -1 -1) (xy 1 -1) (xy 1 1)) (width 0) (fill yes))))
            (pad "1" smd rect (at -1 2) (size 1 .6) (layers "F.Cu") (net "/SIG"))
            (pad "2" thru_hole circle (at 1 0) (size 1.5 1.5) (drill .8)
              (layers "*.Cu" "*.Mask") (net "/GND")))
          (zone (net "/GND") (layer "B.Cu") (priority 1)
            (polygon (pts (xy 100 100) (xy 120 100) (xy 120 120))))
          (gr_rect (start 100 100) (end 130 130) (layer "Edge.Cuts") (width .05)))""")

    def test_normalized_metadata_and_fill_caches_do_not_masquerade_as_geometry(self):
        from hardware.electronics.rail_disconnect.revision28.native_contract_compare import differences

        source = self.fixture()
        candidate = copy.deepcopy(source)
        fp = children(candidate, "footprint")[0]
        fp.append(read_sexpr('(uuid "new-native-serializer-id")'))
        fp.append(read_sexpr("(locked yes)"))
        children(candidate, "zone")[0].append(
            read_sexpr('(filled_polygon (layer "B.Cu") (pts (xy 101 101) (xy 119 101) (xy 119 119)))')
        )
        first(children(candidate, "general")[0], "thickness")[1] = type(
            first(children(candidate, "general")[0], "thickness")[1]
        )("1.600000")
        self.assertTrue(differences(source, candidate)["contracts_equal"])

    def test_pad_body_and_zone_mutations_are_rejected_including_duplicate_pad_numbers(self):
        from hardware.electronics.rail_disconnect.revision28.native_contract_compare import differences

        for mutation in (
            "net",
            "drill",
            "size",
            "layer",
            "mask",
            "paste",
            "primitive",
            "pad_pose",
            "body",
            "zone",
        ):
            source = self.fixture()
            candidate = copy.deepcopy(source)
            fp = children(candidate, "footprint")[0]
            pads = children(fp, "pad")
            if mutation == "net":
                first(pads[0], "net")[1] = "/OTHER"
            elif mutation == "drill":
                first(pads[2], "drill")[1] = 0.9
            elif mutation == "size":
                first(pads[1], "size")[1] = 1.1
            elif mutation == "layer":
                first(pads[0], "layers").remove("F.Mask")
            elif mutation == "mask":
                first(pads[0], "solder_mask_margin")[1] = 0.1
            elif mutation == "paste":
                first(pads[0], "solder_paste_margin_ratio")[1] = -0.2
            elif mutation == "primitive":
                first(first(first(pads[0], "primitives"), "gr_poly"), "pts")[1][1] = -1.1
            elif mutation == "pad_pose":
                first(pads[0], "at")[1] = -1.1
            elif mutation == "body":
                first(first(fp, "fp_rect"), "end")[1] = 2.1
            else:
                first(first(children(candidate, "zone")[0], "polygon"), "pts")[1][1] = 101
            self.assertFalse(differences(source, candidate)["contracts_equal"], mutation)


class NativeBarrelReuse(unittest.TestCase):
    @unittest.skipIf(np is None, "NumPy required for physical routing masks")
    def test_refill_cut_option_keeps_real_foreign_copper_and_drills_blocked(self):
        from hardware.electronics.rail_disconnect.revision26 import router as aid
        from hardware.electronics.rail_disconnect.revision28.repair import Router

        saved = aid.STEP, aid.CLEARANCE
        try:
            aid.STEP, aid.CLEARANCE = 1, 0.2
            r = Router.__new__(Router)
            r.nx = r.ny = 20
            r.xx = np.arange(20)[:, None]
            r.yy = np.arange(20)[None, :]
            r.geometry = [
                dict(kind="rect", xy=(10, 10), size=(0.8, 0.8), net="FOREIGN", layers=(0,)),
                dict(kind="via", xy=(14, 10), radius=0.3, net="FOREIGN", layers=tuple(range(6))),
            ]
            r.plane_masks = {0: {"POUR": np.ones((20, 20), dtype=bool)}}
            r.inner_escape = True
            r.allow_pour_clearance = False
            r.cached = {}
            self.assertTrue(r.masks("SIGNAL", 0.2)[0][0, 8, 8])
            r.allow_pour_clearance = True
            r.cached = {}
            blocked, drills = r.masks("SIGNAL", 0.2)
            self.assertFalse(blocked[0, 8, 8])
            self.assertFalse(blocked[1, 8, 8])
            self.assertTrue(blocked[0, 10, 10])
            self.assertTrue(all(blocked[layer, 14, 10] for layer in range(6)))
            self.assertTrue(drills[14, 10])
        finally:
            aid.STEP, aid.CLEARANCE = saved

    def test_stencil_only_shapes_are_not_copper_or_phantom_drill_holes(self):
        from hardware.electronics.rail_disconnect.revision28.repair import ROOT, Router

        tree = read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text())
        for ref, kind, extra in (("STENCIL", "smd", ""), ("REAL_HOLE", "np_thru_hole", "(drill 3.2)")):
            tree.append(
                read_sexpr(f'''(footprint "test" (layer "F.Cu") (at 120 120)
              (property "Reference" "{ref}") (pad "" {kind} circle (at 0 0)
              (size 3.2 3.2) {extra} (layers "F.Paste")))''')
            )
        r = Router(tree)
        self.assertFalse(any(g.get("ref") == "STENCIL" for g in r.geometry))
        self.assertTrue(any(g.get("ref") == "REAL_HOLE" for g in r.geometry))
        self.assertFalse(
            any(g.get("ref") in ("Q1", "Q2") and g.get("pin") == "" and not g["layers"] for g in r.geometry)
        )

    def test_actual_setting_resistors_are_local_to_each_efuse(self):
        from hardware.electronics.rail_disconnect.revision28.repair import ROOT, Router

        board = Router(read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text()))
        for index, ref in enumerate(("U13", "U14", "U32", "U15", "U16", "U17", "U33")):
            domain = "ANA" if index < 3 else "DIG"
            channel = index if index < 3 else index - 3
            for suffix, pin in (("DVDT", "7"), ("ILM", "9")):
                net = f"E28_{domain}_{channel}_{suffix}"
                pads = [p for p in board.pads if p["net"] == net]
                self.assertEqual(len(pads), 2, net)
                self.assertEqual({p["ref"] for p in pads} & {ref}, {ref}, net)
                self.assertIn(pin, {p["pin"] for p in pads if p["ref"] == ref})
                self.assertLess(math.dist(pads[0]["xy"], pads[1]["xy"]), 15, net)

    def test_off_grid_barrel_is_reused_and_trace_attaches_to_actual_centre(self):
        from hardware.electronics.rail_disconnect.revision26 import router as aid
        from hardware.electronics.rail_disconnect.revision28.repair import Router

        saved = aid.STEP
        try:
            aid.STEP = 0.125
            r = Router.__new__(Router)
            r.board = read_sexpr(
                '(kicad_pcb (via (at110.1 110.1) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net 1)))'.replace(
                    "at110", "at 110"
                )
            )
            r.geometry = [dict(kind="via", xy=(10.1, 10.1), radius=0.3, net="TEST", layers=tuple(range(6)))]
            r.nets = {"TEST": 1}
            r.routes = []
            r.via("TEST", (10.125, 10.125))
            self.assertEqual(len(children(r.board, "via")), 1)
            r.path("TEST", 4, [(12, 10), (10.125, 10.125)], 0.2)
            end = first(children(r.board, "segment")[0], "end")
            self.assertEqual(list(map(float, end[1:])), [110.1, 110.1])
            r.via("TEST", (12, 12))
            self.assertEqual(len(children(r.board, "via")), 2)
        finally:
            aid.STEP = saved


@unittest.skipIf(
    np is None or importlib.util.find_spec("scipy") is None, "NumPy/SciPy required for component search"
)
class NativeComponentAnchors(unittest.TestCase):
    def test_force_guard_reads_normalized_filled_nets_and_preserves_antipads(self):
        from types import SimpleNamespace

        from hardware.electronics.rail_disconnect.revision28.force_guard import ForceGuard

        router = SimpleNamespace(nx=20, ny=20, xx=np.arange(20)[:, None], yy=np.arange(20)[None, :])
        tree = read_sexpr("""(kicad_pcb
          (zone (net "/5V_DIG_SRC") (layer "In1.Cu")
            (filled_polygon (layer "In1.Cu")
              (pts (xy 104 104) (xy 116 104) (xy 116 116) (xy 104 116)
                (xy 104 104) (xy 108 108) (xy 108 112) (xy 112 112)
                (xy 112 108) (xy 108 108) (xy 104 104)))))""")
        guard = ForceGuard(tree, router, 1)
        blocked, drills = guard.apply("SIGNAL", np.zeros((6, 20, 20), bool), np.zeros((20, 20), bool), 0.2)
        self.assertTrue(blocked[1, 14, 10])
        self.assertFalse(blocked[4, 14, 10])
        self.assertTrue(drills[14, 10])
        self.assertFalse(blocked[1, 10, 10])
        self.assertFalse(drills[10, 10])
        self.assertFalse(drills[18, 18])
        own, _ = guard.apply("5V_DIG_SRC", np.zeros((6, 20, 20), bool), np.zeros((20, 20), bool), 0.2)
        self.assertFalse(own.any())
        children(tree, "zone")[0].remove(children(children(tree, "zone")[0], "filled_polygon")[0])
        with self.assertRaises(AssertionError):
            ForceGuard(tree, router, 1)

    def test_accessible_anchor_is_used_when_nearest_real_anchor_is_trapped(self):
        from hardware.electronics.rail_disconnect.revision26 import router as aid
        from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components

        class Corridor:
            nx = 10
            ny = 10

            def __init__(self):
                self.paths = []

            def masks(self, net, width):
                blocked = np.ones((6, 10, 10), bool)
                blocked[0, 1:9, 1] = False
                return blocked, np.ones((10, 10), bool)

            def existing_via(self, net, point):
                return None

            def path(self, net, layer, points, width):
                self.paths.append((net, layer, points, width))

            def via(self, net, point):
                raise AssertionError("No drill is available in this real corridor")

        saved = aid.STEP
        try:
            aid.STEP = 1
            r = Corridor()
            row = dict(
                net="TEST",
                components=[
                    [dict(xy=(1, 8), layers=[0], kind="PAD"), dict(xy=(1, 1), layers=[0], kind="PAD")],
                    [dict(xy=(8, 1), layers=[0], kind="PAD")],
                ],
            )
            result = connect_components(r, row)
            self.assertTrue(result["connected"])
            self.assertEqual(result["source"]["xy"], (1, 1))
            self.assertEqual(r.paths[0][2][0], (1, 1))
            self.assertEqual(r.paths[-1][2][-1], (8, 1))
            self.assertTrue(all(layer == 0 for _, layer, _, _ in r.paths))
        finally:
            aid.STEP = saved


@unittest.skipIf(np is None, "NumPy required for local geometry search")
class FilledPassiveEscapes(unittest.TestCase):
    def test_filled_via_uses_own_passive_land_but_keeps_foreign_pad_clearance(self):
        from hardware.electronics.rail_disconnect.revision26.router import Router
        from hardware.electronics.rail_disconnect.revision28.local_escapes import escape

        def board(foreign_x):
            return read_sexpr(f"""(kicad_pcb (net 1 "/TEST") (net 2 "/OTHER")
              (footprint "test" (layer "F.Cu") (at 120 120)
                (property "Reference" "C")
                (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 1 "/TEST"))
                (pad "2" smd rect (at {foreign_x} 0) (size 1 1) (layers "F.Cu") (net 2 "/OTHER"))))""")

        clear = Router(board(2))
        result, reason = escape(clear, clear.by_ref["C"][0], maxdistance=0.25)
        self.assertIsNone(reason)
        self.assertEqual(result["via"], (20, 20))
        self.assertEqual(len(children(clear.board, "via")), 1)
        blocked = Router(board(0.8))
        result, reason = escape(blocked, blocked.by_ref["C"][0], maxdistance=0.25)
        self.assertIsNone(result)
        self.assertEqual(len(children(blocked.board, "via")), 0)


@unittest.skipIf(np is None, "NumPy required for native-copper electrode diagnostics")
class CompleteTerminalElectrodes(unittest.TestCase):
    def test_crossing_row_raster_preserves_boundary_and_concave_cells(self):
        import numpy as np

        from hardware.electronics.rail_disconnect.revision28.copper import Mesh
        from hardware.electronics.rail_disconnect.revision28.distributed_mesh import DistributedBarrelMesh

        reference, accelerated = Mesh.__new__(Mesh), DistributedBarrelMesh.__new__(DistributedBarrelMesh)
        for mesh in (reference, accelerated):
            mesh.x = np.arange(-2, 4.01, 0.125)
            mesh.y = np.arange(-2, 4.01, 0.125)
            mesh.mask = np.zeros((2, len(mesh.x), len(mesh.y)), dtype=bool)
        # Exact grid-aligned edges/vertices, a concavity, off-grid rotation,
        # clipped shapes, reversed winding and a zero-height polygon.
        contours = [
            [(0, 0), (2, 0), (2, 2), (1, 1), (0, 2)],
            [(-3, -1), (0.375, 2.125), (3.125, -0.875)],
            [(0, 0), (1, 0), (2, 0)],
        ]
        for layer in range(2):
            for points in contours:
                reference.polygon(layer, points if layer else points[::-1])
                accelerated.polygon(layer, points if layer else points[::-1])
                np.testing.assert_array_equal(reference.mask, accelerated.mask)
        self.assertTrue(accelerated.mask[0, 20, 20])
        self.assertFalse(accelerated.mask[0, 0, 0])

    def test_distributed_wall_matches_closed_form_uniform_tube(self):
        from hardware.electronics.rail_disconnect.revision28.copper import ALPHA, RHO_BARREL20, STACKUP
        from hardware.electronics.rail_disconnect.revision28.distributed_mesh import DistributedBarrelMesh

        tree = read_sexpr(
            '(kicad_pcb (via (at 120 120) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net "/TEST")))'
        )
        mesh = DistributedBarrelMesh(tree, "TEST", 0.05, dict(pad_polygons=[]))
        mesh.pads = {("A", "1"): {0: mesh.mask[0].copy()}, ("B", "1"): {5: mesh.mask[5].copy()}}
        result = mesh.resistance([("A", "1")], [("B", "1")])
        length = (
            STACKUP["copper_center_nominal_depth_mm"][-1] - STACKUP["copper_center_nominal_depth_mm"][0]
        ) * (STACKUP["laminate_thickness_mm"]["maximum"] / STACKUP["laminate_thickness_mm"]["nominal"])
        expected = RHO_BARREL20 * (1 + ALPHA * 65) * length / (math.pi * (0.175**2 - 0.15**2))
        self.assertAlmostEqual(result["ohm"], expected, places=12)
        self.assertFalse(mesh.distributed_barrel_diagnostic["within_layer_annuli_shorted"])
        self.assertFalse(mesh.distributed_barrel_diagnostic["certified_resistance_upper_bound"])

    def test_distributed_annuli_retain_nonuniform_terminal_spreading(self):
        from hardware.electronics.rail_disconnect.revision28.distributed_mesh import DistributedBarrelMesh
        from hardware.electronics.rail_disconnect.revision28.native_mesh import NativePadMesh

        tree = read_sexpr(
            '(kicad_pcb (via (at 120 120) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net "/TEST")))'
        )
        estimates = []
        for cls in (NativePadMesh, DistributedBarrelMesh):
            mesh = cls(tree, "TEST", 0.05, dict(pad_polygons=[]))
            mesh.pads = {
                ("A", "1"): {0: mesh.mask[0] & (mesh.x[:, None] < 20)},
                ("B", "1"): {5: mesh.mask[5] & (mesh.x[:, None] > 20)},
            }
            estimates.append(mesh.resistance([("A", "1")], [("B", "1")])["ohm"])
        self.assertGreater(estimates[1], estimates[0])

    def test_fine_barrel_route_reuses_own_net_but_rejects_foreign_target(self):
        from types import SimpleNamespace

        from hardware.electronics.rail_disconnect.revision28.ground_corridor import path_between

        own = dict(kind="via", xy=(24, 20), radius=0.3, layers=(1,), net="TEST")
        points, _ = path_between(
            SimpleNamespace(geometry=[own]), (20, 20), (24, 20), 1, net="TEST", margin=1, step=0.1
        )
        self.assertEqual(points[0], (20, 20))
        self.assertEqual(points[-1], (24, 20))
        with self.assertRaises(AssertionError):
            path_between(
                SimpleNamespace(geometry=[dict(own, net="OTHER")]),
                (20, 20),
                (24, 20),
                1,
                net="TEST",
                margin=1,
                step=0.1,
            )

    def test_fine_barrel_route_cannot_cross_a_real_foreign_copper_barrier(self):
        from types import SimpleNamespace

        from hardware.electronics.rail_disconnect.revision28.ground_corridor import path_between

        wall = dict(kind="line", start=(22, 0), end=(22, 45.25), width=0.2, layers=(1,), net="OTHER")
        with self.assertRaisesRegex(AssertionError, "No actual local clearance path"):
            path_between(
                SimpleNamespace(geometry=[wall]), (20, 20), (24, 20), 1, net="TEST", margin=1, step=0.1
            )

    def test_domain_rejects_partially_overlapping_outboard_terminal(self):
        from hardware.electronics.rail_disconnect.revision28.native_mesh import NativePadMesh

        geometry = dict(
            pad_polygons=[
                dict(
                    ref="J4",
                    pin="1",
                    net="TEST",
                    position_mm=[257.3, 128.5],
                    drill_mm=[0, 0],
                    nominal_size_mm=[3, 3],
                    layers={
                        "F.Cu": [
                            dict(outer=[(255.8, 127), (258.8, 127), (258.8, 130), (255.8, 130)], holes=[])
                        ]
                    },
                )
            ]
        )
        tree = read_sexpr("(kicad_pcb)")
        # A nonempty sliver at x155.8..156 must not count as a complete contact.
        with self.assertRaisesRegex(AssertionError, "Copper outside extraction domain"):
            NativePadMesh(tree, "TEST", 0.2, geometry)
        mesh = NativePadMesh(tree, "TEST", 0.2, geometry, bounds=(159.3, 45.25))
        self.assertTrue(mesh.domain_coverage["full_native_pad_coverage_checked"])
        self.assertGreater(np.count_nonzero(mesh.pads[("J4", "1")][0]), 100)

    def test_return_contact_face_is_applied_before_network_build(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from hardware.electronics.rail_disconnect.revision28 import coupled

        seen = []
        regions = {i: np.ones((1, 1), bool) for i in (0, 5)}
        mesh = SimpleNamespace(pads={(r, "2"): regions.copy() for r in ("J3", "J4")})

        def network():
            seen.append({key: set(value) for key, value in mesh.pads.items()})
            return dict(u=[], v=[], g=[], n=1, electrodes=lambda keys: np.array([0]))

        mesh.network = network
        with tempfile.TemporaryDirectory() as directory:
            board = Path(directory) / "test.kicad_pcb"
            board.write_text("(kicad_pcb)")
            with (
                patch.object(coupled, "make_mesh", return_value=mesh),
                patch.object(coupled, "solve_network", return_value=dict(status="unresolved_test_network")),
            ):
                row = coupled.returns(board, load_contact_layer="F.Cu")
        self.assertEqual(seen, [{("J3", "2"): {0}, ("J4", "2"): {0}}])
        self.assertFalse(row["all_load_pad_layers_clamped"])

    def test_native_compound_pad_adapter_keeps_all_lands_and_actual_drills(self):
        from hardware.electronics.rail_disconnect.revision28.bipolar_copper import NativePadMesh

        tree = read_sexpr("""(kicad_pcb
          (footprint "CUSTOM" (layer "F.Cu") (at 120 120)
            (property "Reference" "Q1")
            (pad "3" smd custom (at 0 0) (size .01 .01) (layers "F.Cu") (net "/P12")))
          (via (at 120 120) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net "/P12")))""")
        shapes = [
            [(119, 119.8), (121, 119.8), (121, 120.2), (119, 120.2)],
            [(122, 119), (124, 119), (122, 121)],
        ]
        geometry = dict(
            pad_polygons=[
                dict(
                    ref="Q1",
                    pin="3",
                    net="P12",
                    position_mm=[120, 120],
                    drill_mm=[0, 0],
                    nominal_size_mm=[0.01, 0.01],
                    layers={"F.Cu": [dict(outer=shape, holes=[])]},
                )
                for shape in shapes
            ]
        )
        mesh = NativePadMesh(tree, "P12", 0.1, geometry)
        region = mesh.pads[("Q1", "3")][0]
        for x, y in ((19.5, 20.05), (22.2, 19.2)):
            i, j = np.argmin(abs(mesh.x - x)), np.argmin(abs(mesh.y - y))
            self.assertTrue(region[i, j])
        i, j = np.argmin(abs(mesh.x - 20.05)), np.argmin(abs(mesh.y - 20.05))
        self.assertFalse(mesh.mask[0, i, j])

    def test_face_contact_does_not_clamp_every_plated_hole_layer(self):
        from hardware.electronics.rail_disconnect.revision28.coupled import restrict_pad_contact_layer

        tree = read_sexpr("""(kicad_pcb
          (footprint "TEST" (layer "F.Cu") (at 120 120)
            (property "Reference" "J4")
            (pad "1" thru_hole circle (at 0 0) (size 4.2 4.2) (drill 2.2)
              (layers "*.Cu" "*.Mask") (net "/TEST"))))""")
        mesh = Mesh(tree, "TEST", 0.2)
        physical = mesh.mask.copy()
        holes = copy.deepcopy(mesh.holes)
        before = mesh.network()
        self.assertEqual(len(np.unique(before["electrodes"]([("J4", "1")]))), 6)
        row = restrict_pad_contact_layer(mesh, "J4", "1", "F.Cu")
        after = mesh.network()
        self.assertEqual(len(np.unique(after["electrodes"]([("J4", "1")]))), 1)
        self.assertTrue(np.array_equal(mesh.mask, physical))
        self.assertEqual(mesh.holes, holes)
        self.assertFalse(row["interface_assembly_bound_accepted"])

    def test_stud_contact_scenario_preserves_outer_conducting_copper(self):
        from hardware.electronics.rail_disconnect.revision28.coupled import restrict_stud_electrode

        fp = copy.deepcopy(terminal())
        fp.append(read_sexpr("(at 120 120 0)"))
        first(fp, "property")[2] = "J7"
        children(fp, "pad")[0].append(read_sexpr('(net "/AGND")'))
        tree = ["kicad_pcb", fp]
        mesh = Mesh(tree, "AGND", 0.1)
        actual_copper = mesh.mask.copy()
        row = restrict_stud_electrode(mesh, tree, "J7", 3.5)
        self.assertLess(row["scenario_electrode_cells"], row["original_electrode_cells"])
        self.assertTrue(np.array_equal(mesh.mask, actual_copper))
        self.assertFalse(row["manufacturer_or_assembler_contact_bound_accepted"])
        i, j = np.argmin(abs(mesh.x - 24)), np.argmin(abs(mesh.y - 20))
        self.assertTrue(mesh.mask[0, i, j])
        self.assertFalse(mesh.pads[("J7", "1")][0][i, j])

    def test_repeated_source_lands_are_unioned_on_each_actual_layer(self):
        tree = read_sexpr("""(kicad_pcb
          (footprint "test" (layer "F.Cu") (at 110 110)
            (property "Reference" "Q")
            (pad "1" smd rect (at 0 -1) (size 1 1) (layers "F.Cu") (net "/TEST"))
            (pad "1" smd rect (at 0 1) (size 1 1) (layers "F.Cu") (net "/TEST"))
            (pad "1" smd rect (at 0 3) (size 1 1) (layers "B.Cu") (net "/TEST"))))""")
        mesh = Mesh(tree, "TEST", 0.1)
        regions = mesh.pads[("Q", "1")]
        self.assertEqual(set(regions), {0, 5})
        self.assertEqual(np.count_nonzero(regions[0]), 200)
        self.assertEqual(np.count_nonzero(regions[5]), 100)
        # The old E27 assignment overwrote the F.Cu source lands entirely.
        self.assertGreater(np.count_nonzero(regions[0]), np.count_nonzero(regions[5]))

    def test_annular_electrode_does_not_become_a_solid_disc(self):
        fp = copy.deepcopy(terminal())
        fp.append(read_sexpr("(at 120 120 0)"))
        first(fp, "property")[2] = "J7"
        children(fp, "pad")[0].append(read_sexpr('(net "/AGND")'))
        mesh = Mesh(["kicad_pcb", fp], "AGND", 0.1)
        regions = mesh.pads[("J7", "1")]
        i = np.argmin(abs(mesh.x - 20))
        j = np.argmin(abs(mesh.y - 20))
        self.assertFalse(regions[0][i, j])
        self.assertTrue(regions[0][i + 33, j])


class ActualAuxResetReceiving(unittest.TestCase):
    def test_actual_aup_receiver_and_old_static_pass_are_not_confused_with_2g17(self):
        from hardware.electronics.rail_disconnect.revision28.reset_pullup import screen

        actual = next(p for p in components() if p["ref"] == "U31")
        self.assertEqual(actual["part"], "SN74AUP2G08DCUR")
        self.assertEqual(next(p for p in actual["pins"] if p["number"] == "5")["net"], "E28_AUX_RESET_N")
        old, new = screen(100000), screen(10000)
        self.assertAlmostEqual(old["HIGH_min_v"], 2.2195)
        self.assertGreater(old["static_high_margin_v"], 0)
        self.assertAlmostEqual(old["allowable_total_node_C_f"] / 1e-12, 1.214705882352941)
        self.assertAlmostEqual(new["HIGH_min_v"], 2.47195)
        self.assertAlmostEqual(new["allowable_total_node_C_f"] / 1e-12, 17.09705882352941)
        self.assertLess(new["RESET_LOW_sink_allocation_a"], 0.0004)
        self.assertFalse(new["actual_node_C_trace_via_Coff_probe_and_received_slew_accepted"])
        self.assertFalse(new["physical_and_fabrication_qualified"])

    def test_selected_panasonic_lands_reject_generic_pitch_and_undersized_courtyard(self):
        from hardware.electronics.rail_disconnect.revision28.reset_pullup import (
            validate_footprint,
        )
        from hardware.electronics.rail_disconnect.revision28.reset_pullup_candidate2 import (
            WORK,
        )

        fp = read_sexpr((WORK / "RMX_E28.pretty/Resistor_SMD_Panasonic_ERA6A_2012.kicad_mod").read_text())
        self.assertTrue(validate_footprint(fp))
        generic = copy.deepcopy(fp)
        first(children(generic, "pad")[0], "at")[1] = -0.9125
        with self.assertRaises(AssertionError):
            validate_footprint(generic)
        cramped = copy.deepcopy(fp)
        rect = next(r for r in children(cramped, "fp_rect") if first(r, "layer")[1] == "F.CrtYd")
        first(rect, "start")[1] = -1.68
        with self.assertRaises(AssertionError):
            validate_footprint(cramped)


class ActualTripleSchmittReadyRepair(unittest.TestCase):
    def parts(self):
        import json

        from hardware.electronics.rail_disconnect.revision28.reset_buffer_candidate4 import WORK

        return json.loads((WORK / "components.json").read_text())

    def test_actual_triple_pin_contract_and_fail_closed_ready_without_start_deadlock(self):
        import itertools

        parts = self.parts()
        contract(parts)
        for bits in itertools.product((0, 1), repeat=6):
            pg3, pg2, ana, dig, nf, aux = bits
            model = StaticLogic(parts)
            model.settle(**safe_inputs(parts))
            values = model.settle(
                E28_AUX_RESET_RAW=aux,
                POWER_RUN=1,
                P03_SOURCES_READY=1,
                ANA_SOURCE_OK=1,
                DIG_SOURCE_OK=1,
                DIG_PG0=1,
                DIG_PG1=1,
                DIG_PG2=1,
                DIG_PG3=pg3,
                ANA_PG0=1,
                ANA_PG1=1,
                ANA_PG2=pg2,
                ANA_OUTPUT_OK=ana,
                DIG_OUTPUT_OK=dig,
                NF_OUTPUT_VALID_RAW=nf,
            )
            self.assertEqual(values["E28_OUTPUT_READY"], values["POS_OUTPUT_READY"] & nf)
            self.assertEqual(values["E28_MASTER_ENABLE"], aux)
            if not nf or not aux or not pg3 or not pg2 or not ana or not dig:
                self.assertFalse(values["E28_OUTPUT_READY"])
        mutated = copy.deepcopy(parts)
        buffer = next(c for c in mutated if c["ref"] == "U35")
        next(p for p in buffer["pins"] if p["number"] == "2")["net"] = "E28_MASTER_ENABLE"
        with self.assertRaises(AssertionError):
            contract(mutated)
        bypassed = copy.deepcopy(parts)
        gate = next(c for c in bypassed if c["ref"] == "U25")
        next(p for p in gate["pins"] if p["number"] == "5")["net"] = "V2V5_AUX"
        with self.assertRaises(AssertionError):
            contract(bypassed)

    def test_manufacturer_triple_and_bypass_lands_reject_wrong_dimensions(self):
        from hardware.electronics.rail_disconnect.revision28.reset_buffer_patterns import (
            bypass,
            triple,
            validate,
        )

        for fp in (triple(), bypass()):
            validate(fp)
            damaged = copy.deepcopy(fp)
            first(children(damaged, "pad")[0], "size")[1] = 0.5
            with self.assertRaises(AssertionError):
                validate(damaged)
            swapped = copy.deepcopy(fp)
            children(swapped, "pad")[0][1] = "8" if len(children(fp, "pad")) == 8 else "2"
            with self.assertRaises(AssertionError):
                validate(swapped)


class ActualViaEdgeRegression(unittest.TestCase):
    def test_every_planned_barrel_clears_the_declared_rectangular_board_edges(self):
        from hardware.electronics.rail_disconnect.revision28.band_router import BandRouter

        planner = BandRouter.__new__(BandRouter)
        planner.nx, planner.ny = 3121, 1091
        planner.xx = np.arange(planner.nx)[:, None] * 0.05
        planner.yy = np.arange(planner.ny)[None, :] * 0.05
        planner.geometry = []
        _, via_block = planner.physical_masks("TEST", 0.2)
        x, y = np.broadcast_arrays(planner.xx, planner.yy)
        edge_distance = np.minimum.reduce([x, 156 - x, y, 54.5 - y])
        self.assertTrue(np.all(edge_distance[~via_block] - 0.3 >= 0.5))
        self.assertTrue(via_block[round(90.85 / 0.05), round(53.75 / 0.05)])


class ActualSMTReadyReceiving(unittest.TestCase):
    def test_real_tabs_and_barrelless_smt_lands_do_not_become_fake_ground_terminals(self):
        from hardware.electronics.rail_disconnect.revision28.ready_smt_connector import validate
        from hardware.electronics.rail_disconnect.revision28.ready_smt_tail_repair import WORK

        fp = read_sexpr((WORK / "RMX_E28.pretty/JST_B2B_PH_SM4_TB_MechanicalLands.kicad_mod").read_text())
        self.assertTrue(validate(fp))
        missing = copy.deepcopy(fp)
        missing.remove(next(p for p in children(missing, "pad") if not p[1]))
        with self.assertRaises(AssertionError):
            validate(missing)
        fictional_ground = copy.deepcopy(fp)
        next(p for p in children(fictional_ground, "pad") if not p[1]).append(read_sexpr('(net 15 "/AGND")'))
        with self.assertRaises(AssertionError):
            validate(fictional_ground)
        drilled = copy.deepcopy(fp)
        children(drilled, "pad")[0].append(read_sexpr("(drill .75)"))
        with self.assertRaises(AssertionError):
            validate(drilled)

    def test_loaded_nf_output_and_supervisor_corner_inferences_remain_explicit(self):
        from hardware.electronics.rail_disconnect.revision28.reset_buffer_receiving import screen

        r = screen()
        self.assertAlmostEqual(r["supervisor_high_receiving_v"], 2.42605)
        self.assertAlmostEqual(r["NF_conditional_static_high_margin_v"], 0.1)
        self.assertAlmostEqual(r["NF_source_load_allocation_a"] * 1e6, 189.2680412371134)
        self.assertLess(r["supervisor_low_sink_times1p2_a"], 0.0004)
        self.assertEqual(r["NF_U49_rated_temperature_C"], [-40, 85])
        self.assertFalse(r["continuous_VCC_intermediate_VI_current_transfer_verified"])
        self.assertFalse(r["partial_VCC_0_to_1p65V_failOFF_dynamic_capture_accepted"])
        self.assertFalse(r["physical_and_fabrication_qualified"])


class PhysicalSupervisorPinRegression(unittest.TestCase):
    def test_primary_reset6_vdd4_contract_rejects_a_parity_consistent_symbol_swap(self):
        from hardware.electronics.rail_disconnect.revision28.supervisor_pin_audit import component_contract

        for part in components():
            if not part["part"].startswith("TPS3890"):
                continue
            component_contract(part)
            wrong = copy.deepcopy(part)
            for p in wrong["pins"]:
                if p["number"] == "4":
                    p["number"] = "6"
                elif p["number"] == "6":
                    p["number"] = "4"
            with self.assertRaises(AssertionError):
                component_contract(wrong)

    def test_actual_mirrored_board_lands_do_not_swap_supply_and_reset(self):
        import json

        from hardware.electronics.rail_disconnect.revision28.supervisor_pin_audit import (
            SOURCE,
            board_contract,
        )

        parts = {p["ref"]: p for p in json.loads((SOURCE / "components.json").read_text())}
        tree = read_sexpr((SOURCE / "rail_disconnect.kicad_pcb").read_text())
        for fp in children(tree, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            if ref not in ("U19", "U20"):
                continue
            board_contract(parts[ref], fp)
            wrong = copy.deepcopy(fp)
            four = next(p for p in children(wrong, "pad") if p[1] == "4")
            six = next(p for p in children(wrong, "pad") if p[1] == "6")
            first(four, "net")[:], first(six, "net")[:] = (
                copy.deepcopy(first(six, "net")),
                copy.deepcopy(first(four, "net")),
            )
            with self.assertRaises(AssertionError):
                board_contract(parts[ref], wrong)


class AllOpenCollectorSchmittReceiving(unittest.TestCase):
    def test_all_actual_slow_nodes_have_one_schmitt_receiver_and_bounded_load(self):
        import json

        from hardware.electronics.rail_disconnect.revision28.schmitt_cone_contract import SOURCE, contract

        parts = json.loads((SOURCE / "components.json").read_text())
        rows = contract(parts)
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(r["load_allocation_uA"] < 100 for r in rows))
        wrong = copy.deepcopy(parts)
        for part in wrong:
            if part["ref"] == "U11":
                next(p for p in part["pins"] if p["number"] == "1")["net"] = "P19_OV_OK"
        with self.assertRaises(AssertionError):
            contract(wrong)
        wrong = copy.deepcopy(parts)
        for part in wrong:
            if part["ref"] == "U42":
                next(p for p in part["pins"] if p["number"] == "3")["net"] = None
        with self.assertRaises(AssertionError):
            contract(wrong)

    def test_steady_equivalence_is_not_a_received_edge_or_partial_power_pass(self):
        import json

        from hardware.electronics.rail_disconnect.revision28.schmitt_cone_contract import SOURCE

        report = json.loads((SOURCE / "generated/receiving-audit.json").read_text())
        self.assertEqual(len(report["steady_boolean_cases"]), 64)
        self.assertEqual(report["continuous_output_rows"]["max_load_uA"], 100)
        self.assertFalse(report["received_output_edge_required"]["buffer_output_rise_fall_max_specified"])
        self.assertFalse(
            report["received_output_edge_required"]["assembled_node_C_and_rise_fall_capture_accepted"]
        )
        self.assertFalse(report["partial_AUX_failOFF_accepted"])
        self.assertFalse(report["physical_qualified"])


class Actual0402ReceivingBypass(unittest.TestCase):
    def test_primary_density_b0402_lands_and_courtyard_reject_mutation(self):
        from hardware.electronics.rail_disconnect.revision28.c79_0402_candidate import pattern, validate

        fp = pattern()
        self.assertTrue(validate(fp))
        wrong = copy.deepcopy(fp)
        first(children(wrong, "pad")[0], "at")[1] = -0.5
        with self.assertRaises(AssertionError):
            validate(wrong)
        wrong = copy.deepcopy(fp)
        first(children(wrong, "pad")[0], "size")[1] = 0.61
        with self.assertRaises(AssertionError):
            validate(wrong)
        wrong = copy.deepcopy(fp)
        children(wrong, "pad")[0][3] = "roundrect"
        with self.assertRaises(AssertionError):
            validate(wrong)

    def test_physical_graph_cut_never_relabels_a_source_or_hysteresis_terminal(self):
        import json

        from hardware.electronics.rail_disconnect.revision28.schmitt_backbone_cut_plan import partition
        from hardware.electronics.rail_disconnect.revision28.schmitt_cone_candidate import ROOT

        graph = json.loads(
            (ROOT / "generated/schmitt-cone-proposal/native-backbone-direct-graph.json").read_text()
        )
        plans = json.loads((ROOT / "generated/schmitt-cone-proposal/backbone-cut-plan.json").read_text())
        for net in ("P19_OV_OK", "N19_OV_OK", "P12_OV_OK"):
            row = graph["rows"][net]
            self.assertTrue(row["direct_shape_components_equal_native_transitive_clusters"])
            cut = set(plans["rows"][net]["cut_track_uuids"])
            buffered, roots, receivers = partition(row, cut)
            self.assertFalse(buffered & roots)
            self.assertTrue(receivers <= buffered)
            with self.assertRaises(AssertionError):
                partition(row, set())
            with self.assertRaises(AssertionError):
                partition(row, cut | {next(iter(roots))})


class LogicalNetDeltaContracts(unittest.TestCase):
    def test_transient_numeric_code_cannot_change_the_physical_ground_net(self):
        from hardware.electronics.rail_disconnect.revision28.merge_external_closures import retarget

        # Actual captured generations used7 for AGND and15 for AGND;
        # code7 in the newer board instead meant5V_DIG_MCAP1_LIMIT.
        segment = read_sexpr(
            '(segment (start 163.35 153.4) (end 163.275 153.475) (width 0.2) (layer "F.Cu") (net 7))'
        )
        retarget(segment, {"AGND": "15", "5V_DIG_MCAP1_LIMIT": "7"}, {"7": "AGND"})
        self.assertEqual([str(v) for v in first(segment, "net")], ["net", "15"])
        self.assertEqual([float(v) for v in first(segment, "start")[1:3]], [163.35, 153.4])

    def test_native_track_net_clause_and_pad_net_clause_are_different(self):
        from hardware.electronics.rail_disconnect.revision28.merge_external_closures import retarget

        segment = read_sexpr('(segment (start 1 2) (end 3 4) (net "/V2V5_AUX"))')
        pad = read_sexpr('(pad "1" smd rect (at 0 0) (net "/V2V5_AUX"))')
        retarget(segment, {"V2V5_AUX": "94"})
        retarget(pad, {"V2V5_AUX": "94"})
        self.assertEqual([str(v) for v in first(segment, "net")], ["net", "94"])
        self.assertEqual([str(v) for v in first(pad, "net")], ["net", "94", "/V2V5_AUX"])

    def test_unknown_external_net_is_rejected_before_a_candidate_is_written(self):
        from hardware.electronics.rail_disconnect.revision28.merge_external_closures import retarget

        with self.assertRaises(AssertionError):
            retarget(read_sexpr('(segment (net "/UNKNOWN_EXTERNAL_NET"))'), {"AGND": "15"})


class ActualAUPInputCommutation(unittest.TestCase):
    def test_same_gate_commutation_preserves_both_physical_gate_signatures(self):
        import json

        from hardware.electronics.rail_disconnect.revision28.aup_gate_commutation import verify
        from hardware.electronics.rail_disconnect.revision28.pg_master_local_repair import SOURCE, WORK

        before = next(p for p in json.loads((SOURCE / "components.json").read_text()) if p["ref"] == "U34")
        after = next(p for p in json.loads((WORK / "components.json").read_text()) if p["ref"] == "U34")
        self.assertTrue(verify(before, after))
        pins = {p["number"]: p["net"] for p in after["pins"]}
        self.assertEqual(pins["1"], "DIG_PG2_SCHMITT")
        self.assertEqual(pins["2"], "E28_MASTER_ENABLE")
        self.assertEqual(pins["7"], "E28_DIG_FOLLOW3")
        # A same-package exchange with another gate is not a commutation.
        wrong = copy.deepcopy(after)
        one = next(p for p in wrong["pins"] if p["number"] == "1")
        six = next(p for p in wrong["pins"] if p["number"] == "6")
        one["net"], six["net"] = six["net"], one["net"]
        with self.assertRaises(AssertionError):
            verify(before, wrong)


if __name__ == "__main__":
    unittest.main()
