"""E13 trace/barrel sensitivity model with explicitly ideal pads and power plane."""

import argparse
import hashlib
import heapq
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import native_evidence_errors
from hardware.fabrication.evidence_paths import recorded_path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("hardware/fabrication/staging/rail-monitor-reserved-closed-native-02")
CAPTURE = Path("hardware/fabrication/staging/rail-monitor-dc-inputs-01/capture.json")
PLANES = CAPTURE.with_name("unfractured-planes.json")
NET = "/V3V3_IO"
SOURCE = ("@ideal_supply_plane", 0.0, 0.0)
SCENARIOS = [
    dict(name="illustrative_20C", temperature_c=20, conductivity_IACS=1.0,
         outer_um=35, inner_um=17.5, plating_um=20, board_mm=1.6),
    dict(name="thin_hot_sensitivity", temperature_c=85, conductivity_IACS=0.9,
         outer_um=25, inner_um=12, plating_um=15, board_mm=1.8),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resistivity(temperature_c, conductivity_IACS):
    if conductivity_IACS <= 0 or temperature_c < -55 or temperature_c > 125:
        raise ValueError("Conductivity must be positive; temperature screen is -55..125 C")
    # NBS Circular 31: volume resistivity, including the expansion correction.
    return 1.7241e-8 / conductivity_IACS * (1 + 0.003947 * (temperature_c - 20))


def track_ohm(length_mm, width_mm, thickness_um, rho):
    if length_mm < 0 or min(width_mm, thickness_um, rho) <= 0:
        raise ValueError("Invalid trace dimensions or resistivity")
    return rho * length_mm * 1e6 / (width_mm * thickness_um)


def barrel_ohm(length_mm, finished_drill_mm, plating_um, rho):
    if min(length_mm, finished_drill_mm, plating_um, rho) <= 0:
        raise ValueError("Invalid via dimensions or resistivity")
    thickness_mm = plating_um / 1000
    area_mm2 = math.pi * (finished_drill_mm * thickness_mm + thickness_mm**2)
    return rho * 1000 * length_mm / area_mm2


def geometry(rows):
    polygons = [Polygon(row["outer"], row["holes"]) for row in rows]
    if any(not p.is_valid for p in polygons):
        raise ValueError("Invalid native polygon; do not silently repair copper")
    return unary_union(polygons)


def key(layer, point):
    return layer, round(point[0], 6), round(point[1], 6)


def solve(capture, drills, scenario):
    objects = [o for o in capture["objects"] if o["net"] == NET]
    tracks = [o for o in objects if o["kind"] == "PCB_TRACK"]
    contacts = [o for o in objects if o["kind"] in ("PAD", "PCB_VIA")]
    rho = resistivity(scenario["temperature_c"], scenario["conductivity_IACS"])
    nodes = set()
    lines = []
    graph = defaultdict(list)

    def edge(a, b, resistance, kind, uid):
        if a != b:
            graph[a].append((b, resistance, kind, uid))
            graph[b].append((a, resistance, kind, uid))

    for track in tracks:
        if len(track["layers"]) != 1:
            raise ValueError("A track must occupy exactly one copper layer")
        layer = next(iter(track["layers"]))
        line = LineString([track["position_mm"], track["end_mm"]])
        lines.append((track, layer, line))
        nodes.update(key(layer, xy) for xy in line.coords)
    for contact in contacts:
        nodes.update(key(layer, contact["position_mm"]) for layer in contact["layers"])
    for (_, la, a), (_, lb, b) in itertools.combinations(lines, 2):
        if la != lb:
            continue
        intersection = a.intersection(b)
        if intersection.is_empty:
            continue
        if intersection.geom_type == "Point":
            nodes.add(key(la, intersection.coords[0]))
        elif intersection.geom_type == "LineString":
            nodes.update(key(la, xy) for xy in intersection.coords)
        else:
            raise ValueError("Unexpected centerline intersection")
    for track, layer, line in lines:
        ordered = sorted(
            ((line.project(Point(n[1:])), n) for n in nodes
             if n[0] == layer and line.distance(Point(n[1:])) < 1e-6),
        )
        thickness = scenario["outer_um"] if layer in ("F.Cu", "B.Cu") else scenario["inner_um"]
        for (left, a), (right, b) in zip(ordered, ordered[1:]):
            edge(a, b, track_ohm(right-left, track["width_mm"], thickness, rho), "track", track["uuid"])
    planes = defaultdict(list)
    for zone in capture["zones"]:
        if zone["net"] == NET and not zone["keepout"]:
            planes[zone["layer"]].append(geometry(zone["polygons"]))
    planes = {layer: unary_union(polygons) for layer, polygons in planes.items()}
    targets = {}
    for contact in contacts:
        if contact["kind"] == "PAD":
            name = f"{contact['ref']}.{contact['pin']}"
            hub = ("@pad:"+name, 0.0, 0.0)
            targets[name] = hub
            half_barrel = 0
        else:
            hub = ("@via:"+contact["uuid"], 0.0, 0.0)
            half_barrel = barrel_ohm(scenario["board_mm"], drills[contact["uuid"]], scenario["plating_um"], rho) / 2
        for layer, polygons in contact["layers"].items():
            center = key(layer, contact["position_mm"])
            edge(center, hub, half_barrel, "barrel" if half_barrel else "ideal_pad", contact["uuid"])
            shape = geometry(polygons)
            for node in nodes:
                if node[0] == layer and shape.covers(Point(node[1:])):
                    edge(node, center, 0, "ideal_contact", contact["uuid"])
            if layer in planes and shape.intersection(planes[layer]).area > 1e-9:
                edge(center, SOURCE, 0, "ideal_plane", contact["uuid"])
    for node in nodes:
        if node[0] in planes and planes[node[0]].covers(Point(node[1:])):
            edge(node, SOURCE, 0, "ideal_plane", "")
    distances, previous, queue = {SOURCE: 0.0}, {}, [(0.0, SOURCE)]
    while queue:
        distance, current = heapq.heappop(queue)
        if distance != distances[current]:
            continue
        for other, resistance, kind, uid in graph[current]:
            trial = distance + resistance
            if trial < distances.get(other, math.inf):
                distances[other], previous[other] = trial, (current, resistance, kind, uid)
                heapq.heappush(queue, (trial, other))
    if any(hub not in distances for hub in targets.values()):
        raise ValueError("Model has unreached pads: "+str(sorted(name for name, hub in targets.items() if hub not in distances)))
    result = []
    for name, hub in sorted(targets.items()):
        steps, at = [], hub
        while at != SOURCE:
            parent, resistance, kind, uid = previous[at]
            step = dict(kind=kind, object_uuid=uid, resistance_ohm=resistance)
            if kind == "track":
                step.update(layer=parent[0], start_mm=list(parent[1:]), end_mm=list(at[1:]))
            steps.append(step)
            at = parent
        result.append(dict(pad=name, path_resistance_ohm=distances[hub], steps=list(reversed(steps))))
    maximum = max(result, key=lambda row: row["path_resistance_ohm"])
    return dict(inputs=scenario, rho_ohm_m=rho, paths=result, worst_pad=maximum["pad"],
                maximum_path_ohm=maximum["path_resistance_ohm"],
                illustrative_20mA_drop_v=maximum["path_resistance_ohm"]*0.020)


def build():
    capture_path = REPO / CAPTURE
    capture = json.loads(capture_path.read_text())
    plane_capture = json.loads((REPO / PLANES).read_text())
    if capture["native_uncapped_opens"] != 0:
        raise ValueError("Require a natively connected source")
    for packet in (capture, plane_capture):
        for name, digest in packet["source_sha256"].items():
            if sha(recorded_path(name)) != digest:
                raise ValueError("Stale native capture: "+name)
    capture["zones"] = plane_capture["zones"]
    project = REPO / ROOT / "rail_monitor.kicad_pro"
    review = json.loads((project.parent / "review.json").read_text())
    if native_evidence_errors(project, review) or not review["status"]["native_closed"]:
        raise ValueError("Require current zero-finding native evidence")
    board = read_sexpr(project.with_suffix(".kicad_pcb").read_text())
    drills = {first(v, "uuid")[1]: float(first(v, "drill")[1]) for v in children(board, "via")}
    tracks = [o for o in capture["objects"] if o["kind"] == "PCB_TRACK" and o["net"] == NET]
    return dict(
        schema="E13-trace-barrel-sensitivity-1", net=NET,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in (
            capture_path, REPO / PLANES, project.with_suffix(".kicad_pcb"), project.parent / "review.json", Path(__file__),
        )},
        copper_reference="https://nvlpubs.nist.gov/nistpubs/Legacy/circ/nbscircular31.pdf",
        reference_model="ideal In2 V3V3_IO plane; not connector-to-load total resistance",
        native_capture_polygon_error=capture["obstacle_polygons_error"],
        track_count_by_layer=dict(Counter(next(iter(t["layers"])) for t in tracks)),
        track_length_mm_by_layer={layer: sum(math.dist(t["position_mm"], t["end_mm"]) for t in tracks if layer in t["layers"])
                                  for layer in sorted({next(iter(t["layers"])) for t in tracks})},
        scenarios=[solve(capture, drills, case) for case in SCENARIOS],
        omissions=["finite pad/annulus and junction spreading", "power-plane and thermal-spoke resistance",
                   "connector contacts and inlet plated barrel", "ground-return resistance", "source/harness resistance",
                   "actual static and dynamic current envelope", "L/C impedance and decoupling", "fabricator process tolerances"],
        whole_PDN_upper_bound_established=False, stackup_and_copper_process_accepted=False,
        electrical_qualified=False, fabrication_approved=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build()
    data = json.dumps(report, indent=2) + "\n"
    if args.check:
        if args.output.read_text() != data:
            raise SystemExit("Stale DC-path sensitivity report")
    else:
        with args.output.open("x") as stream:
            stream.write(data)
    print(json.dumps({row["inputs"]["name"]: {k: row[k] for k in ("worst_pad", "maximum_path_ohm", "illustrative_20mA_drop_v")}
                      for row in report["scenarios"]}))


if __name__ == "__main__":
    main()
