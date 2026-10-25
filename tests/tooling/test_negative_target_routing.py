"""Negative DC-target path, Kelvin-sense and quiet-return regressions."""

import json
import math
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform
from hardware.electronics.power_supply.routing.check import OUT, ROOT, ground_layout, local_paths, via_lands
from hardware.electronics.power_supply.routing.negative_target_check import (
    component_faces,
    native_connections,
    quiet_return,
    set_kelvin,
)


class NegativeTargetRouting(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def footprint(self, tree, ref):
        return next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", ref] for p in children(f, "property"))
        )

    def pad(self, tree, ref, pin):
        f = self.footprint(tree, ref)
        p = next(p for p in children(f, "pad") if str(p[1]) == str(pin))
        return p, transform(f, first(p, "at")[1:3])

    def missing(self, ref, pin, expected):
        b = self.tree()
        _, at = self.pad(b, ref, pin)
        for s in list(children(b, "segment")):
            if first(s, "layer")[1] == "B.Cu" and any(
                math.dist(at, tuple(map(float, first(s, k)[1:3]))) < 1e-6 for k in ("start", "end")
            ):
                b.remove(s)
        with self.assertRaisesRegex(AssertionError, expected):
            local_paths(b)

    def closest_via(self, tree, ref, pin):
        p, at = self.pad(tree, ref, pin)
        net = str(first(p, "net")[1])
        return min(
            (v for v in children(tree, "via") if str(first(v, "net")[1]) == net),
            key=lambda v: math.dist(at, tuple(map(float, first(v, "at")[1:3]))),
        )

    def test_n19_isolation_input_is_required(self):
        self.missing("R37", 1, "n19_isolation_drive")

    def test_n12_isolation_input_is_required(self):
        self.missing("R42", 1, "n12_isolation_drive")

    def test_n19_set_drive_is_required(self):
        self.missing("R37", 2, "n19_set_drive")

    def test_n12_set_drive_is_required(self):
        self.missing("R42", 2, "n12_set_drive")

    def test_n19_kelvin_arm_is_required(self):
        self.missing("R34", 1, "n19_set_kelvin")

    def test_n12_kelvin_arm_is_required(self):
        self.missing("R39", 1, "n12_set_kelvin")

    def test_n19_set_filter_is_required(self):
        self.missing("C50", 1, "n19_set_filter")

    def test_n12_set_filter_is_required(self):
        self.missing("C55", 1, "n12_set_filter")

    def test_n19_dc_feedback_cannot_be_disconnected(self):
        b = self.tree()
        b.remove(self.closest_via(b, "U6", 2))
        with self.assertRaisesRegex(AssertionError, "n19_feedback_inv"):
            local_paths(b)

    def test_n12_dc_feedback_cannot_be_disconnected(self):
        b = self.tree()
        b.remove(self.closest_via(b, "R40", 2))
        with self.assertRaisesRegex(AssertionError, "n12_feedback_inv"):
            local_paths(b)

    def test_n19_divider_return_is_required(self):
        self.missing("R36", 2, "n19_divider_return")

    def test_n12_divider_return_is_required(self):
        self.missing("R41", 2, "n12_divider_return")

    def shunt(self, rail, driver, sense):
        b = self.tree()
        p, a = self.pad(b, driver, 2)
        _, c = self.pad(b, sense, 1)
        b.append(
            read_sexpr(
                f'(segment (start {a[0]} {a[1]}) (end {c[0]} {c[1]}) (width .26) (layer "B.Cu") (net {first(p, "net")[1]}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "Kelvin sense shunted"):
            set_kelvin(b)

    def test_n19_drive_and_sense_cannot_join_before_set(self):
        self.shunt("N19", "R37", "R34")

    def test_n12_drive_and_sense_cannot_join_before_set(self):
        self.shunt("N12", "R42", "R39")

    def test_divider_return_cannot_touch_power_ground(self):
        b = self.tree()
        p, a = self.pad(b, "R36", 2)
        _, c = self.pad(b, "C61", 2)
        b.append(
            read_sexpr(
                f'(segment (start {a[0]} {a[1]}) (end {c[0]} {c[1]}) (width .26) (layer "B.Cu") (net {first(p, "net")[1]}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "return shunted to power ground"):
            quiet_return(b)

    def test_quiet_layer_change_needs_its_plane_antipad(self):
        b = self.tree()
        for z in children(b, "zone"):
            if not children(z, "keepout") or not children(z, "layer"):
                continue
            pts = children(first(first(z, "polygon"), "pts"), "xy")
            center = tuple(sum(float(p[k]) for p in pts) / len(pts) for k in (1, 2))
            if math.dist(center, (133.875, 118.625)) < 1e-5:
                b.remove(z)
                break
        else:
            self.fail("missing quiet layer-change guard")
        with self.assertRaises(AssertionError):
            ground_layout(b)

    def test_set_neck_cannot_be_narrower_than_015mm(self):
        b = self.tree()
        p, at = self.pad(b, "U10", 4)
        s = next(
            s
            for s in children(b, "segment")
            if str(first(s, "net")[1]) == str(first(p, "net")[1])
            and list(map(float, first(s, "start")[1:3])) == list(at)
            and float(first(s, "end")[2]) < at[1]
        )
        first(s, "width")[1] = 0.1
        with self.assertRaisesRegex(AssertionError, "n19_set_drive"):
            local_paths(b)

    def test_route_masks_must_not_become_schematic_nets(self):
        b = self.tree()
        b.append(["net", "9999", "/N19_SET_DRIVE_ROUTE"])
        with self.assertRaisesRegex(AssertionError, "must not add schematic nets"):
            component_faces(b)

    def test_native_control_net_opens_are_rejected(self):
        d = json.loads((OUT / "drc.json").read_text())
        d["unconnected_items"].append({"items": [{"description": "Pad 4 [/N12_SET] of U11"}]})
        with self.assertRaisesRegex(AssertionError, "control net has native open"):
            native_connections(d)

    def test_set_escape_via_cannot_be_drilled_in_a_land(self):
        b = self.tree()
        _, at = self.pad(b, "R37", 2)
        v = self.closest_via(b, "R37", 2)
        first(v, "at")[1:3] = at
        with self.assertRaisesRegex(AssertionError, "conventional via drill too close"):
            via_lands(b)

    def test_front_negative_regulator_cannot_flip_faces(self):
        b = self.tree()
        first(self.footprint(b, "U11"), "layer")[1] = "B.Cu"
        with self.assertRaisesRegex(AssertionError, "negative target component face changed"):
            component_faces(b)
