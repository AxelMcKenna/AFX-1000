"""Mutations must fail the completed power-routing candidate's independent checks."""

import copy
import json
import math
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform
from hardware.electronics.power_supply.routing.check import OUT, ROOT, local_paths
from hardware.electronics.power_supply.routing.negative_power_check import (
    dc_route_estimates,
    input_planes,
    native_connections,
)


class NegativePowerRouting(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def cut(self, ref, pin, expected):
        b = self.tree()
        fp = next(
            f
            for f in children(b, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )
        pad = next(p for p in children(fp, "pad") if str(p[1]) == str(pin))
        at = transform(fp, first(pad, "at")[1:3])
        for s in list(children(b, "segment")):
            if any(math.dist(at, tuple(map(float, first(s, k)[1:3]))) < 1e-6 for k in ("start", "end")):
                b.remove(s)
        with self.assertRaisesRegex(AssertionError, expected):
            local_paths(b)

    def test_n19_shutdown_is_required(self):
        self.cut("U10", 5, "n19_shutdown")

    def test_n12_shutdown_is_required(self):
        self.cut("U11", 5, "n12_shutdown")

    def test_n19_input_limit_strap_is_required(self):
        self.cut("U10", 8, "n19_current_limit")

    def test_n12_input_limit_strap_is_required(self):
        self.cut("U11", 8, "n12_current_limit")

    def test_n19_output_header_is_required(self):
        self.cut("J2", 3, "n19_load_header")

    def test_n12_output_header_is_required(self):
        self.cut("J2", 5, "n12_load_header")

    def test_raw_test_feed_is_required(self):
        self.cut("J4", 1, "raw_p22_test")

    def test_virtual_via_endpoint_requires_the_actual_via(self):
        from unittest.mock import patch

        from hardware.electronics.power_supply.routing import check

        fake = (
            "missing_via_probe",
            "RAW_P22",
            ("@via", (89, 43, "In2.Cu")),
            ("J4", 1),
            200,
            ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"),
        )
        with patch.object(check, "NEGATIVE_POWER_PATHS", check.NEGATIVE_POWER_PATHS + [fake]):
            with self.assertRaisesRegex(AssertionError, "via endpoint"):
                local_paths(self.tree())

    def test_n12_load_copper_cannot_be_thinned(self):
        b = self.tree()
        code = next(str(n[1]) for n in children(b, "net") if str(n[2]) == "/N12_SRC")
        for s in children(b, "segment"):
            if str(first(s, "net")[1]) == code and float(first(s, "width")[1]) >= 0.5:
                first(s, "width")[1] = 0.4
        with self.assertRaisesRegex(AssertionError, "n12_load_header"):
            local_paths(b)

    def test_any_native_open_blocks_completed_routing(self):
        with self.assertRaisesRegex(AssertionError, "connectivity is incomplete"):
            native_connections(dict(unconnected_items=[{}]))

    def test_drop_estimate_retains_its_budget(self):
        p = copy.deepcopy(json.loads((OUT / "verification.json").read_text())["local_paths"])
        p["n12_load_header"]["length_mm"] = 500
        with self.assertRaisesRegex(AssertionError, "DC-drop budget"):
            dc_route_estimates(p)

    def test_input_plane_cannot_lose_the_bank(self):
        b = read_sexpr((OUT / "filled.kicad_pcb").read_text())
        z = next(
            z
            for z in children(b, "zone")
            if not children(z, "keepout")
            and first(z, "layer")[1] == "B.Cu"
            and first(z, "net")[-1] == "/RAW_N17"
        )
        for p in list(children(z, "filled_polygon")):
            z.remove(p)
        with self.assertRaisesRegex(AssertionError, "split across filled regions"):
            input_planes(b)
