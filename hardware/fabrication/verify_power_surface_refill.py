"""Check the native pad partition and filled copper after refilling an additive power layout."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew


def pad_groups(board):
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    connectivity.RecalculateRatsnest()
    groups = set()
    seen = set()
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            key = pad.m_Uuid.AsString()
            if key in seen or not pad.GetNetCode() or not pad.GetNumber():
                continue
            members = {key}
            members.update(
                item.m_Uuid.AsString()
                for item in connectivity.GetConnectedItems(pad)
                if item.GetClass() == "PAD" and item.GetNumber() and item.GetNetCode()
            )
            groups.add(frozenset(members))
            seen.update(members)
    return connectivity.GetUnconnectedCount(False), groups


def filled_polygons(board):
    return {
        (zone.m_Uuid.AsString(), board.GetLayerName(layer)):
            pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(layer))
        for zone in board.Zones() if not zone.GetIsRuleArea()
        for layer in zone.GetLayerSet().Seq()
    }


def verify(project, parent):
    path = project / "power_protection.kicad_pcb"
    expected = json.loads((project / "connectivity.json").read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected["candidate_sha256"]:
        raise ValueError("Board differs from the connectivity report")
    parent_path = parent / path.name
    parent_digest = hashlib.sha256(parent_path.read_bytes()).hexdigest()
    retention = json.loads((project / "retention.json").read_text())
    if (parent_digest, digest) != (retention["parent_sha256"], retention["candidate_sha256"]):
        raise ValueError("Board pair differs from the retained-objects report")
    board = pcbnew.LoadBoard(str(path.resolve()))
    opens, groups = pad_groups(board)
    before = filled_polygons(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    after = filled_polygons(board)
    if (opens, groups) != pad_groups(board) or opens != expected["native_opens"]:
        raise ValueError("Refill changed the native open count or physical pad partition")
    if before.keys() != after.keys():
        raise ValueError("Refill changed the zone or layer inventory")
    parent_board = pcbnew.LoadBoard(str(parent_path.resolve()))
    parent_saved = filled_polygons(parent_board)
    pcbnew.ZONE_FILLER(parent_board).Fill(parent_board.Zones())
    parent_refilled = filled_polygons(parent_board)
    if before.keys() != parent_saved.keys() or after.keys() != parent_refilled.keys():
        raise ValueError("Parent and candidate have different zone inventories")

    refill_deltas = []
    for key, polygon in before.items():
        if polygon.Format() != parent_saved[key].Format():
            raise ValueError(f"Saved candidate differs from parent zone {key}")
        if after[key].Format() != parent_refilled[key].Format():
            raise ValueError(f"Refilled candidate differs from refilled parent zone {key}")
        if polygon.Format() != after[key].Format():
            polygon.BooleanXor(after[key])
            refill_deltas.append(dict(zone=key[0], layer=key[1], area_mm2=polygon.Area() / 1e12))
    return dict(board_sha256=digest, kicad_version=pcbnew.GetBuildVersion(),
                parent_sha256=parent_digest,
                native_opens_before_and_after=opens, connected_pad_groups=len(groups),
                zone_layer_pairs_checked=len(after), saved_and_refilled_fields_match_parent=True,
                inherited_refill_differences=refill_deltas)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("parent", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.project, args.parent), indent=2))
