"""Positive regulator, feedback, conventional-via and quiet-return regressions."""

import json
import math
import tempfile
import unittest
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.power_supply.routing.check import (
    OUT,
    ROOT,
    SUPPLY,
    ground_layout,
    local_paths,
    via_lands,
)
from hardware.electronics.power_supply.routing.mechanical import mechanical
from hardware.electronics.power_supply.routing.positive_linear_check import (
    component_faces,
    output_planes,
    set_kelvin,
)


class PositiveLinearRouting(unittest.TestCase):
    def tree(self):
        return read_sexpr((ROOT / "power_supply.kicad_pcb").read_text())

    def segment(self, tree, start, layer, end=None):
        return next(
            (
                s
                for s in children(tree, "segment")
                if first(s, "layer")[1] == layer
                and [round(float(v), 6) for v in first(s, "start")[1:3]] == start
                and (end is None or [round(float(v), 6) for v in first(s, "end")[1:3]] == end)
            )
        )

    def test_u7_vcontrol_is_required_separately_from_input(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [115.2, 133.8], "F.Cu"))
        with self.assertRaisesRegex(AssertionError, "p19_control_bypass"):
            local_paths(tree)

    def test_u8_vcontrol_is_required_separately_from_input(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [135.35, 133.7], "F.Cu", [135.35, 135.4]))
        with self.assertRaisesRegex(AssertionError, "p12_control_bypass"):
            local_paths(tree)

    def test_u8_tab_cannot_be_isolated_from_the_lead_and_header(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [135.35, 132], "F.Cu", [144.5, 132]))
        with self.assertRaisesRegex(AssertionError, "p12_output_tab"):
            local_paths(tree)

    def test_wide_left_output_feed_cannot_be_replaced_by_a_thinner_trace(self):
        tree = self.tree()
        first(self.segment(tree, [135.35, 132], "F.Cu", [131.8, 132.2]), "width")[1] = 0.8
        with self.assertRaisesRegex(AssertionError, "p12_source_header"):
            local_paths(tree)

    def test_new_output_vias_cannot_be_drilled_in_the_ldo_lead(self):
        tree = self.tree()
        via = next(
            (v for v in children(tree, "via") if list(map(float, first(v, "at")[1:3])) == [131.8, 132.2])
        )
        first(via, "at")[1:3] = [135.35, 132]
        with self.assertRaisesRegex(AssertionError, "conventional via drill too close"):
            via_lands(tree)

    def test_p19_set_drive_and_sense_must_not_join_before_the_regulator(self):
        tree = self.tree()
        net = next((n[1] for n in children(tree, "net") if str(n[2]) == "/P19_SET"))
        tree.append(
            read_sexpr(
                f'(segment (start 109.7 126.5) (end 108.8 122) (width .26) (layer "In2.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "Kelvin sense shunted"):
            set_kelvin(tree)

    def test_p12_midsegment_set_shunt_is_rejected(self):
        tree = self.tree()
        net = next((n[1] for n in children(tree, "net") if str(n[2]) == "/P12_SET"))
        tree.append(
            read_sexpr(
                f'(segment (start 128.7 139.5) (end 133.3 139.5) (width .26) (layer "In4.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "Kelvin sense shunted"):
            set_kelvin(tree)

    def test_local_p12_input_bypass_cannot_be_disconnected(self):
        tree = self.tree()
        tree.remove(self.segment(tree, [133, 138.525], "F.Cu"))
        with self.assertRaisesRegex(AssertionError, "p12_input_bypass"):
            local_paths(tree)

    def test_quiet_inner_return_cannot_touch_a_plated_power_ground_land(self):
        tree = self.tree()
        net = next((n[1] for n in children(tree, "net") if str(n[2]) == "/AGND"))
        tree.append(
            read_sexpr(
                f'(segment (start 169 136.5) (end 176.3 123.74) (width .26) (layer "In3.Cu") (net {net}))'
            )
        )
        with self.assertRaisesRegex(AssertionError, "quiet inner return shunted by power-ground contact"):
            ground_layout(tree)

    def test_set_filter_needs_its_own_ground_antipad(self):
        tree = self.tree()
        for zone in children(tree, "zone"):
            if not children(zone, "keepout") or not children(zone, "layer"):
                continue
            points = children(first(first(zone, "polygon"), "pts"), "xy")
            center = [sum((float(p[i]) for p in points)) / len(points) for i in (1, 2)]
            if math.dist(center, (112.8, 138)) < 0.001:
                break
        else:
            self.fail("missing set-filter ground reserve")
        for point in points:
            point[1:3] = [112.8 + (float(point[1]) - 112.8) * 0.5, 138 + (float(point[2]) - 138) * 0.5]
        with self.assertRaisesRegex(AssertionError, "quiet return plane isolation reduced"):
            ground_layout(tree)

    def test_local_compensation_cannot_move_under_the_regulator(self):
        tree = self.tree()
        fp = next(
            (
                f
                for f in children(tree, "footprint")
                if any((p[1:3] == ["Reference", "C39"] for p in children(f, "property")))
            )
        )
        first(fp, "layer")[1] = "B.Cu"
        with self.assertRaisesRegex(AssertionError, "positive linear stage component face changed"):
            component_faces(tree)

    def test_changed_board_edge_needs_an_updated_mechanical_contract(self):
        tree = self.tree()
        tree[:] = [
            x for x in tree if not isinstance(x, list) or not x or x[0] not in ("segment", "via", "zone")
        ]
        for line in children(tree, "gr_line"):
            if first(line, "layer")[1] == "Edge.Cuts":
                for tag in ("start", "end"):
                    if float(first(line, tag)[1]) == 190:
                        first(line, tag)[1] = 189
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bare.kicad_pcb"
            path.write_text(sexpr(tree))
            _, pins = netlist(SUPPLY / "generated/placement-netlist.xml")
            with self.assertRaises(AssertionError):
                mechanical(path, pins)

    def test_wrong_net_thermal_spreader_is_rejected(self):
        tree = read_sexpr((OUT / "filled.kicad_pcb").read_text())
        drc = json.loads((OUT / "drc.json").read_text())
        zone = next(
            (
                z
                for z in children(tree, "zone")
                if not children(z, "keepout") and str(first(z, "net")[-1]) == "/P19_SRC"
            )
        )
        first(zone, "net")[1] = "/AGND"
        with self.assertRaisesRegex(AssertionError, "Missing positive output spreader"):
            output_planes(tree, drc)

    def test_positive_stage_native_open_item_is_not_hidden_by_path_checks(self):
        tree = read_sexpr((OUT / "filled.kicad_pcb").read_text())
        drc = json.loads((OUT / "drc.json").read_text())
        drc["unconnected_items"].append({"description": "missing /P12_FB connection"})
        with self.assertRaisesRegex(AssertionError, "Positive linear stage has native open connections"):
            output_planes(tree, drc)


if __name__ == "__main__":
    unittest.main()
