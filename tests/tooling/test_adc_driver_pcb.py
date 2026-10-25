"""Characterization routing must not masquerade as converter-loop qualification."""

import copy
import json
import unittest
from pathlib import Path

from hardware.electronics.adc_driver.pcb import check, paths
from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.reports import sha
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr


class AdcDriverPcbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = read_sexpr((check.ROOT / "adc_driver.kicad_pcb").read_text())
        cls.filled = read_sexpr((check.OUT / "filled.kicad_pcb").read_text())
        cls.parts, cls.pins = netlist(check.PARENT / "generated/netlist.xml")

    def test_source_contract_and_actual_native_copper(self):
        self.assertEqual(len(check.inspect(self.tree, self.parts, self.pins)), 79)
        self.assertEqual(len(paths.local_feedback(self.filled)), 24)
        self.assertEqual(len(paths.header_sense_contract(self.filled)), 4)
        self.assertEqual(
            paths.ground_contract(self.filled)["ground_lands_with_local_actual_plane_contact"], 45
        )

    def test_missing_ic_and_wrong_reference_pin_are_rejected(self):
        for change in ("missing", "wrong_net"):
            tree = copy.deepcopy(self.tree)
            fp = next(
                f
                for f in children(tree, "footprint")
                if any(p[1:3] == ["Reference", "U4"] for p in children(f, "property"))
            )
            if change == "missing":
                tree.remove(fp)
            else:
                first(next(p for p in children(fp, "pad") if p[1] == "3"), "net")[-1] = "/V5_REG"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                check.inspect(tree, self.parts, self.pins)

    def test_removed_or_narrow_feedback_copper_is_rejected(self):
        for remove in (True, False):
            tree = copy.deepcopy(self.tree)
            code = next(n[1] for n in children(tree, "net") if n[2] == "/FB_N_L")
            segments = [s for s in children(tree, "segment") if first(s, "net")[1] == code]
            for segment in segments:
                if remove:
                    tree.remove(segment)
                else:
                    first(segment, "width")[1] = 0.1
            with self.subTest(remove=remove), self.assertRaises(AssertionError):
                paths.local_feedback(tree)

    def test_upstream_force_sense_merge_is_rejected(self):
        tree = copy.deepcopy(self.tree)
        code = next(n[1] for n in children(tree, "net") if n[2] == "/ADC_LP")
        # A deliberate upstream copper bridge defeats header sensing even though
        # an ordinary same-net connectivity check would accept it.
        tree.append(
            read_sexpr(
                f'(segment (start 120.9125 149) (end 118 140.4125) (width .25) (layer "F.Cu") (net {code}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "before J2"):
            paths.header_sense_contract(tree)

    def test_missing_inner_sense_route_is_rejected(self):
        tree = copy.deepcopy(self.filled)
        tree[:] = [
            n
            for n in tree
            if not (
                isinstance(n, list)
                and n
                and n[0] == "segment"
                and first(n, "net")[-1] == "/ADC_RN"
                and first(n, "layer")[1] == "In2.Cu"
            )
        ]
        with self.assertRaises(AssertionError):
            paths.header_sense_contract(tree)

    def test_missing_plane_fill_or_local_ground_escape_is_rejected(self):
        for change in ("fill", "vias"):
            tree = copy.deepcopy(self.filled)
            if change == "fill":
                zone = next(z for z in children(tree, "zone") if children(z, "filled_polygon"))
                zone.remove(children(zone, "filled_polygon")[0])
            else:
                tree[:] = [
                    n
                    for n in tree
                    if not (isinstance(n, list) and n and n[0] == "via" and first(n, "net")[-1] == "/AGND")
                ]
            with self.subTest(change=change), self.assertRaises(AssertionError):
                paths.ground_contract(tree)

    def test_foreign_signal_cannot_split_reference_plane(self):
        tree = copy.deepcopy(self.filled)
        tree.append(
            read_sexpr('(segment (start 110 130) (end 200 130) (width .5) (layer "In1.Cu") (net "/V5_REG"))')
        )
        with self.assertRaises(AssertionError):
            paths.ground_contract(tree)

    def test_reviewed_recipe_replays_exact_copper(self):
        recipe = json.loads((check.ROOT / "reviewed-copper.json").read_text())
        self.assertEqual(recipe["placed_pcb_sha256"], sha(check.OUT / "placed.kicad_pcb"))
        board = read_sexpr((check.OUT / "placed.kicad_pcb").read_text())
        board.extend(read_sexpr(n) for n in recipe["copper_s_expressions"])
        self.assertEqual(sexpr(board) + "\n", (check.ROOT / "adc_driver.kicad_pcb").read_text())

    def test_native_record_is_current_and_characterization_only(self):
        report = json.loads((check.OUT / "verification.json").read_text())
        for key in ("native_open_connections", "native_drc_violations", "schematic_parity_issues"):
            self.assertEqual(report[key], 0, key)
        for key in (
            "build_ready",
            "integrated_in_a11",
            "physical_fit_verified",
            "analog_stability_verified",
            "adc_noise_or_distortion_verified",
            "closed_converter_loop_verified",
            "header_sensing_is_converter_pin_kelvin",
            "high_impedance_leakage_or_guard_qualified",
            "production_parts_or_stackup_qualified",
        ):
            self.assertFalse(report[key], key)
        self.assertTrue(report["characterization_board_only"])
        self.assertTrue(report["final_codec_co_location_or_revised_force_sense_interface_required"])
        repo = Path(__file__).resolve().parents[2]
        for name, expected in report["source_sha256"].items():
            self.assertEqual(sha(repo / name), expected, name)

    def test_fine_pitch_exception_is_scoped_to_four_library_packages(self):
        rules = (check.ROOT / "adc_driver.kicad_dru").read_text()
        self.assertIn("(constraint clearance (min 0.25mm))", rules)
        self.assertIn("A.Type == 'Pad' && B.Type == 'Pad'", rules)
        for ref in ("U1", "U2", "U5", "U6"):
            self.assertIn(f"A.memberOfFootprint('{ref}')", rules)
        self.assertEqual(
            json.loads((check.ROOT / "adc_driver.kicad_pro").read_text())["board"]["design_settings"][
                "rules"
            ]["min_clearance"],
            0.15,
        )


if __name__ == "__main__":
    unittest.main()
