"""Read-only actual native P19 gate components before any targeted repair."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

from hardware.qualification.boards.freerouting_bridge import copper


def main(source, filled, output):
    source, filled, output = Path(source), Path(filled), Path(output)
    original, board = pcbnew.LoadBoard(str(source)), pcbnew.LoadBoard(str(filled))
    assert copper(original, pcbnew) == copper(board, pcbnew)
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    items = [i for i in board.GetTracks() if i.GetNetname().lstrip("/") == "P19_GATE"]
    items += [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname().lstrip("/") == "P19_GATE"]
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
            assert neighbor.GetNetname() == item.GetNetname()
            if target in parent:
                parent[root(target)] = root(uid)
    groups = {}
    for uid, item in by_id.items():
        row = dict(uuid=uid, kind=item.GetClass())
        if item.GetClass() == "PAD":
            row.update(
                ref=item.GetParentFootprint().GetReference(),
                pin=item.GetNumber(),
                position_mm=[item.GetPosition().x / 1e6, item.GetPosition().y / 1e6],
            )
        else:
            row.update(position_mm=[item.GetPosition().x / 1e6, item.GetPosition().y / 1e6])
        groups.setdefault(root(uid), []).append(row)
    rows = []
    for group in groups.values():
        pads = sorted({(r["ref"], r["pin"]) for r in group if r["kind"] == "PAD"})
        rows.append(
            dict(
                logical_pads=[list(p) for p in pads],
                native_objects=group,
                track_via_count=sum(r["kind"] != "PAD" for r in group),
            )
        )
    report = dict(
        source_pcb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        filled_pcb_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(),
        reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        net="P19_GATE",
        native_version=pcbnew.GetBuildVersion(),
        groups=rows,
        source_changed=False,
        physical_qualified=False,
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    print([(r["logical_pads"], r["track_via_count"]) for r in rows])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source")
    p.add_argument("filled")
    p.add_argument("output")
    args = p.parse_args()
    main(args.source, args.filled, args.output)
