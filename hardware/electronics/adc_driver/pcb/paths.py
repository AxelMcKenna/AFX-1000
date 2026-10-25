"""Portable checks against actual copper, not router labels or schematic intent."""

import copy
import math
from collections import deque

from ...common.sexpr import a as atom
from ...common.sexpr import children, first
from ...output_stage.check_placement import transform
from ...rail_disconnect.routing.check import copper_path, point_segment, segment_distance

LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def normalized(tree):
    """Accept both KiCad 8 numeric nets and KiCad 10 named-net serialization."""
    tree = copy.deepcopy(tree)
    if children(tree, "net"):
        return tree
    names = set()

    def visit(node):
        if isinstance(node, list):
            if node and node[0] == "net":
                names.add(str(node[-1]))
            for item in node:
                visit(item)

    visit(tree)
    codes = {name: i + 1 for i, name in enumerate(sorted(names))}

    def update(node):
        if isinstance(node, list):
            if node and node[0] == "net":
                name = str(node[-1])
                node[:] = [atom("net"), codes[name], name]
            else:
                for item in node:
                    update(item)

    update(tree)
    tree.extend([atom("net"), code, name] for name, code in codes.items())
    return tree


def local_feedback(tree):
    tree = normalized(tree)
    result = {}
    for ci, ch in enumerate(("L", "R")):
        u = "U" + str(ci + 1)
        for net, pin, r, c in [
            ("FB_N_" + ch, 1, 2, 2),
            ("FB_N_" + ch, 1, 4, 2),
            ("FB_P_" + ch, 8, 1, 1),
            ("FB_P_" + ch, 8, 3, 1),
        ]:
            for ref, num in [("R" + str(r + 16 * ci), 2), ("C" + str(c + 14 * ci), 2)]:
                length = copper_path(tree, net, (u, pin, 0), (ref, num, 0), 0.25)
                assert length < 22, ("FDA local feedback detour", net, ref, length)
                result[net + "_" + ref] = length
        for pin, r, c in [(4, 5, 2), (5, 6, 1)]:
            net = "DRV_" + ch + ("P" if pin == 4 else "N")
            for ref, num in [("R" + str(r + 16 * ci), 1), ("C" + str(c + 14 * ci), 1)]:
                length = copper_path(tree, net, (u, pin, 0), (ref, num, 0), 0.25)
                assert length < 25, ("FDA output detour", net, ref, length)
                result[net + "_" + ref] = length
    for net, start, end in [
        ("BUF_L", ("U3", 1, 0), ("U3", 2, 0)),
        ("BUF_R", ("U3", 7, 0), ("U3", 6, 0)),
        ("REF_HALF_L", ("U4", 1, 0), ("U4", 2, 0)),
        ("REF_HALF_R", ("U4", 8, 0), ("U4", 9, 0)),
    ]:
        length = copper_path(tree, net, start, end, 0.25)
        assert length < 6, ("Buffer feedback detour", net, length)
        result[net] = length
    return result


def objects(tree, net):
    tree = normalized(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    result = []
    for s in children(tree, "segment"):
        if names[str(first(s, "net")[1])] == net:
            result.append(
                dict(
                    kind="line",
                    p=tuple(map(float, first(s, "start")[1:3])),
                    q=tuple(map(float, first(s, "end")[1:3])),
                    r=float(first(s, "width")[1]) / 2,
                    layers={str(first(s, "layer")[1])},
                )
            )
    for v in children(tree, "via"):
        if names[str(first(v, "net")[1])] == net:
            result.append(
                dict(
                    kind="circle",
                    p=tuple(map(float, first(v, "at")[1:3])),
                    r=float(first(v, "size")[1]) / 2,
                    layers=set(LAYERS),
                    via=True,
                )
            )
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
        for pad in children(fp, "pad"):
            if not children(pad, "net") or str(first(pad, "net")[-1]).lstrip("/") != net:
                continue
            xy = tuple(map(float, transform(fp, first(pad, "at")[1:3])))
            size = tuple(map(float, first(pad, "size")[1:3]))
            size = size[::-1] if int(angle) % 180 else size
            through = pad[2] == "thru_hole"
            result.append(
                dict(
                    kind="rect",
                    p=xy,
                    size=size,
                    r=0,
                    layers=set(LAYERS) if through else {str(first(fp, "layer")[1])},
                    pad=(ref, str(pad[1])),
                    through=through,
                )
            )
    return result


def rect_edges(o):
    x, y = o["p"]
    w, h = o["size"]
    x0, x1 = x - w / 2, x + w / 2
    y0, y1 = y - h / 2, y + h / 2
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def point_rect(p, o):
    return math.hypot(
        max(abs(p[0] - o["p"][0]) - o["size"][0] / 2, 0), max(abs(p[1] - o["p"][1]) - o["size"][1] / 2, 0)
    )


def separation(a, b):
    if a["kind"] == "rect" and b["kind"] == "rect":
        return math.hypot(
            *(max(abs(a["p"][k] - b["p"][k]) - (a["size"][k] + b["size"][k]) / 2, 0) for k in (0, 1))
        )
    if a["kind"] == "rect" or b["kind"] == "rect":
        if b["kind"] == "rect":
            a, b = b, a
        if b["kind"] == "circle":
            return point_rect(b["p"], a)
        if not point_rect(b["p"], a) or not point_rect(b["q"], a):
            return 0
        return min(segment_distance(b["p"], b["q"], c, d) for c, d in rect_edges(a))
    if a["kind"] == "circle" and b["kind"] == "circle":
        return math.dist(a["p"], b["p"])
    if a["kind"] == "circle":
        return point_segment(a["p"], b["p"], b["q"])
    if b["kind"] == "circle":
        return point_segment(b["p"], a["p"], a["q"])
    return segment_distance(a["p"], a["q"], b["p"], b["q"])


def graph(items):
    edges = [set() for _ in items]
    for i, a in enumerate(items):
        for j, b in enumerate(items[:i]):
            if a["layers"] & b["layers"] and separation(a, b) <= a["r"] + b["r"] + 1e-6:
                edges[i].add(j)
                edges[j].add(i)
    return edges


def reachable(edges, start, excluded=()):
    seen = set(excluded)
    pending = deque([start])
    found = set()
    while pending:
        i = pending.popleft()
        if i in seen:
            continue
        seen.add(i)
        found.add(i)
        pending.extend(edges[i] - seen)
    return found


def header_sense_contract(tree):
    result = {}
    for ci, ch in enumerate(("L", "R")):
        for pol, offset in [("P", 0), ("N", 1)]:
            net = "ADC_" + ch + pol
            items = objects(tree, net)
            edges = graph(items)
            pads = {o["pad"]: i for i, o in enumerate(items) if "pad" in o}
            h = pads[("J2", str(1 + 3 * ci + offset))]
            force = pads[("R" + str((5 if pol == "P" else 6) + 16 * ci), "2")]
            senses = [pads[("R" + str(k + 16 * ci), "1")] for k in ((4, 10) if pol == "P" else (3, 11))]
            all_connected = reachable(edges, force)
            assert h in all_connected and all(s in all_connected for s in senses), (
                net,
                "sense/force not connected at header",
            )
            without_header = reachable(edges, force, {h})
            assert all(s not in without_header for s in senses), (
                net,
                "sense merges with force before J2 terminal",
            )
            sense_component = reachable(edges, senses[0], {h})
            assert senses[1] in sense_component, (net, "CM and FDA sense paths split before header")
            result[net] = dict(
                force_land=items[force]["pad"],
                sense_lands=[items[s]["pad"] for s in senses],
                common_terminal=items[h]["pad"],
                header_terminal_removal_separates_force_and_sense=True,
                converter_pin_kelvin_verified=False,
            )
    return result


def in_polygon(point, vertices):
    inside = False
    x, y = point
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def ground_contract(filled):
    planes = {}
    for z in children(filled, "zone"):
        if children(z, "keepout"):
            continue
        assert str(first(z, "net")[-1]).lstrip("/") == "AGND"
        layer = str(first(z, "layer")[1])
        fills = children(z, "filled_polygon")
        assert layer in ("In1.Cu", "In4.Cu") and len(fills) == 1, ("Disconnected/missing ground fill", layer)
        planes[layer] = [tuple(map(float, p[1:3])) for p in children(first(fills[0], "pts"), "xy")]
    assert set(planes) == {"In1.Cu", "In4.Cu"}
    # No foreign tracks are allowed to split either reference plane.
    assert not any(
        str(first(s, "layer")[1]) in planes and str(first(s, "net")[-1]).lstrip("/") != "AGND"
        for s in children(filled, "segment")
    )
    items = objects(filled, "AGND")
    edges = graph(items)
    anchors = {
        i
        for i, o in enumerate(items)
        if (o.get("via") or o.get("through")) and all(in_polygon(o["p"], p) for p in planes.values())
    }
    assert anchors, "No ground contacts touch both actual fills"
    paths = {}
    for i, o in enumerate(items):
        if "pad" not in o:
            continue
        component = reachable(edges, i)
        candidates = component & anchors
        assert candidates, ("Ground land has no actual copper escape to both planes", o["pad"])
        nearest = min(math.dist(o["p"], items[j]["p"]) for j in candidates)
        assert nearest < 7, ("Nonlocal ground escape", o["pad"], nearest)
        paths[".".join(o["pad"])] = round(nearest, 6)
    return dict(
        native_filled_polygons_per_plane=1,
        plane_layers=list(planes),
        ground_lands_with_local_actual_plane_contact=len(paths),
        ground_land_nearest_plane_contact_mm=paths,
        quiet_return_or_noise_verified=False,
    )
