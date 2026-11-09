"""Compare 1 um copper planning margins without changing native PCB rules.

The native 0.20 mm copper clearance and 0.20 mm track width remain fixed.
Existing drill, same-net land, keepout, new-hole spacing and edge guards retain
their earlier conservative values. Every candidate still needs native DRC and
independent actual-copper measurements before adoption.
"""
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface


class CloseMarginViaScreen(DigitalViaScreen):
    def __init__(self, capture, signal_layers=('F.Cu','In3.Cu','In5.Cu','B.Cu')):
        assert surface.WIDTH == .2 and surface.CLEARANCE == .2 and surface.MARGIN == .001
        super().__init__(capture, signal_layers)
        # Keep the earlier track/edge guard despite the smaller copper margin.
        self.outline = surface.shape(capture['outline']).buffer(-.61)

    def obstacles(self, net):
        if net not in self._obstacle_cache:
            rows = []
            for other, copper, kind in self.via_obstacles:
                if other == net and kind in ('PCB_TRACK','PCB_VIA'):
                    continue
                clearance = .313 if other == net or kind == 'KEEPOUT' else .501
                rows.append(copper.buffer(clearance, quad_segs=32))
            rows += [Point(p).buffer(radius+.413, quad_segs=32) for _,p,radius,_ in self.drilled]
            self._obstacle_cache[net] = unary_union(rows)
        extra = [Point(p).buffer(.563 if other == net else .801, quad_segs=32) for other,p in self.new_vias]
        extra += [line.buffer(.601, quad_segs=32) for other,_,line in self.added if other != net]
        return unary_union([self._obstacle_cache[net],*extra]) if extra else self._obstacle_cache[net]

    def legal(self, net, layer, points):
        if not surface.Screen.legal(self, net, layer, points):
            return False
        line = LineString(points)
        return all(other == net or line.distance(Point(p)) > .601 for other,p in self.new_vias)
