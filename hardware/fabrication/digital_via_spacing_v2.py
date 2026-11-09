"""Native-sized via spacing for additive digital routing trials.

This planning screen retains 0.20 mm foreign-net copper clearance, 0.25 mm
hole-to-hole clearance, 0.16 mm drill-edge/SMD clearance and a 0.01 mm routing
margin. It distinguishes a via's actual copper diameter from its drill.
Every emitted candidate still requires independent native verification.
"""
import math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr, children, first
from hardware.fabrication.audit_candidate import sha
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point
from shapely.ops import unary_union
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen
from hardware.fabrication.route_nf_surface import shape


class DigitalViaScreen(ExistingViaScreen):
    def __init__(self, capture, signal_layers=('F.Cu', 'In3.Cu', 'B.Cu')):
        super().__init__(capture, signal_layers)
        via_drills = {}
        if any(o['kind'] == 'PCB_VIA' and 'drill_mm' not in o for o in capture['objects']):
            sources = [Path(p) for p in capture.get('source_sha256', {}) if p.endswith('.kicad_pcb')]
            assert len(sources) == 1, 'Via drill sizes require the source-bound native PCB'
            source = sources[0]
            assert sha(source) == capture['source_sha256'][str(source)]
            board = read_sexpr(source.read_text())
            via_drills = {str(first(v, 'uuid')[1]): (float(first(v, 'drill')[1]),
                          tuple(map(float, first(v, 'at')[1:3]))) for v in children(board, 'via')}
        self.drilled = []
        self.via_obstacles = []
        for obj in capture['objects']:
            if obj['kind'] == 'PCB_VIA' and 'drill_mm' not in obj:
                drill, at = via_drills[obj['uuid']]
                assert math.dist(at, obj['position_mm']) < 1e-6
                drills = [drill, drill]
            else:
                drills = obj.get('drill_mm', [0, 0])
            if any(drills):
                # Circumscribed radius for slots; exact for circular drills.
                radius = max(drills) / 2 if abs(drills[0]-drills[1]) < 1e-9 else math.hypot(*drills)/2
                self.drilled.append((obj['net'], tuple(obj['position_mm']), radius, obj['kind']))
            copper = shape([p for ps in obj['layers'].values() for p in ps])
            if not copper.is_empty:
                self.via_obstacles.append((obj['net'], copper, obj['kind']))
        for zone in capture['zones']:
            if zone['keepout'] and zone['prohibit_vias']:
                self.via_obstacles.append((None, shape(zone['polygons']), 'KEEPOUT'))
        self._obstacle_cache = {}

    def obstacles(self, net):
        if net not in self._obstacle_cache:
            rows = []
            for other, copper, kind in self.via_obstacles:
                if other == net and kind in ('PCB_TRACK', 'PCB_VIA'):
                    continue
                # Same-net pads remain protected from drilling into their lands.
                clearance = .31 if other == net or kind == 'KEEPOUT' else .51
                rows.append(copper.buffer(clearance + .003, quad_segs=32))
            rows += [Point(p).buffer(radius + .15 + .25 + .01 + .003, quad_segs=32)
                     for _, p, radius, _ in self.drilled]
            self._obstacle_cache[net] = unary_union(rows)
        extra = [Point(p).buffer((.56 if other == net else .81) + .003, quad_segs=32)
                 for other, p in self.new_vias]
        extra += [line.buffer(.613, quad_segs=32) for other, _, line in self.added if other != net]
        return unary_union([self._obstacle_cache[net], *extra]) if extra else self._obstacle_cache[net]

    def via_legal(self, net, xy):
        centred = [other for other, p in self.vias+self.new_vias if math.dist(xy, p) < 1e-7]
        if centred:
            return all(other == net for other in centred)
        point = Point(xy)
        return self.via_outline.covers(point) and not self.obstacles(net).intersects(point)


def via_mask(screen, net, xs, ys):
    xx, yy = np.meshgrid(xs, ys)
    return contains_xy(screen.via_outline, xx, yy) & ~contains_xy(screen.obstacles(net), xx, yy)
