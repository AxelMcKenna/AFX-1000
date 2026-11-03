"""Apply enlarged noise clearances with a matching spatial-search radius."""

from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen


class QuietTraceScreen(LayeredSignalScreen):
    def __init__(self, captured, protected_nets):
        from shapely.strtree import STRtree

        super().__init__(captured)
        self.protected_nets = frozenset(protected_nets)
        self.search_radius = {}
        for face in self.layers:
            self.geometry[face] = [(net, g, max(d, .71) if net in self.protected_nets else d)
                                   for net, g, d in self.geometry[face]]
            self.trees[face] = STRtree([g for _, g, _ in self.geometry[face]])
            self.search_radius[face] = max((d for _, _, d in self.geometry[face]), default=.71)

    def legal(self, net, layer, points):
        from shapely.geometry import LineString

        if not super().legal(net, layer, points):
            return False
        line = LineString(points)
        # The base screen's .5 mm broad-phase search is sufficient for its
        # ordinary .31/.36 mm margins, but cannot enforce an enlarged .71 mm
        # margin. Search at least as far as the largest actual clearance.
        for i in self.trees[layer].query(line.buffer(self.search_radius[layer]+1e-8)):
            other, geometry, distance = self.geometry[layer][int(i)]
            if other != net and line.distance(geometry) <= distance:
                return False
        # Added geometry is stored as centre-lines, so include both half-widths.
        return all(other == net or face != layer or other not in self.protected_nets or line.distance(g) > .81
                   for other, face, g in self.added)
