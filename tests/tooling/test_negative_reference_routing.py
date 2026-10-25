"""Negative-reference missing connections and same-net power-shunt regressions."""

import json
import math
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.power_supply.routing.check import OUT, ROOT, ground_layout, local_paths, via_lands
from hardware.electronics.power_supply.routing.negative_reference_check import (
    component_faces,
    native_connections,
    reference_return,
)


class NegativeReferenceRouting(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def disconnect(self, tree, point, layer):
        for s in list(children(tree, "segment")):
            if first(s, "layer")[1] == layer and any(
                math.dist(tuple(map(float, first(s, tag)[1:3])), point) < 1e-6 for tag in ("start", "end")
            ):
                tree.remove(s)

    def add_shunt(self, tree, start, end, layer):
        net = next(n[1] for n in children(tree, "net") if n[2] == "/AGND")
        tree.append(
            read_sexpr(
                f'(segment (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (width .26) (layer "{layer}") (net {net}))'
            )
        )

    def test_bias_supply_is_required(self):
        b = self.tree()
        self.disconnect(b, (110.9125, 114), "B.Cu")
        with self.assertRaisesRegex(AssertionError, "nref_raw_bias"):
            local_paths(b)

    def test_negative_shunt_ground_and_test_tie_is_required(self):
        b = self.tree()
        self.disconnect(b, (114.475, 116.095), "B.Cu")
        with self.assertRaisesRegex(AssertionError, "nref_test_tie"):
            local_paths(b)

    def test_film_filter_cannot_be_left_floating(self):
        b = self.tree()
        self.disconnect(b, (107, 117.0875), "B.Cu")
        with self.assertRaisesRegex(AssertionError, "nref_film_filter"):
            local_paths(b)

    def test_both_negative_target_inputs_are_required(self):
        for point, expected in [
            ((140.525, 113.365), "nref_n19_target"),
            ((145.475, 112.095), "nref_n12_target"),
        ]:
            with self.subTest(expected):
                b = self.tree()
                self.disconnect(b, point, "B.Cu")
                with self.assertRaisesRegex(AssertionError, expected):
                    local_paths(b)

    def test_shunt_return_cannot_be_disconnected(self):
        b = self.tree()
        self.disconnect(b, (114.475, 117.365), "B.Cu")
        with self.assertRaisesRegex(AssertionError, "nref_shunt_return"):
            local_paths(b)

    def test_same_net_surface_shunt_to_a_power_capacitor_is_rejected(self):
        b = self.tree()
        self.add_shunt(b, (116.3, 118.5), (121.95, 118), "B.Cu")
        with self.assertRaisesRegex(AssertionError, "return shunted to power ground"):
            reference_return(b)

    def test_raw_quiet_return_cannot_touch_the_positive_reference_domain(self):
        b = self.tree()
        for s in children(b, "segment"):
            if first(s, "layer")[1] == "In3.Cu":
                for tag in ("start", "end"):
                    p = first(s, tag)
                    if float(p[2]) == 107.5 and float(p[1]) in (112.5, 114.7):
                        p[2] = 107
        with self.assertRaisesRegex(AssertionError, "return shunted to power ground"):
            reference_return(b)

    def test_undeclared_plane_contact_via_on_the_quiet_return_is_rejected(self):
        b = self.tree()
        net = next(n[1] for n in children(b, "net") if n[2] == "/AGND")
        b.append(read_sexpr(f'(via (at 105.5 115) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {net}))'))
        with self.assertRaisesRegex(AssertionError, "return shunted to power ground"):
            reference_return(b)

    def test_film_ground_antipad_is_required(self):
        b = self.tree()
        for z in children(b, "zone"):
            if not children(z, "keepout") or not children(z, "layer"):
                continue
            pts = children(first(first(z, "polygon"), "pts"), "xy")
            center = tuple(sum(float(p[i]) for p in pts) / len(pts) for i in (1, 2))
            if math.dist(center, (106.8, 108.2)) < 1e-5:
                for p in pts:
                    p[1:3] = [center[i] + (float(p[i + 1]) - center[i]) * 0.5 for i in (0, 1)]
                break
        else:
            self.fail("missing film ground antipad")
        with self.assertRaisesRegex(AssertionError, "quiet return plane isolation reduced"):
            ground_layout(b)

    def test_reference_face_is_checked(self):
        b = self.tree()
        fp = next(
            f
            for f in children(b, "footprint")
            if any(p[1:3] == ["Reference", "U12"] for p in children(f, "property"))
        )
        first(fp, "layer")[1] = "F.Cu"
        with self.assertRaisesRegex(AssertionError, "negative reference face changed"):
            component_faces(b)

    def test_reference_via_cannot_be_drilled_in_an_amplifier_land(self):
        b = self.tree()
        v = next(v for v in children(b, "via") if list(map(float, first(v, "at")[1:3])) == [136.875, 115.5])
        first(v, "at")[1:3] = [140.525, 113.365]
        with self.assertRaisesRegex(AssertionError, "conventional via drill too close"):
            via_lands(b)

    def test_native_reference_opens_are_rejected(self):
        drc = json.loads((OUT / "drc.json").read_text())
        drc["unconnected_items"].append({"items": [{"description": "Pad 3 [/NREF_FILTER] of U6"}]})
        with self.assertRaisesRegex(AssertionError, "Negative reference has native open"):
            native_connections(drc)
