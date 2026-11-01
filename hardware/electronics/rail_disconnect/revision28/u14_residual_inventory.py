"""Actual UUID-based native residual components; never collapse co-located pads."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pcbnew


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(source, filled, drc, output):
    source, filled, drc, output = map(Path, (source, filled, drc, output))
    inputs = {str(p): sha(p) for p in (source, filled, drc, Path(__file__))}
    board = pcbnew.LoadBoard(str(filled))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    raw = json.loads(drc.read_text())
    names = {
        re.search(r"\[/([^]]+)\]", r["items"][0]["description"]).group(1) for r in raw["unconnected_items"]
    }
    items = [t for t in board.GetTracks() if t.GetNetname().lstrip("/") in names]
    items += [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname().lstrip("/") in names]
    by_id = {i.m_Uuid.AsString(): i for i in items}
    assert len(by_id) == len(items)
    parent = {uid: uid for uid in by_id}

    def root(uid):
        while parent[uid] != uid:
            parent[uid] = parent[parent[uid]]
            uid = parent[uid]
        return uid

    for uid, item in by_id.items():
        for neighbor in connection.GetConnectedItems(item):
            target = neighbor.m_Uuid.AsString()
            assert item.GetNetname() == neighbor.GetNetname()
            if target in parent:
                parent[root(target)] = root(uid)
    groups = {}
    for uid, item in by_id.items():
        net = item.GetNetname().lstrip("/")
        row = dict(
            uuid=uid,
            net=net,
            kind=item.GetClass(),
            layers=[
                i
                for i, n in enumerate(("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"))
                if item.IsOnLayer(board.GetLayerID(n))
            ],
        )
        point = item.GetPosition()
        row["position_mm"] = [pcbnew.ToMM(point.x) - 100, pcbnew.ToMM(point.y) - 100]
        if row["kind"] == "PAD":
            row.update(ref=item.GetParentFootprint().GetReference(), pin=item.GetNumber())
        if row["kind"] == "PCB_TRACK":
            row["end_mm"] = [pcbnew.ToMM(item.GetEnd().x) - 100, pcbnew.ToMM(item.GetEnd().y) - 100]
        groups.setdefault((net, root(uid)), []).append(row)
    result = {}
    for net in sorted(names):
        comps = [g for (n, _), g in groups.items() if n == net]
        result[net] = dict(
            reported_opens=sum(
                re.search(r"\[/([^]]+)\]", r["items"][0]["description"]).group(1) == net
                for r in raw["unconnected_items"]
            ),
            actual_component_count=len(comps),
            components=comps,
            component_logical_pads=[
                sorted({r["ref"] + "." + r["pin"] for r in g if r["kind"] == "PAD"}) for g in comps
            ],
            component_kind_counts=[dict(Counter(r["kind"] for r in g)) for g in comps],
        )
    report = dict(
        source_sha256=inputs,
        native_version=pcbnew.GetBuildVersion(),
        source_residual_count=len(raw["unconnected_items"]),
        actual_residual_net_count=len(names),
        inventory=result,
        co_located_pad_identities_retained=True,
        native_not_physical_qualification=True,
    )
    assert all(sha(Path(p)) == v for p, v in inputs.items())
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                n: dict(
                    opens=r["reported_opens"],
                    components=r["actual_component_count"],
                    pads=r["component_logical_pads"],
                )
                for n, r in result.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("source", "filled", "drc", "output"):
        p.add_argument(key)
    main(**vars(p.parse_args()))
