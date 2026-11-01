"""Export native connected-component anchors; run with KiCad's Python."""

import argparse
import json
from pathlib import Path

import pcbnew


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board")
    p.add_argument("drc")
    p.add_argument("output")
    a = p.parse_args()
    board = pcbnew.LoadBoard(a.board)
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    items = (
        list(board.GetTracks()) + [p for f in board.GetFootprints() for p in f.Pads()] + list(board.Zones())
    )
    by_id = {item.m_Uuid.AsString(): item for item in items}

    def anchors(item):
        kind = item.GetClass()
        layers = [
            i
            for i, n in enumerate(("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"))
            if item.IsOnLayer(board.GetLayerID(n))
        ]
        if kind == "PCB_TRACK":
            points = [item.GetStart(), item.GetEnd()]
        elif kind in ("PCB_VIA", "PAD"):
            points = [item.GetPosition()]
        else:
            return []
        return [
            dict(
                xy=[pcbnew.ToMM(point.x) - 100, pcbnew.ToMM(point.y) - 100],
                layers=layers,
                kind=kind,
                uuid=item.m_Uuid.AsString(),
            )
            for point in points
        ]

    result = []
    native = json.loads(Path(a.drc).read_text())
    for row in native["unconnected_items"]:
        ends = []
        net = None
        for entry in row["items"]:
            item = by_id[entry["uuid"]]
            net = item.GetNetname().lstrip("/")
            connected = [item] + list(connection.GetConnectedItems(item))
            points = [anchor for obj in connected for anchor in anchors(obj)]
            unique = {(tuple(p["xy"]), tuple(p["layers"])): p for p in points}
            ends.append(list(unique.values()))
        result.append(dict(net=net, components=ends, reported=row))
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
    print(len(result), "native open pairs exported")


if __name__ == "__main__":
    main()
