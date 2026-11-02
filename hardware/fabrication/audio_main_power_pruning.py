"""Remove abandoned V3V3 leaves while protecting every actual power terminal."""

import math


def prune(captured, net="V3V3_IO"):
    from shapely.geometry import Point

    from hardware.fabrication.route_nf_surface import shape

    removed = []
    while True:
        objects = [o for o in captured["objects"] if o["net"] == net]
        tracks = [o for o in objects if o["kind"] == "PCB_TRACK"]
        vias = [o for o in objects if o["kind"] == "PCB_VIA"]
        copper = {(o["uuid"], layer): shape(ps) for o in objects for layer, ps in o["layers"].items() if ps}

        def terminal_present(point, layers):
            p = Point(point)
            return any(o["kind"] == "PAD" and any((o["uuid"], layer) in copper and
                       copper[o["uuid"], layer].covers(p) for layer in layers) for o in objects)

        leaves = set()
        for track in tracks:
            for endpoint in (track["position_mm"], track["end_mm"]):
                faces = set(track["layers"])
                at_via = [o for o in vias if math.dist(endpoint, o["position_mm"]) < 1e-7]
                for via in at_via:
                    faces.update(via["layers"])
                if terminal_present(endpoint, faces):
                    continue
                p = Point(endpoint)
                connected = any(other["uuid"] != track["uuid"] and any((other["uuid"], layer) in copper and
                                copper[other["uuid"], layer].covers(p) for layer in faces) for other in tracks)
                if not connected:
                    leaves.add(track["uuid"])
                    leaves.update(o["uuid"] for o in at_via)
                    break
        if not leaves:
            break
        removed.extend(o["uuid"] for o in captured["objects"] if o["uuid"] in leaves)
        captured["objects"] = [o for o in captured["objects"] if o["uuid"] not in leaves]
    assert len(removed) == len(set(removed))
    return removed
