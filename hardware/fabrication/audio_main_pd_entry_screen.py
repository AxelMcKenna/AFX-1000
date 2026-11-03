"""Permit only a declared FDA PD-pin entry through its owner's F.Cu mask."""

from shapely.geometry import LineString
from shapely.strtree import STRtree

from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
from hardware.fabrication.audit_audio_main_named_routes import NETS

OWNERS = {"/ADC/PD_L": ("U101", "R115", (45.8, 20.74, 49.95, 27.85)),
          "/ADC/PD_R": ("U102", "R131", (45.8, 32.74, 49.95, 39.85))}


class PDEntryScreen(QuietTraceScreen):
    def __init__(self, captured, net, path):
        super().__init__(captured, NETS)
        chip, resistor, bounds = OWNERS[net]
        pads = {(p["ref"], p["pin"]): p for p in captured["objects"] if p["kind"] == "PAD" and p["pin"]}
        start, end = pads[chip, "7"], pads[resistor, "1"]
        assert start["net"] == end["net"] == net
        assert path[0] == start["position_mm"] and path[-1] == end["position_mm"]
        assert start["layers"].get("F.Cu") and end["layers"].get("F.Cu")
        band, count, rows = LineString(path).buffer(.16), 0, []
        for other, geometry, distance in self.geometry["F.Cu"]:
            if other is None and distance == .11 and all(abs(a-b) < 1e-6 for a, b in zip(geometry.bounds, bounds)):
                geometry = geometry.difference(band)
                count += 1
            rows.append((other, geometry, distance))
        assert count == 1
        self.geometry["F.Cu"] = rows
        self.trees["F.Cu"] = STRtree([g for _, g, _ in rows])
        # Via masks, plane reference requirements and every other analog mask
        # remain unchanged. This class admits only this complete surface path.
        self.entry_net, self.entry_path = net, path

    def legal(self, net, layer, points):
        return (net == self.entry_net and layer == "F.Cu" and points == self.entry_path
                and super().legal(net, layer, points))
