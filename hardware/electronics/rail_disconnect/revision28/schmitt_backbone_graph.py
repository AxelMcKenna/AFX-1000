"""Actual KiCad item adjacency and source/receiver terminals for 19 OC backbones."""

import hashlib
import json
from pathlib import Path

import pcbnew

from .schmitt_cone_candidate import GROUPS, ROOT, SOURCE


def main():
    f = SOURCE / "generated/filled-coherent-ground-repair.kicad_pcb"
    parts = json.loads((SOURCE / "components.json").read_text())
    roles = {(c["ref"], p["number"]): p["kind"] for c in parts for p in c["pins"]}
    raw = {n for g in GROUPS for n in g if n}
    b = pcbnew.LoadBoard(str(f))
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    items = [v for v in b.GetTracks() if v.GetNetname().lstrip("/") in raw] + [
        p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname().lstrip("/") in raw
    ]
    by = {v.m_Uuid.AsString(): v for v in items}
    rows = {}
    for net in sorted(raw):
        ns = {uid: v for uid, v in by.items() if v.GetNetname().lstrip("/") == net}
        nodes = {}
        edges = []
        for uid, v in ns.items():
            xy = v.GetPosition()
            r = dict(kind=v.GetClass(), position_mm=[pcbnew.ToMM(xy.x), pcbnew.ToMM(xy.y)])
            if r["kind"] == "PAD":
                r.update(
                    ref=v.GetParentFootprint().GetReference(),
                    pin=v.GetNumber(),
                    role=roles[(v.GetParentFootprint().GetReference(), v.GetNumber())],
                )
            if r["kind"] == "PCB_TRACK":
                r["end_mm"] = [pcbnew.ToMM(v.GetEnd().x), pcbnew.ToMM(v.GetEnd().y)]
            r["layers"] = [
                name
                for name in ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
                if v.IsOnLayer(b.GetLayerID(name))
            ]
            nodes[uid] = r
            # GetConnectedItems is transitive. Native copper-shape collision,
            # rather than its cluster enumeration, establishes each local edge.
            for other in conn.GetConnectedItems(v):
                oid = other.m_Uuid.AsString()
                if oid not in ns or oid == uid or uid >= oid:
                    continue
                if not v.GetBoundingBox().Intersects(other.GetBoundingBox()):
                    continue
                for lname in r["layers"]:
                    layer = b.GetLayerID(lname)
                    if other.IsOnLayer(layer) and v.GetEffectiveShape(layer).Collide(
                        other.GetEffectiveShape(layer), 0
                    ):
                        edges.append([uid, oid])
                        break
        adjacency = {u: set() for u in nodes}
        for one, two in edges:
            adjacency[one].add(two)
            adjacency[two].add(one)
        unseen = set(nodes)
        checked = []
        while unseen:
            start = min(unseen)
            component = {start}
            queue = [start]
            while queue:
                item = queue.pop()
                for neighbor in adjacency[item] - component:
                    component.add(neighbor)
                    queue.append(neighbor)
            native_component = {start} | {
                v.m_Uuid.AsString() for v in conn.GetConnectedItems(ns[start]) if v.m_Uuid.AsString() in ns
            }
            assert component == native_component, (net, len(component), len(native_component))
            checked.append(sorted(component))
            unseen -= component
        rows[net] = dict(
            nodes=nodes,
            edges=sorted(set(map(tuple, edges))),
            direct_shape_components_equal_native_transitive_clusters=True,
            components=checked,
        )
    out = ROOT / "generated/schmitt-cone-proposal/native-backbone-direct-graph.json"
    report = dict(
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [f, SOURCE / "rail_disconnect.kicad_pcb", SOURCE / "components.json", Path(__file__)]
        },
        native_version=pcbnew.GetBuildVersion(),
        rows=rows,
        no_board_mutation=True,
    )
    out.write_text(json.dumps(report, indent=2) + "\n")
    print({n: dict(nodes=len(v["nodes"]), edges=len(v["edges"])) for n, v in rows.items()})


if __name__ == "__main__":
    main()
