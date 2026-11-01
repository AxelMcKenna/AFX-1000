"""Find actual filled-board copper components with no physical pad connection.

Run with KiCad Python. This exports UUIDs; it never mutates a board or filters
DRC. E28cleanup removes those real orphan tracks/vias from editable source.
"""

import argparse
import json
from pathlib import Path

import pcbnew


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board")
    p.add_argument("output")
    a = p.parse_args()
    board = pcbnew.LoadBoard(a.board)
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    seen = set()
    rows = []
    for item in board.GetTracks():
        uid = item.m_Uuid.AsString()
        if uid in seen:
            continue
        group = [item] + list(conn.GetConnectedItems(item))
        ids = {x.m_Uuid.AsString() for x in group}
        seen.update(ids)
        if any(x.GetClass() == "PAD" for x in group):
            continue
        rows.append(
            dict(
                net=item.GetNetname(),
                items=[
                    dict(uuid=x.m_Uuid.AsString(), kind=x.GetClass())
                    for x in group
                    if x.GetClass() in ("PCB_TRACK", "PCB_VIA")
                ],
                reason="Actual native connected component has no physical pad in filled geometry",
            )
        )
    Path(a.output).write_text(json.dumps(rows, indent=2) + "\n")
    print(len(rows), "actual padless copper components")


if __name__ == "__main__":
    main()
