"""Plan literal local bypass/plane connections before global signal routing.

Uses native pad polygons plus a2um planning allowance. Native DRC and actual
filled-plane connectivity remain mandatory; this script grants no PDN pass.
"""

import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "routing/power-stitches"
LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]


def poly(rows):
    result = [Polygon(r["outer"], r["holes"]) for r in rows]
    assert all(p.is_valid for p in result), "Reject invalid geometry instead of repairing it"
    return unary_union(result)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    geometry_path = ROOT / "generated/power-via-pad-geometry.json"
    data = json.loads(geometry_path.read_text())
    assert hashlib.sha256((ROOT / "negative_startup_physical.kicad_pcb").read_bytes()).hexdigest() == data["source_PCB_sha256"]
    pads = [r for r in data["pads"] if r["layers"]]
    shapes = [unary_union([poly(rows) for rows in r["layers"].values()]) for r in pads]
    tree = STRtree(shapes)
    keepouts = unary_union([poly(z["polygons"]) for z in data["keepouts"]])
    assert keepouts.is_valid
    by = {(r["ref"], r["pin"]): r for r in pads if r["pin"]}
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    plan = json.loads((ROOT / "placement.json").read_text())
    vias, segments, actions, failures = [], [], [], []

    def drill_clear(p):
        for i in tree.query(p.buffer(2.0)):
            r = pads[int(i)]
            d = r["drill_mm"]
            if max(d) > 0:
                assert abs(d[0] - d[1]) < 1e-9, "Oval drill needs an actual shape model"
                if p.distance(Point(r["position_mm"])) < .15 + d[0] / 2 + .252:
                    return False
        return True

    def via_clear(xy, net):
        p = Point(xy)
        if not (1.2 <= xy[0] <= 147.8 and 1.2 <= xy[1] <= 37.8):
            return False
        if p.distance(keepouts) < .327 or not drill_clear(p):
            return False
        for i in tree.query(p.buffer(.53)):
            r, shape = pads[int(i)], shapes[int(i)]
            distance = p.distance(shape)
            if r["net"] != net and distance < .527:
                return False
            if r["SMD"] and distance < .272:
                return False  # no unqualified via-in-pad/solder-wicking credit
        if any(p.distance(Point(v["at_mm"])) < .852 for v in vias):
            return False
        if any(s["net"] != net and p.distance(s["shape"]) < .627 for s in segments):
            return False
        return True

    def path_clear(points, layer, net):
        if math.dist(points[0], points[-1]) < 1e-9:
            return True
        line = LineString(points)
        if line.distance(keepouts) < .102:
            return False
        for i in tree.query(line.buffer(.303)):
            r = pads[int(i)]
            if r["net"] != net and layer in r["layers"] and line.distance(poly(r["layers"][layer])) < .302:
                return False
        if any(s["net"] != net and s["layer"] == layer and line.distance(s["shape"]) < .402 for s in segments):
            return False
        if any(v["net"] != net and line.distance(Point(v["at_mm"])) < .627 for v in vias):
            return False
        return True

    def path(start, end, layer, net):
        if math.dist(start, end) < 1e-9:
            return [start, end]
        dx, dy = end[0] - start[0], end[1] - start[1]
        diagonal = min(abs(dx), abs(dy))
        sx, sy = math.copysign(1, dx), math.copysign(1, dy)
        options = [[start, end], [start, [start[0], end[1]], end], [start, [end[0], start[1]], end],
                   [start, [start[0] + sx * diagonal, start[1] + sy * diagonal], end],
                   [start, [end[0] - sx * diagonal, end[1] - sy * diagonal], end]]
        options = [p for p in options if path_clear(p, layer, net)]
        return min(options, key=lambda p: LineString(p).length) if options else None

    def append_path(points, layer, net):
        for a, b in zip(points, points[1:]):
            if math.dist(a, b) > 1e-9:
                segments.append(dict(start_mm=a, end_mm=b, layer=layer, net=net,
                                     width_mm=.2, shape=LineString([a, b])))

    def connect(endpoints, label):
        assert len({p["net"] for p in endpoints}) == 1
        net = endpoints[0]["net"]
        common = set(endpoints[0]["layers"])
        for p in endpoints[1:]:
            common &= set(p["layers"])
        if len(endpoints) == 2:
            for layer in ["F.Cu", "B.Cu"]:
                if layer in common:
                    points = path(endpoints[0]["position_mm"], endpoints[1]["position_mm"], layer, net)
                    if points is not None:
                        append_path(points, layer, net)
                        actions.append(dict(label=label, kind="direct_same_layer", net=net))
                        return True
        centres = [p["position_mm"] for p in endpoints]
        centres.append([math.fsum(p[i] for p in centres) / len(centres) for i in [0, 1]])
        candidates = set()
        for centre in centres:
            for radius in [.6, .7, .8, .9, 1., 1.1, 1.2, 1.4, 1.6, 1.8, 2., 2.3, 2.6]:
                for angle in range(0, 360, 30):
                    rad = math.radians(angle)
                    candidates.add((round(centre[0] + radius * math.cos(rad), 4),
                                    round(centre[1] + radius * math.sin(rad), 4)))
        ranked = sorted(candidates, key=lambda xy: math.fsum(math.dist(xy, p["position_mm"]) for p in endpoints))
        for xy in ranked:
            if not via_clear(xy, net):
                continue
            paths = []
            for p in endpoints:
                # Access an existing PTH directly from the counterpart's face.
                layer = p["side"] if p["SMD"] else next((s for s in ["B.Cu", "F.Cu"] if s in common), "F.Cu")
                points = path(p["position_mm"], list(xy), layer, net)
                if points is None:
                    break
                paths.append((points, layer))
            if len(paths) != len(endpoints):
                continue
            vias.append(dict(at_mm=list(xy), net=net, diameter_mm=.65, drill_mm=.3,
                             front_back_tented=True))
            for points, layer in paths:
                append_path(points, layer, net)
            actions.append(dict(label=label, kind="conventional_via", at_mm=list(xy), net=net))
            return True
        failures.append(dict(label=label, net=net, endpoints=[[p["ref"], p["pin"]] for p in endpoints]))
        return False

    paired = set()
    for a in plan["backside_bypass_assignments"]:
        cap, owner = a["cap"], a["owner"]
        source = by[(owner, a["owner_power_pin"])] if "owner_power_pin" in a else None
        power_net = next(p["net"] for p in parts[cap]["pins"] if p["number"] == "1")
        power_pins = [p["number"] for p in parts[owner]["pins"] if p["net"] == power_net
                      and p["kind"] in ["power_in", "power_out", "output"]]
        assert len(power_pins) == 1
        source = by[(owner, power_pins[0])]
        if connect([source, by[(cap, "1")]], cap + "_POWER"):
            paired |= {(owner, power_pins[0]), (cap, "1")}
        return_net = next(p["net"] for p in parts[cap]["pins"] if p["number"] == "2")
        returns = [p for p in parts[owner]["pins"] if p["net"] == return_net]
        preferred = [p for p in returns if p["kind"] == "power_in"]
        returns = preferred or returns
        assert returns, (cap, owner, return_net)
        ground = min((by[(owner, p["number"])] for p in returns),
                     key=lambda p: math.dist(p["position_mm"], by[(cap, "2")]["position_mm"]))
        if connect([ground, by[(cap, "2")]], cap + "_RETURN"):
            paired |= {(ground["ref"], ground["pin"]), (cap, "2")}
    # Additional AGND/AUX electrodes get a literal local conventional via.
    for p in pads:
        if p["SMD"] and p["pin"] and p["net"] in ["/AGND", "/AUX2V6"] and (p["ref"], p["pin"]) not in paired:
            connect([p], p["ref"] + "." + p["pin"] + "_PLANE")
    output = dict(source_PCB_sha256=data["source_PCB_sha256"],
                  source_geometry_sha256=hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
                  source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_clearance_mm=.2, extra_polygon_error_allowance_mm=.002,
                  same_net_SMD_hole_edge_gap_mm=.12, vias=vias,
                  segments=[{k: v for k, v in s.items() if k != "shape"} for s in segments],
                  actions=actions, unresolved=failures, native_DRC_required=True,
                  actual_plane_connectivity_and_local_return_inductance_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (OUTPUT / "plan.json").write_text(json.dumps(output, indent=2) + "\n")
    print(len(vias), "literal vias;", len(segments), "surface segments;", len(actions), "actions;", len(failures), "unresolved attempts")


if __name__ == "__main__":
    main()
