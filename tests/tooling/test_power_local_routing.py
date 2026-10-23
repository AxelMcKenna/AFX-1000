"""Reject disconnected input return and a wrong-net output-sense via."""

import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.power_supply.routing.check import (
    ROOT,
    front_buck,
    front_raw,
    ground_layout,
    local_paths,
    via_lands,
)


class PowerLocalRoutingTests(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def test_missing_front_input_return_is_rejected(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "start")[1:3])) == [157.26, 114.25]
        )
        tree.remove(segment)
        with self.assertRaisesRegex(AssertionError, "input_bypass_ground"):
            local_paths(tree)

    def test_wrong_net_kelvin_via_is_rejected(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/AGND")
        via = next(v for v in children(tree, "via") if list(map(float, first(v, "at")[1:3])) == [162, 104.25])
        first(via, "net")[1] = net
        with self.assertRaisesRegex(AssertionError, "output_kelvin"):
            local_paths(tree)

    def test_output_bulk_capacitor_cannot_move_to_back(self):
        tree = self.tree()
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "C19"] for p in children(f, "property"))
        )
        first(fp, "layer")[1] = "B.Cu"
        with self.assertRaisesRegex(AssertionError, "moved off front"):
            front_buck(tree)

    def test_same_net_via_cannot_be_drilled_in_capacitor_land(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/AGND")
        via = next(v for v in children(tree, "via") if first(v, "net")[1] == net)
        first(via, "at")[1:3] = [166.425, 106.45]
        with self.assertRaisesRegex(AssertionError, "conventional via drill too close"):
            via_lands(tree)

    def test_thin_output_branch_cannot_satisfy_power_path(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "start")[1:3])) == [173.325, 113.5]
            and list(map(float, first(s, "end")[1:3])) == [178.025, 113.5]
        )
        first(segment, "width")[1] = 0.15
        with self.assertRaisesRegex(AssertionError, "output_cap_2"):
            local_paths(tree)

    def test_reduced_mount_copper_clearance_is_rejected(self):
        tree = self.tree()
        zone = next(z for z in children(tree, "zone") if children(z, "keepout"))
        for p in children(first(first(zone, "polygon"), "pts"), "xy"):
            p[1:3] = [104 + (float(p[1]) - 104) * 0.5, 104 + (float(p[2]) - 104) * 0.5]
        with self.assertRaisesRegex(AssertionError, "mount copper clearance reduced"):
            ground_layout(tree)

    def test_plane_track_cannot_shunt_quiet_reference_return(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/AGND")
        tree.append(
            read_sexpr(
                f'(segment (start 165 104.75) (end 165 108.6) (width .26) (layer "In1.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "quiet via shunted by In1 track"):
            ground_layout(tree)

    def test_rotated_analog_buck_keeps_floating_rt_name(self):
        tree = self.tree()
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "U3"] for p in children(f, "property"))
        )
        pad = next(p for p in children(fp, "pad") if p[1] == "1")
        first(pad, "net")[-1] = "/" + str(first(pad, "net")[-1])
        with self.assertRaisesRegex(AssertionError, "floating RT pin lost"):
            front_buck(tree)

    def test_sense_connection_cannot_replace_linear_regulator_feed(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "start")[1:3])) == [157.5, 135.5]
            and list(map(float, first(s, "end")[1:3])) == [168.6, 135.5]
            and first(s, "layer")[1] == "In3.Cu"
        )
        tree.remove(segment)
        with self.assertRaisesRegex(AssertionError, "pre_linear_feed"):
            local_paths(tree)

    def test_analog_quiet_return_cannot_join_power_plane_track(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/AGND")
        tree.append(
            read_sexpr(
                f'(segment (start 174.3 121.6125) (end 175 123.74) (width .26) (layer "In1.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "quiet via shunted by In1 track"):
            ground_layout(tree)

    def test_missing_cuk_switch_connection_is_rejected(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "start")[1:3])) == [145.45, 109.2]
            and list(map(float, first(s, "end")[1:3])) == [145.45, 111.7]
        )
        tree.remove(segment)
        with self.assertRaisesRegex(AssertionError, "raw_cuk_switch"):
            local_paths(tree)

    def test_thin_negative_output_cannot_satisfy_bulk_power_path(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "end")[1:3])) == [154.6, 117.9] and first(s, "layer")[1] == "F.Cu"
        )
        first(segment, "width")[1] = 0.15
        with self.assertRaisesRegex(AssertionError, "raw_negative_bulk_1"):
            local_paths(tree)

    def test_removed_negative_bulk_feed_is_rejected(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "start")[1:3])) == [147.1, 118]
            and list(map(float, first(s, "end")[1:3])) == [147.1, 116.5]
            and first(s, "layer")[1] == "B.Cu"
        )
        tree.remove(segment)
        with self.assertRaisesRegex(AssertionError, "raw_negative_bulk_2"):
            local_paths(tree)

    def test_raw_enable_network_needs_its_power_feed(self):
        tree = self.tree()
        segment = next(
            s
            for s in children(tree, "segment")
            if list(map(float, first(s, "start")[1:3])) == [169.375, 104.5]
            and list(map(float, first(s, "end")[1:3])) == [169.375, 101.5]
            and first(s, "layer")[1] == "In4.Cu"
        )
        tree.remove(segment)
        with self.assertRaisesRegex(AssertionError, "raw_positive_enable_feed"):
            local_paths(tree)

    def test_raw_quiet_return_cannot_be_shunted_on_another_inner_layer(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/AGND")
        tree.append(
            read_sexpr(
                f'(segment (start 144.6 109.9) (end 145 112.8) (width .26) (layer "In4.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "quiet via shunted on reserved layer"):
            ground_layout(tree)

    def test_negative_bulk_ground_via_must_clear_its_own_land(self):
        tree = self.tree()
        via = next(
            v for v in children(tree, "via") if list(map(float, first(v, "at")[1:3])) == [147.2, 111.525]
        )
        first(via, "at")[1:3] = [148, 111.525]
        with self.assertRaisesRegex(AssertionError, "conventional via drill too close"):
            via_lands(tree)

    def test_cuk_transfer_capacitor_must_stay_on_component_face(self):
        tree = self.tree()
        fp = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "C63"] for p in children(f, "property"))
        )
        first(fp, "layer")[1] = "B.Cu"
        with self.assertRaisesRegex(AssertionError, "raw supply component moved off front"):
            front_raw(tree)


if __name__ == "__main__":
    unittest.main()
