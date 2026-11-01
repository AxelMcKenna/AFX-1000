"""Dogbone search with same-net drill outside SMD copper by at least0.1mm.

Annular overlap is allowed; drilled-hole overlap with an SMD land is not.
Stencil/mask acceptance remains open and full native DRC is mandatory.
"""

import math

from shapely.geometry import Point

from hardware.fabrication.route_nf_layers import DIAMETER, DRILL, WIDTH, LayerScreen


class DogboneScreen(LayerScreen):
    def via_legal(self, net, xy):
        point = Point(xy)
        if not self.via_outline.covers(point):
            return False
        for other, position in self.vias+self.new_vias:
            if math.dist(position, xy) < 1e-7:
                return other == net
            if math.dist(position, xy) <= DIAMETER+.2+.01:
                return False
        for index in self.via_tree.query(point.buffer(.6)):
            other, obstacle, kind = self.via_geometry[int(index)]
            if kind == "HOLE":
                clearance = DRILL/2+.25+.01
            elif kind == "KEEPOUT":
                clearance = DIAMETER/2+.01
            elif other == net:
                # Keep the drill at least0.101mm outside the own SMD copper
                # approximation. The annular land may overlap its same-net pad.
                # Other net clearances and off-centre track restrictions remain.
                clearance = DRILL/2+.101 if kind == "PAD" else DIAMETER/2+.01
            else:
                clearance = DIAMETER/2+.2+.01
            if point.distance(obstacle) <= clearance:
                return False
        for _, _, line in self.added:
            if point.distance(line) <= DIAMETER/2+WIDTH/2+.2+.01:
                return False
        return True
