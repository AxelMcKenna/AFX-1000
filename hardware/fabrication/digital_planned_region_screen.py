"""Freeze proposed copper into the polygon connectivity screen.

The original screen remains the independent segment validator. Proposed vias
occupy every signal layer at their full copper radius, and the frozen via field
retains the original copper/drill and mutual-new-via spacing rules.
"""
from shapely.geometry import Point
import hardware.fabrication.route_nf_surface as surface


class PlannedRegionScreen:
    def __init__(self, screen, net):
        self.outline = screen.outline
        self.via_outline = screen.via_outline
        self.geometry = {face: list(rows) for face, rows in screen.geometry.items()}
        self._net = net
        self._obstacles = screen.obstacles(net)
        self._screen = screen
        self.added = []
        self.new_vias = []
        distance = surface.WIDTH/2 + surface.CLEARANCE + surface.MARGIN
        for other, face, line in screen.added:
            self.geometry[face].append((other, line.buffer(surface.WIDTH/2, quad_segs=32), distance))
        for other, point in screen.new_vias:
            for rows in self.geometry.values():
                rows.append((other, Point(point).buffer(.3, quad_segs=32), distance))

    def obstacles(self, net):
        assert net == self._net
        return self._obstacles

    def via_legal(self, net, xy):
        assert net == self._net
        point = Point(xy)
        return self.via_outline.covers(point) and not self._obstacles.intersects(point)

    def legal(self, net, face, points):
        assert net == self._net
        return self._screen.legal(net, face, points)
