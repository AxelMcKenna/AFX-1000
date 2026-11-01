"""Weighted physical-graph vertex cuts preserving every source/pullup terminal."""

import hashlib
import json
import math
import sys
from collections import deque
from pathlib import Path

from .schmitt_cone_candidate import GROUPS, ROOT


class Flow:
    def __init__(self, n):
        self.g = [[] for _ in range(n)]

    def edge(self, u, v, c):
        self.g[u].append([v, c, len(self.g[v])])
        self.g[v].append([u, 0, len(self.g[u]) - 1])

    def solve(self, s, t):
        total = 0
        while True:
            level = [-1] * len(self.g)
            level[s] = 0
            q = deque([s])
            while q:
                u = q.popleft()
                for v, c, _ in self.g[u]:
                    if c and level[v] < 0:
                        level[v] = level[u] + 1
                        q.append(v)
            if level[t] < 0:
                break
            it = [0] * len(self.g)

            def send(u, w):
                if u == t:
                    return w
                while it[u] < len(self.g[u]):
                    e = self.g[u][it[u]]
                    v, c, rev = e
                    if c and level[v] == level[u] + 1:
                        got = send(v, min(w, c))
                        if got:
                            e[1] -= got
                            self.g[v][rev][1] += got
                            return got
                    it[u] += 1
                return 0

            while True:
                sent = send(s, 10**15)
                if not sent:
                    break
                total += sent
        seen = {s}
        q = deque([s])
        while q:
            u = q.popleft()
            for v, c, _ in self.g[u]:
                if c and v not in seen:
                    seen.add(v)
                    q.append(v)
        return total, seen


def partition(row, cut):
    nodes = row["nodes"]
    adj = {u: set() for u in nodes}
    for u, v in row["edges"]:
        adj[u].add(v)
        adj[v].add(u)
    receivers = {u for u, r in nodes.items() if r["kind"] == "PAD" and r["role"] == "input"}
    roots = {u for u, r in nodes.items() if r["kind"] == "PAD" and r["role"] != "input"}
    assert receivers and roots and not cut & (receivers | roots)
    seen = set(receivers)
    q = deque(receivers)
    while q:
        u = q.popleft()
        for v in adj[u] - cut - seen:
            seen.add(v)
            q.append(v)
    assert not seen & roots, (
        "Proposed buffered copper remains attached to a RAW source/pullup/hysteresis terminal"
    )
    assert all(nodes[u]["kind"] == "PCB_TRACK" for u in cut)
    return seen, roots, receivers


def plan(row, target):
    ns = row["nodes"]
    uids = sorted(ns)
    idx = {u: i for i, u in enumerate(uids)}
    n = len(uids)
    s = 2 * n
    t = s + 1
    f = Flow(t + 1)
    inf = 10**10
    for uid, r in ns.items():
        i = idx[uid]
        if r["kind"] == "PCB_TRACK":
            points = [r["position_mm"], r["end_mm"]]
            distance = min(math.dist(target, p) for p in points)
            cost = 100000 + round(distance * 100)
        else:
            cost = inf
        f.edge(2 * i, 2 * i + 1, cost)
        if r["kind"] == "PAD":
            f.edge((2 * i + 1) if r["role"] == "input" else s, t if r["role"] == "input" else 2 * i, inf)
    for a, b in row["edges"]:
        f.edge(2 * idx[a] + 1, 2 * idx[b], inf)
        f.edge(2 * idx[b] + 1, 2 * idx[a], inf)
    total, seen = f.solve(s, t)
    assert total < inf
    cut = {u for u, i in idx.items() if 2 * i in seen and 2 * i + 1 not in seen}
    down, roots, receivers = partition(row, cut)
    return dict(
        cut_track_uuids=sorted(cut),
        buffered_item_uuids=sorted(down),
        source_terminal_uuids=sorted(roots),
        receiver_terminal_uuids=sorted(receivers),
        cost=total,
        target_native_mm=target,
        raw_source_terminals_not_in_buffered_partition=True,
    )


def main():
    sys.setrecursionlimit(10000)
    graph = ROOT / "generated/schmitt-cone-proposal/native-backbone-direct-graph.json"
    g = json.loads(graph.read_text())
    placements = json.loads((ROOT / "generated/schmitt-cone-proposal/near-receiver-search.json").read_text())[
        "rows"
    ]
    old = json.loads(
        (ROOT / "generated/schmitt-all-oc-placement2-work/generated/receiving-change.json").read_text()
    )["poses"]
    poses = {r: [100 + v[0], 100 + v[1]] for r, v in old.items() if r.startswith("U")}
    for p in placements:
        poses[p["ref"]] = [100 + v for v in p["local_mm"]]
    rows = {}
    for i, group in enumerate(GROUPS):
        for net in group:
            if not net:
                continue
            r = plan(g["rows"][net], poses[f"U{36 + i}"])
            rows[net] = r
            print(
                net,
                "cut",
                len(r["cut_track_uuids"]),
                "retag",
                len(r["buffered_item_uuids"]),
                "roots",
                len(r["source_terminal_uuids"]),
                flush=True,
            )
    out = ROOT / "generated/schmitt-cone-proposal/backbone-cut-plan.json"
    out.write_text(
        json.dumps(
            dict(
                source_graph_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                rows=rows,
                actual_boundary_clearance_and_native_recheck_required=True,
                no_board_mutation=True,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
