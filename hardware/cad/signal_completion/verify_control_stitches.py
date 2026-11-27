"""Check that each transition's return via contacts the poured island beneath each leg."""
import hashlib
import json
from pathlib import Path
import sys

import pcbnew

from hardware.cad.signal_completion.verify_output_returns import copper, expanded_pad

REFERENCE = {"F.Cu": "In1.Cu", "In2.Cu": "In1.Cu", "In3.Cu": "In4.Cu",
             "In5.Cu": "In6.Cu", "B.Cu": "In6.Cu"}


def ground_islands(board, layer):
    ground = pcbnew.SHAPE_POLY_SET()
    for zone in board.Zones():
        if zone.GetNetname() == "LINK_AGND" and zone.IsOnLayer(layer):
            field = pcbnew.SHAPE_POLY_SET(zone.GetFilledPolysList(layer))
            field.Unfracture()
            ground.BooleanAdd(field)
    ground.Simplify()
    for index in range(ground.OutlineCount()):
        island = pcbnew.SHAPE_POLY_SET()
        island.AddOutline(ground.Outline(index))
        for hole in range(ground.HoleCount(index)):
            island.AddHole(ground.Hole(index, hole))
        yield island


def check(board_path, reports):
    board = pcbnew.LoadBoard(str(board_path))
    anchor = next(pad for pad in board.GetPads()
                  if pad.GetParentFootprint().GetReference() == "D_U1001" and pad.GetNumber() == "20")
    assert anchor.GetNetname() == "LINK_AGND"
    connected = {item.m_Uuid.AsString() for item in board.GetConnectivity().GetConnectedItems(anchor)}
    items = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    fields = {name: list(ground_islands(board, board.GetLayerID(name))) for name in set(REFERENCE.values())}
    legs = []
    for report in reports:
        route = json.loads(report.read_text())["routes"]
        stitches = route["stitch_ids"]
        assert len(stitches) == len(route["segment_ids"]) - 1 and {uid for uid in stitches if uid} <= connected
        previous_island = None
        for leg_index, (face, segments) in enumerate(zip(route["layers"], route["segment_ids"], strict=True)):
            ref = REFERENCE[face]
            layer = board.GetLayerID(ref)
            projection = pcbnew.SHAPE_POLY_SET()
            for uid in segments:
                track = items[uid]
                assert track.GetNetname() == route["net"] and track.GetLayer() == board.GetLayerID(face)
                projection.BooleanAdd(copper(track, track.GetLayer()))
            for contact in [*board.GetPads(), *(item for item in items.values() if item.GetClass() == "PCB_VIA")]:
                if contact.GetNetname() != route["net"]:
                    continue
                if contact.GetClass() == "PCB_VIA" or contact.GetDrillSize().x > 0:
                    projection.BooleanSubtract(expanded_pad(contact, layer, .23))
            ends = stitches[max(0, leg_index - 1):leg_index + 1]
            shared = leg_index > 0 and stitches[leg_index - 1] is None
            if shared and REFERENCE[route["layers"][leg_index - 1]] != ref:
                raise ValueError("A reference-layer change requires a connected return stitch")
            for island_number, island in enumerate(fields[ref]):
                if shared and previous_island != island_number:
                    continue
                gap = pcbnew.SHAPE_POLY_SET(projection)
                gap.BooleanSubtract(island)
                if gap.Area() > 1e6:
                    continue
                contacts = []
                for uid in filter(None, ends):
                    contact = copper(items[uid], layer)
                    contact.BooleanIntersection(island)
                    contacts.append(contact.Area() / 1e12)
                if all(area > .01 for area in contacts):
                    previous_island = island_number
                    legs.append(dict(net=route["net"], signal_layer=face, reference_layer=ref,
                                     uncovered_mm2=gap.Area()/1e12, stitch_ids=list(filter(None, ends)), contact_mm2=contacts))
                    break
            else:
                raise ValueError(f"{route['net']} leg {leg_index} lacks a common return island")
    return dict(board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(), legs=legs)


if __name__ == "__main__":
    pcb, *inputs = map(Path, sys.argv[1:])
    print(json.dumps(check(pcb, inputs), indent=2))
