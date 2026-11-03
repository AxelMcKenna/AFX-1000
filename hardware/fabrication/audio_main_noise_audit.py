"""Measure trace-to-noisy-copper gaps exhaustively, without a spatial index."""

from shapely.geometry import LineString

from hardware.fabrication.route_nf_surface import shape


def measure(captured, quiet_nets, noisy_nets, limit=.71, quiet_tracks=None):
    noisy = [(o, face, shape(polygons)) for o in captured["objects"] if o["net"] in noisy_nets
             for face, polygons in o["layers"].items() if polygons]
    traces = ([o for o in captured["objects"] if o["kind"] == "PCB_TRACK" and o["net"] in quiet_nets]
              if quiet_tracks is None else quiet_tracks)
    checks, violations, minima = 0, [], {}
    for obj in traces:
        line = LineString([obj["position_mm"], obj["end_mm"]])
        for other, face, copper in noisy:
            faces = obj.get("copper_faces", obj.get("layers", {}))
            if face not in faces:
                continue
            checks += 1
            distance = line.distance(copper)
            minima[obj["net"]] = min(minima.get(obj["net"], float("inf")), distance)
            if distance <= limit:
                violations.append(dict(trace_uuid=obj["uuid"], net=obj["net"], layer=face,
                                       noisy_uuid=other["uuid"], noisy_net=other["net"],
                                       centreline_to_copper_mm=distance))
    return dict(trace_count=len(traces), same_layer_pairs_measured=checks,
                centreline_limit_mm=limit, minimum_by_net_mm={n: round(d, 9) for n, d in sorted(minima.items())},
                violations=violations, method="all same-layer trace/copper pairs; no broad-phase exclusion")
