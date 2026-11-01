"""Add a bounded, exact-obstacle front path from C401 to U202 VCC."""

import hashlib
import heapq
import itertools
import json
import math
import uuid
from pathlib import Path

import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import transform
from hardware.electronics.power_distribution.p03.spec import MOUNTS

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def run():
    source = WORK/"generated/native-closed-transmitter"
    output = WORK/"generated/front-bypass"
    assert not output.exists()
    pcb = source/"power_p03.kicad_pcb"
    digest = hashlib.sha256(pcb.read_bytes()).hexdigest()
    tree = read_sexpr(pcb.read_text())
    pads = json.loads((source/"pads.json").read_text())
    assert pads["source_pcb_sha256"] == digest
    polygons = []
    for row in pads["pad_polygons"]:
        if row["net"] != "V2V5_AUX":
            polygons.extend(Polygon(p["outer"]) for p in row["layers"].get("F.Cu", []))
    for node in children(tree, "segment"):
        if first(node, "layer")[1] == "F.Cu" and first(node, "net")[1] != "/V2V5_AUX":
            polygons.append(LineString([tuple(map(float, first(node, k)[1:3])) for k in ("start", "end")]).buffer(float(first(node, "width")[1])/2))
    for node in children(tree, "via"):
        if first(node, "net")[1] != "/V2V5_AUX":
            polygons.append(Point(tuple(map(float, first(node, "at")[1:3]))).buffer(float(first(node, "size")[1])/2))
    for footprint in children(tree,"footprint"):
        for pad in children(footprint,"pad"):
            if pad[2] == "np_thru_hole":
                drill = first(pad,"drill")
                assert len(drill) == 2, "Slot geometry needs an explicit obstacle"
                polygons.append(Point(transform(footprint,first(pad,"at")[1:3])).buffer(float(drill[1])/2+.08))
    polygons.extend(Point((100+x,100+y)).buffer(3.7) for x,y in MOUNTS)
    for zone in children(tree, "zone"):
        if not children(zone, "keepout"):
            continue
        layers = first(zone, "layers")[1:] if children(zone, "layers") else first(zone, "layer")[1:]
        if ("F.Cu" in layers or "*.Cu" in layers) and first(first(zone, "keepout"), "tracks")[1] == "not_allowed":
            polygons.append(Polygon([tuple(map(float, n[1:3])) for n in first(first(zone, "polygon"), "pts")[1:]]))
    clearance, width, step = .170001, .2, .025
    obstacle = unary_union(polygons).buffer(clearance+width/2)
    xs, ys = 108+np.arange(441)*step, 130+np.arange(401)*step
    blocked = contains_xy(obstacle, xs[:, None], ys[None, :])
    by = {(p["ref"], p["pin"]): p for p in pads["pad_polygons"]}
    start, goal = [tuple(by[key]["position_mm"]) for key in (("C401", "1"), ("U202", "5"))]

    def index(point):
        result = (round((point[0]-108)/step), round((point[1]-130)/step))
        assert math.dist((xs[result[0]], ys[result[1]]), point) < 1e-8
        return result

    first_point, last_point = index(start), index(goal)
    assert not blocked[first_point] and not blocked[last_point]
    costs, previous = {first_point: 0}, {}
    serial = itertools.count()
    queue, seen = [(0, next(serial), first_point)], set()
    while queue:
        _, _, current = heapq.heappop(queue)
        if current in seen:
            continue
        seen.add(current)
        if current == last_point:
            break
        assert len(seen) < 180000, "Bounded local front-path search exhausted"
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
            x, y = current[0]+dx, current[1]+dy
            if not (0 <= x < len(xs) and 0 <= y < len(ys)) or blocked[x,y]:
                continue
            if dx and dy and (blocked[x,current[1]] or blocked[current[0],y]):
                continue
            other = (x,y)
            distance = costs[current]+math.hypot(dx,dy)
            if distance < costs.get(other, math.inf):
                costs[other], previous[other] = distance, current
                heapq.heappush(queue, (distance+math.dist(other,last_point), next(serial), other))
    assert last_point in seen, "No clear front-only bypass path; do not write a candidate"
    route = [last_point]
    while route[-1] != first_point:
        route.append(previous[route[-1]])
    route.reverse()
    points = [start]
    direction = None
    for left, right in zip(route, route[1:]):
        delta = (right[0]-left[0], right[1]-left[1])
        if delta != direction:
            points.append((float(xs[left[0]]), float(ys[left[1]])))
        direction = delta
    points.append(goal)
    points = [p for i,p in enumerate(points) if not i or math.dist(p,points[i-1]) > 1e-8]
    assert not LineString(points).intersects(obstacle), "Exact continuous clearance failed"
    for i,(left,right) in enumerate(zip(points,points[1:])):
        key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:P03:AX03:frontbypass:{digest}:{i}"))
        tree.append(read_sexpr(f'(segment (start {left[0]} {left[1]}) (end {right[0]} {right[1]}) (width {width}) (layer "F.Cu") (net "/V2V5_AUX") (uuid "{key}"))'))
    output.mkdir()
    destination = output/pcb.name
    destination.write_text(sexpr(tree)+"\n")
    (output/"front-bypass.json").write_text(json.dumps(dict(source_PCB_sha256=digest,
        output_PCB_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), source="C401.1", target="U202.5",
        layer="F.Cu", width_mm=width, points_mm=points, authored_length_mm=LineString(points).length,
        no_existing_objects_changed=True, no_new_drills=True, native_validation_pending=True,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Added actual front-only C401 to U202 bypass:", LineString(points).length, "mm")


if __name__ == "__main__":
    run()
