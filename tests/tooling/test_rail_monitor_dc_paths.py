"""Analytic resistor and topology witnesses for the partial E13 DC model."""

import copy
import math
import unittest

from hardware.fabrication.rail_monitor_dc_paths import (
    SCENARIOS,
    barrel_ohm,
    geometry,
    resistivity,
    solve,
    track_ohm,
)


def rectangle(left, bottom, right, top):
    return {"outer": [[left, bottom], [right, bottom], [right, top], [left, top]], "holes": []}


def straight_fixture():
    return {
        "objects": [
            dict(uuid="track", net="/V3V3_IO", kind="PCB_TRACK", position_mm=[0, 0], end_mm=[10, 0],
                 width_mm=0.2, layers={"F.Cu": []}),
            dict(uuid="source-via", net="/V3V3_IO", kind="PCB_VIA", position_mm=[0, 0],
                 layers={"F.Cu": [rectangle(-0.3, -0.3, 0.3, 0.3)],
                         "In2.Cu": [rectangle(-0.3, -0.3, 0.3, 0.3)]}),
            dict(uuid="load", net="/V3V3_IO", kind="PAD", ref="U1", pin="1", position_mm=[10, 0],
                 layers={"F.Cu": [rectangle(9.9, -0.1, 10.1, 0.1)]}),
        ],
        "zones": [dict(net="/V3V3_IO", layer="In2.Cu", keepout=False,
                       polygons=[rectangle(-1, -1, 1, 1)])],
    }


class DCPowerPaths(unittest.TestCase):
    def test_trace_units_match_analytic_100mm_200um_35um_strip(self):
        self.assertAlmostEqual(track_ohm(100, 0.2, 35, 1.7241e-8), 0.2463)
        self.assertAlmostEqual(track_ohm(100, 0.2, 17.5, 1.7241e-8), 2 * 0.2463)

    def test_barrel_uses_annular_copper_area_and_full_board_length(self):
        expected = 1.7241e-8 * 0.0016 / (math.pi * (0.00017**2 - 0.00015**2))
        self.assertAlmostEqual(barrel_ohm(1.6, 0.3, 20, 1.7241e-8), expected)
        self.assertGreater(barrel_ohm(1.6, 0.3, 15, 1.7241e-8), expected)

    def test_source_to_load_fixture_contains_trace_and_barrel(self):
        scenario = SCENARIOS[0]
        actual = solve(straight_fixture(), {"source-via": 0.3}, scenario)
        expected = track_ohm(10, 0.2, 35, 1.7241e-8) + barrel_ohm(1.6, 0.3, 20, 1.7241e-8)
        self.assertAlmostEqual(actual["maximum_path_ohm"], expected)

    def test_missing_plane_or_broken_trace_cannot_report_a_connected_load(self):
        fixture = straight_fixture()
        fixture["zones"] = []
        with self.assertRaisesRegex(ValueError, "unreached pads"):
            solve(fixture, {"source-via": 0.3}, SCENARIOS[0])
        fixture = straight_fixture()
        fixture["objects"][0]["end_mm"] = [9, 0]
        with self.assertRaisesRegex(ValueError, "unreached pads"):
            solve(fixture, {"source-via": 0.3}, SCENARIOS[0])

    def test_plane_hole_is_preserved_and_cannot_short_the_load(self):
        fixture = straight_fixture()
        fixture["objects"] = fixture["objects"][1:]
        fixture["zones"][0]["polygons"] = [rectangle(-1, -1, 11, 1)]
        fixture["zones"][0]["polygons"][0]["holes"] = [rectangle(9, -0.5, 10.5, 0.5)["outer"]]
        fixture["objects"][1]["layers"] = {"In2.Cu": [rectangle(9.9, -0.1, 10.1, 0.1)]}
        self.assertFalse(geometry(fixture["zones"][0]["polygons"]).covers(geometry(fixture["objects"][1]["layers"]["In2.Cu"])))
        with self.assertRaisesRegex(ValueError, "unreached pads"):
            solve(fixture, {"source-via": 0.3}, SCENARIOS[0])
        solid = copy.deepcopy(fixture)
        solid["zones"][0]["polygons"][0]["holes"] = []
        self.assertEqual(solve(solid, {"source-via": 0.3}, SCENARIOS[0])["maximum_path_ohm"], 0)

    def test_temperature_conductivity_and_invalid_dimensions(self):
        self.assertGreater(resistivity(85, 0.9), resistivity(20, 1.0))
        for function, args in [(resistivity, (20, 0)), (track_ohm, (10, 0, 35, 1.7241e-8)),
                               (barrel_ohm, (1.6, 0.3, 0, 1.7241e-8))]:
            with self.assertRaises(ValueError):
                function(*args)


if __name__ == "__main__":
    unittest.main()
