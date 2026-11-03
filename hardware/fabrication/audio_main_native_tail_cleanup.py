"""Walk abandoned rail tails by track centre lines, preserving actual pad lands.

Round copper end caps can cover a neighbouring tail's free end. That is not
evidence of a routed junction; use centre-line incidence when pruning tails.
"""

import math

from shapely.geometry import LineString, Point

from hardware.electronics.common.sexpr import children, first
from hardware.fabrication.route_nf_surface import shape


def prune(board, captured, initial):
    names = {n[1]: str(n[2]) for n in children(board, "net")}
    tracks = {str(first(n, "uuid")[1]): n for n in children(board, "segment")}
    vias = {str(first(n, "uuid")[1]): n for n in children(board, "via")}
    pads = [p for p in captured["objects"] if p["kind"] == "PAD" and p["pin"]]
    queue, retired = sorted(initial), []
    geometry = {i: LineString([list(map(float, first(n, k)[1:3])) for k in ("start", "end")])
                for i, n in tracks.items()}

    def xy(n):
        return tuple(map(float, first(n, "at")[1:3]))

    def terminal(net, point, faces):
        return any(p["net"] == net and any(shape(p["layers"].get(face, [])).buffer(.000001).covers(Point(point))
                   for face in faces if p["layers"].get(face)) for p in pads)

    while queue:
        ident = queue.pop()
        if ident not in tracks:
            continue
        node = tracks[ident]
        net = names[first(node, "net")[1]]
        assert net in ("V3V3_IO", "5V_DIG"), "Only native-identified abandoned rail chains may be pruned"
        ends = [tuple(map(float, first(node, k)[1:3])) for k in ("start", "end")]
        faces = {str(first(node, "layer")[1])}
        is_leaf = False
        for point in ends:
            connected_vias = [v for v in vias.values() if names[first(v, "net")[1]] == net and
                              math.dist(point, xy(v)) <= float(first(v, "size")[1])/2+.000001]
            available = {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"} if connected_vias else faces
            # Stop at a plated junction. Pruning a live rail tree through a
            # via requires a separate native connectivity decision.
            if connected_vias or terminal(net, point, available):
                continue
            adjacent = [i for i, n in tracks.items() if i != ident and names[first(n, "net")[1]] == net and
                        first(n, "layer")[1] in available and geometry[i].distance(Point(point)) < .000001]
            if not adjacent:
                is_leaf = True
                break
        if not is_leaf:
            continue
        retired.append(tracks.pop(ident))
        for point in ends:
            attached_vias = [(i, v) for i, v in vias.items() if names[first(v, "net")[1]] == net and
                             math.dist(point, xy(v)) <= float(first(v, "size")[1])/2+.000001]
            available = {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"} if attached_vias else faces
            adjacent = [i for i, n in tracks.items() if names[first(n, "net")[1]] == net and
                        first(n, "layer")[1] in available and geometry[i].distance(Point(point)) < .000001]
            if not adjacent and not terminal(net, point, available):
                for i, _ in attached_vias:
                    retired.append(vias.pop(i))
            queue.extend(adjacent)
        assert len(retired) <= 64, "Stop an unexpected large pruning operation"
    ids = {str(first(n, "uuid")[1]) for n in retired}
    assert initial <= ids
    result = [n for n in board if not isinstance(n, list) or not n or n[0] not in ("segment", "via") or
              str(first(n, "uuid")[1]) not in ids]
    return result, retired
