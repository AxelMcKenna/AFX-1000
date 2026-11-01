"""Measure local authored paths, actual barrels and nominal stack distances.

Zones provide no graph shortcuts. This is a routing diagnostic, not impedance,
EM, capacitance, assembly-process or physical qualification.
"""

import hashlib
import heapq
import json
import math
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def run():
    source = WORK/"generated/native-closed-transmitter"
    output = source/"local-bypass-inventory.json"
    assert not output.exists()
    pcb = source/"power_p03.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    pads = json.loads((source/"pads.json").read_text())["pad_polygons"]
    by = {(p["ref"],p["pin"]): p for p in pads}
    depth, levels = 0, {}
    for layer in children(first(first(tree,"setup"),"stackup"),"layer"):
        if not children(layer,"thickness"):
            continue
        thickness = float(first(layer,"thickness")[1])
        if str(layer[1]).endswith(".Cu"):
            levels[str(layer[1])] = depth+thickness/2
        depth += thickness
    assert tuple(levels) == LAYERS and math.isclose(depth,1.6)
    rows = []
    for cap,ic,supply,ground,bounds in (("C402","U201","4","2",(100.2,115,108,126.5)),
                                      ("C401","U202","5","3",(108,130,119,140))):
        for cpin,ipin,net in (("1",supply,"V2V5_AUX"),("2",ground,"AGND")):
            region, graph = box(*bounds), defaultdict(dict)

            def node(point,layer):
                return (round(float(point[0]),6),round(float(point[1]),6),layer)

            def link(left,right,length):
                if left != right:
                    graph[left][right] = min(length,graph[left].get(right,math.inf))
                    graph[right][left] = min(length,graph[right].get(left,math.inf))

            for layer in LAYERS:
                lines = []
                for segment in children(tree,"segment"):
                    if first(segment,"layer")[1] != layer or first(segment,"net")[1] != "/"+net or float(first(segment,"width")[1]) < .2:
                        continue
                    line = LineString([tuple(map(float,first(segment,key)[1:3])) for key in ("start","end")])
                    if region.covers(line):
                        lines.append(line)
                union = unary_union(lines)
                for line in union.geoms if hasattr(union,"geoms") else [union]:
                    if line.is_empty:
                        continue
                    points = [node(p,layer) for p in line.coords]
                    for left,right in zip(points,points[1:]):
                        link(left,right,math.dist(left[:2],right[:2]))
            vias = {}
            for via in children(tree,"via"):
                if first(via,"net")[1] != "/"+net:
                    continue
                point = tuple(map(float,first(via,"at")[1:3]))
                if not region.covers(Point(point)):
                    continue
                identifier = str(first(via,"uuid")[1])
                vias[node(point,"F.Cu")[:2]] = identifier
                for left,right in zip(LAYERS,LAYERS[1:]):
                    link(node(point,left),node(point,right),levels[right]-levels[left])
            # Electrode-internal links stay inside actual native SMD pad copper
            # outlines. A barrel centre is a CAD electrode abstraction, not a
            # claim that an unfilled drill is a sheet of surface copper.
            for pad in pads:
                if pad["net"] != net or not region.covers(Point(pad["position_mm"])):
                    continue
                for layer,polygons in pad["layers"].items():
                    if layer not in LAYERS:
                        continue
                    shape = unary_union([Polygon(p["outer"]) for p in polygons]).buffer(1e-6)
                    centre = node(pad["position_mm"],layer)
                    nearby = [p for p in graph if p[2] == layer and shape.covers(Point(p[:2]))]
                    for p in nearby:
                        link(centre,p,math.dist(centre[:2],p[:2]))
            start,end = node(by[cap,cpin]["position_mm"],"F.Cu"),node(by[ic,ipin]["position_mm"],"F.Cu")
            queue, costs, previous, seen = [(0,start)], {start:0}, {}, set()
            while queue:
                distance,current = heapq.heappop(queue)
                if current in seen:
                    continue
                seen.add(current)
                if current == end:
                    break
                for other,length in graph[current].items():
                    if distance+length < costs.get(other,math.inf):
                        costs[other],previous[other] = distance+length,current
                        heapq.heappush(queue,(costs[other],other))
            assert end in seen, (cap,cpin,"No local authored/barrel path")
            path = [end]
            while path[-1] != start:
                path.append(previous[path[-1]])
            path.reverse()
            rows.append(dict(capacitor=f"{cap}.{cpin}",IC=f"{ic}.{ipin}",net=net,
                local_bounds_mm=bounds, minimum_track_width_mm=.2,
                actual_authored_and_barrel_path_found=True, nominal_path_length_mm=costs[end],
                copper_layers=sorted({p[2] for p in path},key=LAYERS.index),
                path_mm=path, via_UUIDs=sorted({vias[p[:2]] for p in path if p[:2] in vias}),
                effective_capacitance_and_PDN_EM_qualified=False))
    strict = WORK.parent/"strict-native-centering/power_p03.kicad_pcb"
    original_vias = {str(first(v,"uuid")[1]) for v in children(read_sexpr(strict.read_text()),"via")}
    vip = []
    for via in children(tree,"via"):
        identifier = str(first(via,"uuid")[1])
        if identifier in original_vias:
            continue
        point = tuple(map(float,first(via,"at")[1:3]))
        drill = Point(point).buffer(float(first(via,"drill")[1])/2)
        hits = [p["ref"]+"."+p["pin"] for p in pads if p["attribute"] == 1
                and any(drill.intersects(Polygon(poly["outer"])) for poly in p["layers"].get("F.Cu",[]))]
        if hits:
            vip.append(dict(uuid=identifier, centre_mm=point, land_mm=float(first(via,"size")[1]),
                drill_mm=float(first(via,"drill")[1]), overlapping_SMD_copper=hits,
                filling_metadata=[str(n[1:]) for n in children(via,"filling")],
                capping_metadata=[str(n[1:]) for n in children(via,"capping")],
                filled_capped_receiving_required=True, metadata_drawing_reconciled=False, supplier_accepted=False))
    inputs = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (pcb,source/"pads.json",strict,Path(__file__))}
    output.write_text(json.dumps(dict(source_sha256=inputs, local_paths=rows, nominal_stack_layer_centres_mm=levels,
        new_drills_overlapping_SMD_copper=vip,
        via_centre_is_CAD_electrode_abstraction=True, no_zone_shortcuts=True,
        filled_capped_receiving_process_and_independent_PDN_review_required=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print([(r["capacitor"],round(r["nominal_path_length_mm"],3),r["copper_layers"]) for r in rows])


if __name__ == "__main__":
    run()
