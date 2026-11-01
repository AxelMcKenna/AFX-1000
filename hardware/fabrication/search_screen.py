"""Generate route hypotheses near the polygon approximation boundary.

This search screen permits 2 um of approximation uncertainty; it is not an
acceptance check. The real board rules stay at0.2mm and strict native DRC must
accept every resulting candidate. Drills, mounting holes and keepouts retain
the original conservative screen.
"""

from shapely.geometry import LineString, Point

from hardware.fabrication.route_nf_layers import LayerScreen


class CandidateScreen(LayerScreen):
    def legal(self,net,layer,points):
        line = LineString(points)
        if line.length < 1e-6 or not self.outline.covers(line):
            return False
        for index in self.trees[layer].query(line.buffer(.5)):
            other,obstacle,distance = self.geometry[layer][int(index)]
            if other == net:
                continue
            if other is not None and abs(distance-.31) < 1e-8:
                distance = .298
            if line.distance(obstacle) <= distance:
                return False
        for other,face,obstacle in self.added:
            if other != net and face == layer and line.distance(obstacle) <= .398:
                return False
        return all(other == net or line.distance(Point(xy)) > .325+.1+.2+.01 for other,xy in self.new_vias)
