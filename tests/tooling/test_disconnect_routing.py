"""Mutations must invalidate the E25 local source-bank copper contracts."""

import copy
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.rail_disconnect.routing.check import local_contract, segment_distance

try:
    from hardware.electronics.rail_disconnect.routing.router import LAYERS, Router
except ModuleNotFoundError as error:
    if error.name != "numpy":
        raise
    LAYERS = Router = None

ROOT = Path(__file__).resolve().parents[2]


class DisconnectRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = read_sexpr(
            (ROOT / "hardware/electronics/rail_disconnect/routing/rail_disconnect.kicad_pcb").read_text()
        )
        cls.placed = read_sexpr(
            (ROOT / "hardware/electronics/rail_disconnect/placement/rail_disconnect.kicad_pcb").read_text()
        )

    def test_actual_source_lands_and_parallel_banks_are_connected(self):
        self.assertEqual(len(local_contract(self.board)), 38)

    def test_routing_preserves_complete_non_copper_placement(self):
        stripped = [
            n
            for n in self.board
            if not isinstance(n, list) or not n or n[0] not in ("segment", "via", "zone")
        ]
        self.assertEqual(stripped, self.placed)

    def test_missing_source_land_is_rejected(self):
        board = copy.deepcopy(self.board)
        f = next(
            f
            for f in children(board, "footprint")
            if any(p[1:3] == ["Reference", "Q13"] for p in children(f, "property"))
        )
        p = next(p for p in children(f, "pad") if str(p[1]) == "1")
        f.remove(p)
        with self.assertRaises(AssertionError):
            local_contract(board)

    def test_undersized_source_bars_are_rejected(self):
        board = copy.deepcopy(self.board)
        for s in children(board, "segment"):
            if float(first(s, "width")[1]) == 0.7:
                first(s, "width")[1] = 0.69
        with self.assertRaises(AssertionError):
            local_contract(board)

    def test_missing_digital_current_bridge_is_rejected(self):
        board = copy.deepcopy(self.board)
        board[:] = [
            n
            for n in board
            if not (isinstance(n, list) and n and n[0] == "segment" and float(first(n, "width")[1]) == 2)
        ]
        with self.assertRaises(AssertionError):
            local_contract(board)

    def test_swapping_gate_and_source_net_is_rejected(self):
        board = copy.deepcopy(self.board)
        f = next(
            f
            for f in children(board, "footprint")
            if any(p[1:3] == ["Reference", "Q11"] for p in children(f, "property"))
        )
        p = next(p for p in children(f, "pad") if str(p[1]) == "1")
        first(p, "net")[-1] = "/5V_DIG_GATE"
        with self.assertRaises(AssertionError):
            local_contract(board)

    @unittest.skipUnless(Router is not None, "Requires hardware/cad/a11/requirements.txt")
    def test_plated_pads_block_all_six_copper_layers(self):
        r = Router(copy.deepcopy(self.placed))
        for p in r.by_ref["J1"]:
            self.assertEqual(p["layers"], tuple(range(len(LAYERS))))

    @unittest.skipUnless(Router is not None, "Requires hardware/cad/a11/requirements.txt")
    def test_via_mask_excludes_own_smd_pads(self):
        r = Router(copy.deepcopy(self.placed))
        p = r.by_ref["R1"][0]
        _, mask = r.masks(p["net"], 0.25)
        self.assertTrue(mask[round(p["xy"][0] / 0.25), round(p["xy"][1] / 0.25)])

    @unittest.skipUnless(Router is not None, "Requires hardware/cad/a11/requirements.txt")
    def test_via_mask_prevents_same_net_drill_collisions(self):
        r = Router(copy.deepcopy(self.placed))
        r.via("P19_GATE", (70, 40))
        _, mask = r.masks("P19_GATE", 0.25)
        self.assertTrue(mask[round(70.5 / 0.25), round(40 / 0.25)])

    @unittest.skipUnless(Router is not None, "Requires hardware/cad/a11/requirements.txt")
    def test_existing_plated_land_never_gets_a_second_drill(self):
        r = Router(copy.deepcopy(self.placed))
        pad = next(p for p in r.by_ref["J6"] if p["pin"] == "2")
        r.via(pad["net"], pad["xy"])
        self.assertEqual(children(r.board, "via"), [])

    def test_actual_interior_junctions_are_distinguished_from_gaps(self):
        self.assertEqual(segment_distance((0, 0), (0, 2), (-1, 1), (1, 1)), 0)
        self.assertAlmostEqual(segment_distance((0, 0), (0, 2), (0.1, 0), (0.1, 2)), 0.1)


if __name__ == "__main__":
    unittest.main()
