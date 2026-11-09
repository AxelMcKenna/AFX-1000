"""Construct screened routes, reusing existing crossings without zero-length legs."""
import itertools
import math
import time

from shapely.geometry import Point
from shapely.ops import unary_union
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_polygon_path import route as polygon_route
from hardware.fabrication.digital_region_reachability import reachability, polygon_parts


def route(screen, net, face, start, contacts, deadline, existing_crossings=()):
    frozen = PlannedRegionScreen(screen, net)
    faces = tuple(frozen.geometry)
    report = reachability(frozen, net, [(face, start)], sorted(contacts), faces,
                          existing_crossings=existing_crossings)
    if not report['connected']:
        return None
    point, legs, vias = start, [], []
    for edge in report['component_witness']:
        assert edge['from_component'][0] == face
        target = edge['point_mm']
        legs.append((face, point, target))
        if edge['kind'] == 'new_via':
            vias.append(target)
        point, face = target, edge['to_component'][0]
    if any(math.dist(p, q) <= .563 for p, q in itertools.combinations(vias, 2)):
        return None
    free = {}
    for f in faces:
        obstacles = [g.buffer(d+.0005, quad_segs=32) for n,g,d in frozen.geometry[f] if n != net]
        free[f] = frozen.outline.difference(unary_union(obstacles))
    component = next(p for p in polygon_parts(free[face]) if p.covers(Point(point)))
    ends = [p for f,p in contacts if f == face and component.covers(Point(p))]
    assert ends
    end = min(ends, key=lambda p: math.dist(point,p))
    legs.append((face,point,end))
    runs = []
    for f,p,q in legs:
        # An existing via can be exactly at the start or target. It supplies
        # the layer transition without a new segment at that point.
        if math.dist(p,q) < 1e-9:
            continue
        if time.monotonic() > deadline:
            return None
        path = polygon_route(frozen,net,f,p,q,free[f],deadline)
        if path is None:
            return None
        if len(path) > 1 and any(math.dist(a,b) > 1e-7 for a,b in zip(path,path[1:])):
            runs.append((f,path))
    assert all(screen.via_legal(net,p) for p in vias)
    return dict(runs=runs,vias=vias)
