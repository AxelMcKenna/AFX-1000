"""Headless tests for shared EDA utilities and independently authored board contracts."""

import importlib
import math
import pkgutil
import tempfile
import unittest
from pathlib import Path

from hardware.electronics import common
from hardware.electronics.common.circuits import LU, linear_solve
from hardware.electronics.common.netlists import netlist, number
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.reports import source_hashes
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr


class ElectronicsTests(unittest.TestCase):
    def test_component_units(self):
        for text, expected in [("4.7uF film", 4.7e-6), ("100k 1%", 100000), ("1M", 1e6), ("4.3R", 4.3)]:
            self.assertTrue(math.isclose(number(text), expected))
        with self.assertRaises(ValueError):
            number("invalid")

    def test_complex_solver_pivoting(self):
        matrix = [[0j, 2j], [3 + 0j, 1j]]
        expected = [2 - 1j, 3 + 2j]
        rhs = [sum(a * b for a, b in zip(row, expected)) for row in matrix]
        for actual in (LU(matrix).solve(rhs), linear_solve([row[:] for row in matrix], rhs[:])):
            for a, b in zip(actual, expected):
                self.assertLess(abs(a - b), 1e-12)
        with self.assertRaises(ValueError):
            LU([[1, 2], [2, 4]])

    def test_sexpr_roundtrip_and_malformed_input(self):
        text = '(footprint "escaped \\"name\\"" (at -1.5 3) (layer "F.Cu"))'
        tree = read_sexpr(text)
        self.assertEqual(read_sexpr(sexpr(tree)), tree)
        with self.assertRaises(ValueError):
            read_sexpr("(footprint (at 1 2)")

    def test_placement_origin_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "part.kicad_mod"
            path.write_text(
                '(footprint "part" (layer "F.Cu") (property "Reference" "REF" (layer "F.Fab")) (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu")))'
            )
            component = dict(
                ref="R1", footprint="Resistor:Test", value="1k", source="", mpn="Test", nets={"1": "signal"}
            )
            placed = placed_footprint(component, (5, 7, 0, "F"), path, {"signal": 1}, origin=(20, 30))
            self.assertEqual(list(first(placed, "at")[1:3]), [25, 37])
            self.assertEqual(first(children(placed, "pad")[0], "net")[2], "/signal")

    def test_board_modules_import_without_path_mutation(self):
        import sys

        before = sys.path[:]
        root = Path(__file__).resolve().parents[2] / "hardware/electronics"
        for board in root.iterdir():
            if not (board / "verify.py").exists():
                continue
            for name in ("generate", "verify"):
                importlib.import_module(f"hardware.electronics.{board.name}.{name}")
        self.assertEqual(sys.path, before)

    def test_exposed_pad_stencil_windows_keep_layers_and_have_no_net(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ep.kicad_mod"
            path.write_text(
                '(footprint "ep" (layer "F.Cu") (property "Reference" "REF" (layer "F.Fab")) '
                '(pad "33" smd rect (at 0 0) (size 5 5) (layers "F.Cu")) '
                '(pad "" smd rect (at 0 0) (size 3 3) (layers "F.Mask")) '
                '(pad "" smd rect (at 0 0) (size 2 2) (layers "F.Paste")))'
            )
            component = dict(
                ref="U1", footprint="Local:EP", value="EP", source="", mpn="EP", nets={"33": "GND"}
            )
            for side in ("F", "B"):
                placed = placed_footprint(component, (5, 7, 0, side), path, {"GND": 1})
                pads = children(placed, "pad")
                self.assertEqual(first(pads[0], "net")[2], "/GND")
                self.assertEqual(
                    [list(first(p, "layers")[1:]) for p in pads],
                    [[side + ".Cu"], [side + ".Mask"], [side + ".Paste"]],
                )
                self.assertEqual(
                    [list(map(float, first(p, "size")[1:])) for p in pads], [[5, 5], [3, 3], [2, 2]]
                )
                self.assertTrue(all(not children(p, "net") for p in pads[1:]))

    def test_unnumbered_copper_is_not_treated_as_a_stencil_window(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.kicad_mod"
            path.write_text(
                '(footprint "bad" (layer "F.Cu") (property "Reference" "REF" (layer "F.Fab")) (pad "" smd rect (at 0 0) (size 2 2) (layers "F.Cu")))'
            )
            component = dict(ref="U1", footprint="Local:Bad", value="Bad", source="", mpn="Bad", nets={})
            with self.assertRaises(KeyError):
                placed_footprint(component, (0, 0, 0, "F"), path, {})

    def test_switch_locating_holes_stay_nonplated_and_unconnected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "switch.kicad_mod"
            path.write_text(
                '(footprint "switch" (layer "F.Cu") (property "Reference" "REF" (layer "F.Fab")) '
                '(pad "" np_thru_hole circle (at 3 2) (size 1 1) (drill 1) (layers "*.Cu" "*.Mask")) '
                '(pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu")))'
            )
            component = dict(
                ref="S1", footprint="Local:Switch", value="Switch", source="", mpn="Switch", nets={"1": "RUN"}
            )
            for side, expected_y in (("F", 2), ("B", -2)):
                placed = placed_footprint(component, (5, 7, 0, side), path, {"RUN": 1})
                hole, terminal = children(placed, "pad")
                self.assertEqual(hole[2], "np_thru_hole")
                self.assertEqual(list(map(float, first(hole, "at")[1:3])), [3, expected_y])
                self.assertEqual(float(first(hole, "drill")[1]), 1)
                self.assertFalse(children(hole, "net"))
                self.assertEqual(first(terminal, "net")[2], "/RUN")

    def test_exported_netlists_match_independent_contracts(self):
        root = Path(__file__).resolve().parents[2] / "hardware/electronics"
        checked = 0
        for board in root.iterdir():
            if not (board / "verify.py").exists():
                continue
            module = importlib.import_module(f"hardware.electronics.{board.name}.verify")
            contract = getattr(module, "CONTRACT", None)
            if contract is None:
                continue
            _, pins = netlist(board / "generated/netlist.xml")
            # Unconnected codec pins are represented as None in its contract.
            for ref, expected in contract.items():
                for pin, net in expected.items():
                    actual = pins.get(ref, {}).get(pin)
                    if net is None:
                        self.assertTrue(
                            actual is None or actual.startswith("unconnected-"), (board.name, ref, pin)
                        )
                    else:
                        self.assertEqual(actual, net, (board.name, ref, pin))
            checked += 1
        self.assertGreaterEqual(checked, 5)

    def test_reports_fingerprint_shared_implementations(self):
        root = Path(common.__file__).parent.parent
        hashes = source_hashes(root, [])
        for module in pkgutil.iter_modules(common.__path__):
            self.assertIn("common/" + module.name + ".py", hashes)

    def test_protection_network_uses_shared_solver(self):
        from hardware.electronics.input_protection import verify

        parts, pins = netlist(verify.ROOT / "generated/netlist.xml")
        result = verify.settled_states(parts, pins)
        enabled = {row["name"] for row in result["rows"] if row["efuse_enabled_in_settled_model"]}
        self.assertEqual(enabled, {"normal_ready", "input_returns_to_max_normal"})

    def test_parallel_digital_fet_cannot_bypass_a_disconnect_leg(self):
        from copy import deepcopy

        from hardware.electronics.rail_disconnect import verify

        parts, pins = netlist(verify.OUT / "netlist.xml")
        verify.contract(parts, pins)
        for pin, wrong_net in [("3", "5V_DIG"), ("2", "AGND"), ("1", "5V_DIG_SRC")]:
            with self.subTest(pin=pin, wrong_net=wrong_net):
                broken = deepcopy(pins)
                broken["Q13"][pin] = wrong_net
                with self.assertRaises(AssertionError):
                    verify.contract(parts, broken)

    def test_old_digital_soft_start_fails_with_protected_bulk(self):
        import json
        from copy import deepcopy

        from hardware.electronics.power_supply import verify

        parts, _ = netlist(verify.OUT / "netlist.xml")
        mapping = json.loads((verify.ROOT / "supply-map.json").read_text())
        current = verify.power_screen(parts, mapping)
        self.assertLess(current["digital_startup"]["maximum_conditional_inductor_peak_a"], 4.2)
        old = deepcopy(parts)
        old["C17"].find("value").text = "33nF 16V X7R"
        with self.assertRaises(AssertionError):
            verify.power_screen(old, mapping)


if __name__ == "__main__":
    unittest.main()
