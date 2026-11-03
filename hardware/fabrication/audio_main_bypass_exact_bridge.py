"""Construct an exactly screened repair through the SOIC pad gaps missed by the grid."""

import math

from shapely.geometry import LineString

from hardware.fabrication.audio_main_global_controls import SignalScreen
from hardware.fabrication.route_nf_surface import candidate_paths, shape


def input_enable(captured, seed_routes, port):
    net = "/BYPASS/INPUT_ENABLE"
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {i: key for key, ids in captured["groups"].items() for i in ids}
    root = next(o for o in objects.values() if o["kind"] == "PCB_VIA" and o["net"] == net and
                math.dist(o["position_mm"], [65, 41.7]) < 1e-7)
    root_group = membership[root["uuid"]]
    port_group = membership[pads["U606", "12"]["uuid"]]
    assert root_group != port_group
    screen = SignalScreen(captured)
    for row in seed_routes:
        for layer, points in row["runs"]:
            screen.added.append((row["net"], layer, LineString(points)))
        screen.new_vias.extend((row["net"], p) for p in row["new_vias_mm"])
    left_y = round((shape(pads["U606", "2"]["layers"]["B.Cu"]).bounds[3]+
                    shape(pads["U606", "1"]["layers"]["B.Cu"]).bounds[1])/2, 8)
    right_y = round((shape(pads["U606", "12"]["layers"]["B.Cu"]).bounds[3]+
                     shape(pads["U606", "13"]["layers"]["B.Cu"]).bounds[1])/2, 8)
    for point in ([64.2, 46], [64, 46], [64.2, 45.6], [64.4, 46.2], [63.8, 46]):
        if not screen.via_legal(net, point):
            continue
        back = [point, [64.8, left_y], [68.4, left_y], [69.8, right_y], [73, right_y], port["point"]]
        if not screen.legal(net, "B.Cu", back):
            continue
        for front in candidate_paths(root["position_mm"], point):
            front = [p for i, p in enumerate(front) if not i or p != front[i-1]]
            if not screen.legal(net, "F.Cu", front):
                continue
            runs = [("F.Cu", front), ("B.Cu", back)]
            length = sum(LineString(p).length for _, p in runs)
            terminals = [root["position_mm"], port["point"]]
            physical = [root["position_mm"], pads["U606", "12"]["position_mm"]]
            full = length+sum(LineString(p).length for _, p in port["runs"])
            limit = min(180, 2.5*math.dist(*physical)+10)
            if full > limit:
                continue
            return dict(net=net, runs=runs, vias=[point], groups=[root_group, port_group],
                        source_groups=[[root_group], [port_group]], portals=terminals, terminal_points_mm=terminals,
                        new_vias_mm=[point], planar_length_mm=length,
                        maximum_planar_length_mm=min(180, 2.5*math.dist(*terminals)+10), search_visits=0,
                        layer_transition_count=1, planned_by="exact_native_pad_gap_bridge",
                        physical_terminal_points_mm=physical, escape_inclusive_length_mm=full,
                        fresh_vias_including_reserved=1, maximum_escape_inclusive_length_mm=limit)
    return None
