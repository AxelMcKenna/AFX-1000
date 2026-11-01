"""Choose insertion cuts relative to real upstream copper, never fictitious pads."""

import hashlib
import json
import math
from collections import deque
from pathlib import Path

from .schmitt_backbone_cut_plan import Flow

ROOT = Path(__file__).resolve().parent


def insertion_plan(row, target, upstream):
    nodes = row["nodes"]
    ids = sorted(nodes)
    idx = {u: i for i, u in enumerate(ids)}
    n = len(ids)
    s = 2 * n
    t = s + 1
    f = Flow(t + 1)
    inf = 10**10
    roots = {u for u, r in nodes.items() if r["kind"] == "PAD" and r["role"] != "input"}
    receivers = {u for u, r in nodes.items() if r["kind"] == "PAD" and r["role"] == "input"}
    assert roots and receivers and upstream and upstream <= set(nodes) and not upstream & receivers
    assert all(nodes[u]["kind"] == "PCB_VIA" for u in upstream), (
        "Insertion anchors must be existing real barrels"
    )
    for uid, r in nodes.items():
        i = idx[uid]
        points = [r["position_mm"]] + ([r["end_mm"]] if r["kind"] == "PCB_TRACK" else [])
        cost = (
            100000 + round(min(math.dist(target, p) for p in points) * 100)
            if r["kind"] == "PCB_TRACK"
            else inf
        )
        f.edge(2 * i, 2 * i + 1, cost)
        if uid in roots | upstream:
            f.edge(s, 2 * i, inf)
        if uid in receivers:
            f.edge(2 * i + 1, t, inf)
    for a, b in row["edges"]:
        f.edge(2 * idx[a] + 1, 2 * idx[b], inf)
        f.edge(2 * idx[b] + 1, 2 * idx[a], inf)
    total, reachable = f.solve(s, t)
    assert 0 < total < inf
    cut = {u for u, i in idx.items() if 2 * i in reachable and 2 * i + 1 not in reachable}
    adj = {u: set() for u in nodes}
    for a, b in row["edges"]:
        adj[a].add(b)
        adj[b].add(a)
    down = set(receivers)
    q = deque(receivers)
    while q:
        for v in adj[q.popleft()] - cut - down:
            down.add(v)
            q.append(v)
    assert not down & (roots | upstream)
    assert all(nodes[u]["kind"] == "PCB_TRACK" for u in cut)
    return dict(
        cut_track_uuids=sorted(cut),
        buffered_item_uuids=sorted(down),
        source_terminal_uuids=sorted(roots),
        receiver_terminal_uuids=sorted(receivers),
        real_upstream_copper_anchor_uuids=sorted(upstream),
        target_native_mm=target,
        upstream_copper_is_not_assumed_connected_to_real_source=True,
        required_complete_actual_source_connectivity_still_unproven=True,
    )


def main():
    p = ROOT / "generated/schmitt-cone-proposal/native-backbone-direct-graph.json"
    g = json.loads(p.read_text())
    row = g["rows"]["V5_REG_OV_OK"]
    receivers = {u for u, r in row["nodes"].items() if r["kind"] == "PAD" and r["role"] == "input"}
    component = next(set(c) for c in row["components"] if receivers <= set(c))
    vias = [u for u in component if row["nodes"][u]["kind"] == "PCB_VIA"]
    anchor = max(vias, key=lambda u: row["nodes"][u]["position_mm"][0])
    result = insertion_plan(row, [119, 108], {anchor})
    out = ROOT / "generated/schmitt-cone-proposal/v5-insertion-cut.json"
    out.write_text(
        json.dumps(
            dict(
                graph_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                net="V5_REG_OV_OK",
                plan=result,
                anchor_native_geometry=row["nodes"][anchor],
                cut_native_geometry=[row["nodes"][u] for u in result["cut_track_uuids"]],
                no_PCB_or_schematic_modified=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Real anchor",
        row["nodes"][anchor],
        "cut",
        len(result["cut_track_uuids"]),
        "buffered objects",
        len(result["buffered_item_uuids"]),
        [row["nodes"][u] for u in result["cut_track_uuids"]],
    )


if __name__ == "__main__":
    main()
