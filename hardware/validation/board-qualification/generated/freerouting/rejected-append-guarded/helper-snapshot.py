"""Try router additions on an immutable source while retaining ALL old copper.

This is an isolated development experiment. Native DRC and actual filled-copper
comparison remain mandatory. Conflicting additions may be removed; original
tracks, vias, parts and zones may never be removed by this helper.
"""

import argparse
import json
import shutil
import uuid
from pathlib import Path

from .freerouting_bridge import copper, parts, sha


def key(item, board, pcbnew):
    row = (
        type(item).__name__,
        item.GetNetname(),
        int(item.GetLayer()),
        item.GetStart().x,
        item.GetStart().y,
        item.GetEnd().x,
        item.GetEnd().y,
    )
    if isinstance(item, pcbnew.PCB_VIA):
        layers = (
            [pcbnew.F_Cu]
            + [getattr(pcbnew, "In%d_Cu" % i) for i in range(1, board.GetCopperLayerCount() - 1)]
            + [pcbnew.B_Cu]
        )
        return row + (tuple(item.GetWidth(layer) for layer in layers), item.GetDrillValue())
    assert isinstance(item, pcbnew.PCB_TRACK) and not isinstance(item, pcbnew.PCB_ARC)
    return row + (item.GetWidth(),)


def append(source, routed, workspace):
    import pcbnew

    assert not workspace.exists(), "Use a fresh workspace"
    source_hash, routed_hash = sha(source), sha(routed)
    original, candidate = pcbnew.LoadBoard(str(source)), pcbnew.LoadBoard(str(routed))
    assert parts(original) == parts(candidate), "Candidate component identities/poses differ"
    before = copper(original, pcbnew)
    missing = copper(candidate, pcbnew) - before
    added = []
    for item in list(candidate.GetTracks()):
        row = key(item, candidate, pcbnew)
        if missing[row] <= 0:
            continue
        missing[row] -= 1
        clone = item.Duplicate()
        clone.SetNet(original.FindNet(item.GetNetname()))
        uid = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                "afx-append:" + source_hash + routed_hash + json.dumps(row) + str(len(added)),
            )
        )
        clone.SetUuid(pcbnew.KIID(uid))
        clone.SetLocked(False)
        original.Add(clone)
        added.append(dict(uuid=uid, net=item.GetNetname(), candidate_uuid=item.m_Uuid.AsString()))
    assert not before - copper(original, pcbnew), "Original copper changed"
    assert source_hash == sha(source) and routed_hash == sha(routed), "Input changed during capture"
    shutil.copytree(source.parent, workspace)
    pcbnew.SaveBoard(str(workspace / source.name), original)
    receipt = dict(
        source_pcb_sha256=source_hash,
        routed_pcb_sha256=routed_hash,
        original_track_via_count=sum(before.values()),
        added_count=len(added),
        added=added,
        original_copper_preserved=True,
        output_pcb_sha256=sha(workspace / source.name),
        helper_sha256=sha(Path(__file__)),
        native_checked=False,
        filled_force_copper_preserved=False,
        candidate_accepted=False,
        fabrication_released=False,
    )
    (workspace / "append-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Original objects retained:", sum(before.values()), "additions:", len(added))


def remove_conflicting_additions(workspace, drc):
    import pcbnew

    receipt = json.loads((workspace / "append-receipt.json").read_text())
    added = {r["uuid"] for r in receipt["added"]}
    errors = [v for v in json.loads(drc.read_text())["violations"] if v["severity"] == "error"]
    removable, unhandled = set(), []
    for error in errors:
        ids = {item["uuid"] for item in error["items"]} & added
        if not ids:
            unhandled.append(error)
        removable.update(ids)
    board_path = next(workspace.glob("*.kicad_pcb"))
    board = pcbnew.LoadBoard(str(board_path))
    for item in list(board.GetTracks()):
        if item.m_Uuid.AsString() in removable:
            board.Remove(item)
    pcbnew.SaveBoard(str(board_path), board)
    report = dict(
        drc_sha256=sha(drc),
        removed_added_ids=sorted(removable),
        unhandled_errors=unhandled,
        output_pcb_sha256=sha(board_path),
        original_items_authorized_for_removal=0,
        candidate_accepted=False,
    )
    (workspace / ("filter-" + sha(drc)[:12] + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print("Removed only added items:", len(removable), "unhandled errors:", len(unhandled))
    return not unhandled


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    add = sub.add_parser("append")
    add.add_argument("source", type=Path)
    add.add_argument("routed", type=Path)
    add.add_argument("workspace", type=Path)
    filt = sub.add_parser("filter")
    filt.add_argument("workspace", type=Path)
    filt.add_argument("drc", type=Path)
    args = parser.parse_args()
    if args.operation == "append":
        append(args.source.resolve(), args.routed.resolve(), args.workspace.resolve())
    else:
        raise SystemExit(
            0 if remove_conflicting_additions(args.workspace.resolve(), args.drc.resolve()) else 1
        )
