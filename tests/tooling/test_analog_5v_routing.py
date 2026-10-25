"""Reject lost analog bypass/compensation, Kelvin shunts and plane disconnection."""

import json
import unittest

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.power_supply.routing.analog_5v_check import (
    component_faces,
    kelvin_separation,
    output_plane_contacts,
)
from hardware.electronics.power_supply.routing.check import OUT, ROOT, ground_layout, local_paths


class AnalogFiveVoltRouting(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def segment(self, tree, start, layer):
        return next(
            s
            for s in children(tree, "segment")
            if [round(float(v), 6) for v in first(s, "start")[1:3]] == start and first(s, "layer")[1] == layer
        )

    def test_local_compensation_output_cannot_be_disconnected(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [124.8, 136.5], "B.Cu"))
        with self.assertRaisesRegex(AssertionError, "analog_5v_local_comp_out"):
            local_paths(tree)

    def test_local_compensation_inverting_return_cannot_be_disconnected(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [122.9, 133.825], "B.Cu"))
        with self.assertRaisesRegex(AssertionError, "analog_5v_local_comp_inv"):
            local_paths(tree)

    def test_standard_reference_grade_cannot_inherit_enhanced_enable_pin(self):
        tree = self.tree()
        ref = next(
            f
            for f in children(tree, "footprint")
            if any(p[1:3] == ["Reference", "U4"] for p in children(f, "property"))
        )
        next(p for p in children(ref, "property") if p[1] == "Value")[2] = "REF5025IDR"
        with self.assertRaisesRegex(AssertionError, "enhanced E-grade"):
            component_faces(tree)

    def test_vcontrol_is_required_separately_from_ldo_in(self):
        tree = self.tree()
        via = next(v for v in children(tree, "via") if list(map(float, first(v, "at")[1:3])) == [167.6, 131])
        tree.remove(via)
        with self.assertRaisesRegex(AssertionError, "analog_5v_control_power"):
            local_paths(tree)

    def test_missing_set_drive_cannot_pass_using_only_sense(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [120.5, 137.15], "In2.Cu"))
        with self.assertRaisesRegex(AssertionError, "analog_5v_drive_set"):
            local_paths(tree)

    def test_same_net_kelvin_short_is_rejected(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/V5_REG_SET")
        tree.append(
            read_sexpr(
                f'(segment (start 120.5 135.4) (end 125 131) (width .26) (layer "In2.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "Kelvin sense shunted"):
            kelvin_separation(tree)

    def test_same_net_kelvin_short_at_midsegment_junctions_is_rejected(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/V5_REG_SET")
        tree.append(
            read_sexpr(
                f'(segment (start 140 125.2) (end 140 137.15) (width .26) (layer "In2.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "Kelvin sense shunted"):
            kelvin_separation(tree)

    def test_precision_divider_ground_cannot_join_the_power_plane(self):
        tree = self.tree()
        net = next(n[1] for n in children(tree, "net") if str(n[2]) == "/AGND")
        tree.append(
            read_sexpr(
                f'(segment (start 131.4 131) (end 131.4 133) (width .26) (layer "In1.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "quiet via shunted by In1 track"):
            ground_layout(tree)

    def test_film_reference_ground_needs_its_larger_pour_antipad(self):
        tree = self.tree()
        zone = next(
            z
            for z in children(tree, "zone")
            if children(z, "keepout")
            and children(z, "layer")
            and any(
                float(p[1]) > 131.6 and float(p[2]) == 134
                for p in children(first(first(z, "polygon"), "pts"), "xy")
            )
        )
        for point in children(first(first(zone, "polygon"), "pts"), "xy"):
            point[1:3] = [130.5 + (float(point[1]) - 130.5) * 0.7, 134 + (float(point[2]) - 134) * 0.7]
        with self.assertRaisesRegex(AssertionError, "quiet return plane isolation reduced"):
            ground_layout(tree)

    def filled(self):
        return read_sexpr((OUT / "filled.kicad_pcb").read_text()), json.loads((OUT / "drc.json").read_text())

    def test_wrong_net_output_spreader_is_rejected(self):
        tree, drc = self.filled()
        zone = next(
            z
            for z in children(tree, "zone")
            if not children(z, "keepout") and first(z, "layer")[1] == "In4.Cu"
        )
        first(zone, "net")[1] = "/AGND"
        with self.assertRaisesRegex(AssertionError, "Missing analog output plane"):
            output_plane_contacts(tree, drc)

    def test_output_plane_must_cover_header_annulus(self):
        tree, drc = self.filled()
        zone = next(
            z
            for z in children(tree, "zone")
            if not children(z, "keepout") and first(z, "layer")[1] == "In4.Cu"
        )
        # All four right-hand source/bleed vias stay covered; only J2 is excluded.
        first(children(zone, "filled_polygon")[0], "pts")[:] = read_sexpr(
            "(pts (xy 150 100) (xy 184 100) (xy 184 138) (xy 150 138))"
        )
        with self.assertRaisesRegex(AssertionError, "plane contact disconnected.*122.3.*103"):
            output_plane_contacts(tree, drc)

    def test_output_plane_cannot_hide_a_missing_minimum_load_via(self):
        tree, drc = self.filled()
        tree.remove(
            next(v for v in children(tree, "via") if list(map(float, first(v, "at")[1:3])) == [180.5, 121.4])
        )
        with self.assertRaisesRegex(AssertionError, "Missing analog output/bleed power via"):
            output_plane_contacts(tree, drc)


if __name__ == "__main__":
    unittest.main()
