"""Join actual native copper components using every physical anchor jointly.

The search joins real pads, vias or track centres. It adds ordinary copper and
drills; the unfiltered native DRC remains the authority for physical closure.
"""

import argparse
import hashlib
import heapq
import itertools
import json
import math
import uuid
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..revision26 import router as aid
from .repair import ROOT, Router


def connect_components(rt, row, width=0.2, budget=500000):
    net = row["net"]
    blocked, via = rt.masks(net, width)
    if getattr(rt, "force_guard", None) is not None:
        blocked, via = rt.force_guard.apply(net, blocked, via, width)
    anchors = []
    for group in row["components"]:
        states = {}
        for point in group:
            x, y = (round(v / aid.STEP) for v in point["xy"])
            if not (0 <= x < rt.nx and 0 <= y < rt.ny):
                continue
            for z in point["layers"]:
                state = (x, y, z)
                states.setdefault(state, point)
                blocked[z, x, y] = False
            if rt.existing_via(net, point["xy"]) is not None:
                via[x, y] = False
        anchors.append(states)
    starts, goals = anchors
    if not starts or not goals:
        return dict(connected=False, reason="no_native_component_anchor")
    # Distance to the whole target component avoids spending repeated searches
    # on one trapped nearest via while another real terminal is accessible.
    target = np.ones((rt.nx, rt.ny), dtype=bool)
    for x, y, _ in goals:
        target[x, y] = False
    heuristic = distance_transform_edt(target)
    serial = itertools.count()
    queue = [(2 * heuristic[x, y], next(serial), (x, y, z)) for x, y, z in starts]
    heapq.heapify(queue)
    costs = dict.fromkeys(starts, 0.0)
    previous = {}
    visited = set()
    found = None
    while queue:
        _, _, point = heapq.heappop(queue)
        if point in visited:
            continue
        visited.add(point)
        if len(visited) > budget:
            break
        if point in goals:
            found = point
            break
        x, y, z = point
        neighbors = [
            (x + dx, y + dy, z, math.hypot(dx, dy))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
            if 0 <= x + dx < rt.nx and 0 <= y + dy < rt.ny and not blocked[z, x + dx, y + dy]
        ]
        if not via[x, y]:
            neighbors.extend((x, y, w, 12) for w in range(6) if w != z and not blocked[w, x, y])
        for u, v, w, increment in neighbors:
            other = (u, v, w)
            cost = costs[point] + increment
            if cost < costs.get(other, float("inf")):
                costs[other] = cost
                previous[other] = point
                heapq.heappush(queue, (cost + 2 * heuristic[u, v], next(serial), other))
    if found is None:
        return dict(
            connected=False,
            reason="node_budget" if queue else "no_clearance_path",
            visited=len(visited),
            native_anchor_states=[len(x) for x in anchors],
        )
    nodes = [found]
    while nodes[-1] in previous:
        nodes.append(previous[nodes[-1]])
    nodes.reverse()
    source = starts[nodes[0]]
    destination = goals[nodes[-1]]
    points = [source["xy"], (nodes[0][0] * aid.STEP, nodes[0][1] * aid.STEP)]
    direction = None
    for before, after in zip(nodes, nodes[1:]):
        delta = tuple(after[i] - before[i] for i in range(3))
        xy = (before[0] * aid.STEP, before[1] * aid.STEP)
        if delta[2]:
            points.append(xy)
            rt.path(net, before[2], points, width)
            rt.via(net, xy)
            points = [xy]
            direction = None
        elif delta != direction:
            points.append(xy)
            direction = delta
    points.extend([(found[0] * aid.STEP, found[1] * aid.STEP), destination["xy"]])
    rt.path(net, found[2], points, width)
    return dict(
        connected=True,
        visited=len(visited),
        source=source,
        target=destination,
        native_anchor_states=[len(x) for x in anchors],
    )


def main(
    step=0.1,
    budget=500000,
    prefix=None,
    output_path=None,
    route_pour_cuts=False,
    preserve_force_pours=False,
):
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    aid.STEP = step
    aid.CLEARANCE = 0.20
    rt = Router(tree)
    rt.inner_escape = True
    rt.allow_pour_clearance = route_pour_cuts
    graph_path = ROOT / "generated/open-components.json"
    binding_path = ROOT / "generated/native-open-components-binding.json"
    binding = json.loads(binding_path.read_text())
    assert binding["source_pcb_sha256"] == hashlib.sha256(before).hexdigest(), (
        "Source changed since native graph export"
    )
    assert binding["graph_sha256"] == hashlib.sha256(graph_path.read_bytes()).hexdigest(), (
        "Native graph changed after binding"
    )
    rows = json.loads(graph_path.read_text())
    if preserve_force_pours:
        from .force_guard import ForceGuard

        assert route_pour_cuts, "Use actual filled force polygons with low-current pour withdrawal"
        filled = ROOT / f"generated/filled-{binding['native_label']}.kicad_pcb"
        assert hashlib.sha256(filled.read_bytes()).hexdigest() == binding["filled_pcb_sha256"]
        rt.force_guard = ForceGuard(read_sexpr(filled.read_text()), rt, step)
    net_names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    actual_objects = {
        str(first(n, "uuid")[1]): net_names[str(first(n, "net")[1])]
        for kind in ("segment", "via")
        for n in children(tree, kind)
        if children(n, "uuid")
    }
    results = []
    for row in rows:
        if prefix is not None and not row["net"].startswith(prefix):
            continue
        # Refilled scratch copies may assign an orphan track/via to touching
        # copper. Only anchors retaining this declared net in editable source
        # are routing terminals; actual source pads are checked independently.
        rejected = 0
        groups = []
        for group in row["components"]:
            valid = []
            for point in group:
                if point["kind"] == "PAD":
                    present = any(
                        p["net"] == row["net"]
                        and math.dist(p["xy"], point["xy"]) < 1e-5
                        and set(point["layers"]) == set(p["layers"])
                        for p in rt.pads
                    )
                else:
                    present = actual_objects.get(point["uuid"]) == row["net"]
                if present:
                    valid.append(point)
                else:
                    rejected += 1
            groups.append(valid)
        row = dict(row, components=groups)
        rt.cached = {}
        result = dict(net=row["net"], **connect_components(rt, row, budget=budget))
        result["rejected_non_source_anchors"] = rejected
        results.append(result)
        print(result["net"], result["connected"], result.get("reason"), result.get("visited"), flush=True)
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:components:{index}:{sexpr(node)}"))),
                ]
            )
    destination = path if output_path is None else Path(output_path)
    if output_path is not None:
        assert destination.resolve().is_relative_to((ROOT / "generated").resolve()), (
            "Candidate must stay inside owned generated directory"
        )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(before).hexdigest(), (
        "Source changed during routing"
    )
    destination.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/component-routes.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                written_path=str(destination),
                routing_grid_mm=step,
                per_pair_node_budget=budget,
                native_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
                native_graph_binding_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
                actual_pour_cuts_requested=route_pour_cuts,
                actual_filled_force_pours_guarded=preserve_force_pours,
                force_pour_snapshot_sha256=(binding["filled_pcb_sha256"] if preserve_force_pours else None),
                filled_current_paths_require_new_extraction=True,
                results=results,
                native_verified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=float, default=0.1)
    parser.add_argument("--budget", type=int, default=500000)
    parser.add_argument("--prefix")
    parser.add_argument("--output-path")
    parser.add_argument("--route-pour-cuts", action="store_true")
    parser.add_argument("--preserve-force-pours", action="store_true")
    args = parser.parse_args()
    main(
        args.step,
        args.budget,
        args.prefix,
        args.output_path,
        args.route_pour_cuts,
        args.preserve_force_pours,
    )
