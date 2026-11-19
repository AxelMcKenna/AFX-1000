"""Verify an additive signal-board route with its new local ground pour using KiCad Python."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

from hardware.electronics.common.sexpr import first, read_sexpr
from hardware.fabrication.verify_power_surface_refill import (
    filled_polygons,
    pad_groups,
    same_filled_area,
)


def copper(item, layer):
    polygon = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(polygon, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE)
    return polygon


def verify(parent, project):
    review = json.loads((project / "native-review.json").read_text())
    reference = json.loads((project / "reference-review.json").read_text())
    path = project / "signal_main.kicad_pcb"
    parent_path = parent / path.name
    raw = path.read_bytes()
    original = parent_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == review["pcb_sha256"] == reference["board_sha256"]
    assert hashlib.sha256(original).hexdigest() == review["parent_sha256"]
    prefix = original.rstrip()[:-1]
    assert raw.startswith(prefix)
    added = read_sexpr("(" + raw[len(prefix):].decode())
    expected = {reference["ground_zone_uuid"]: "zone"}
    expected.update({uid: "segment" for uid in reference["segment_uuids"]})
    assert len(added) == len(expected)
    assert {first(node, "uuid")[1]: node[0] for node in added} == expected

    before = pcbnew.LoadBoard(str(parent_path.resolve()))
    after = pcbnew.LoadBoard(str(path.resolve()))
    count, groups = pad_groups(before)
    pads = {
        footprint.GetReference() + ":" + pad.GetNumber(): pad
        for footprint in after.GetFootprints() for pad in footprint.Pads()
    }
    merged = [
        next(group for group in groups if pads[name].m_Uuid.AsString() in group)
        for name in review["only_merged_pads"]
    ]
    assert len(merged) == len(set(merged))
    result = count - len(merged) + 1, groups.difference(merged) | {frozenset.union(*merged)}
    assert count == review["baseline_opens"] and result[0] == review["native_opens"]
    assert pad_groups(after) == result

    key = (reference["ground_zone_uuid"], reference["return_layer"])
    saved_parent, saved_after = filled_polygons(before), filled_polygons(after)
    assert saved_after.keys() == saved_parent.keys() | {key}
    assert all(saved_after[k].Format() == p.Format() for k, p in saved_parent.items())
    for board in (before, after):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    assert pad_groups(before) == (count, groups) and pad_groups(after) == result
    old_fields, new_fields = filled_polygons(before), filled_polygons(after)
    assert all(same_filled_area(p, new_fields[k]) for k, p in old_fields.items())
    field = new_fields[key]
    assert field.OutlineCount() == 1 and same_filled_area(saved_after[key], field)

    tracks = {item.m_Uuid.AsString(): item for item in after.GetTracks()}
    for uid in reference["segment_uuids"]:
        track = tracks[uid]
        assert track.GetNetname() == reference["routed_net"]
        assert after.GetLayerName(track.GetLayer()) == reference["route_layer"]
        uncovered = copper(track, track.GetLayer())
        uncovered.BooleanSubtract(field)
        assert uncovered.Area() == 0
    zone = next(z for z in after.Zones() if z.m_Uuid.AsString() == key[0])
    ground = pads[reference["ground_anchor_pad"]]
    ground_group = {o.m_Uuid.AsString() for o in after.GetConnectivity().GetConnectedItems(ground)}
    assert zone.GetNetname() == ground.GetNetname() == "LINK_AGND"
    for uid in review["existing_ground_vias"]:
        via = tracks[uid]
        assert uid in ground_group and via.GetClass() == "PCB_VIA"
        overlap = copper(via, after.GetLayerID(key[1]))
        overlap.BooleanIntersection(field)
        assert overlap.Area() > 0.01 * 1e12
    return result[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(f"Verified local reference extension with {verify(args.parent, args.project)} open connections")
