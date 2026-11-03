"""Capture every actual audio layer and named-net island for a layout comparison."""

import json
import sys
from pathlib import Path

from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes


def capture(output, input_board, manifest, destination, applied):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication.capture_board import polygons

    assert output.is_dir() and applied.is_file()
    dest = output / destination
    assert not dest.exists()
    before = relative_hashes([input_board, manifest, applied, Path(__file__)])
    board = pcbnew.LoadBoard(str(input_board))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    opens = conn.GetUnconnectedCount(False)
    items = [p for f in board.GetFootprints() for p in f.Pads()] + list(board.GetTracks())
    nets = {p.GetNetname() for p in items if p.GetNetname() not in ("", "AGND") and not p.GetNetname().startswith("unconnected-(")}
    rows, groups, seen = [], {}, set()
    layers = ("F.Cu", *[f"In{i}.Cu" for i in range(1,board.GetCopperLayerCount()-1)], "B.Cu")
    for item in items:
        ident = item.m_Uuid.AsString()
        if item.GetNetname() in nets and ident not in seen:
            connected = list(conn.GetConnectedItems(item))
            assert all(v.GetNetname() == item.GetNetname() for v in connected)
            members = {ident} | {v.m_Uuid.AsString() for v in connected}
            groups[min(members)] = sorted(members)
            seen.update(members)
        row = dict(uuid=ident, net=item.GetNetname(), kind=item.GetClass(),
                   position_mm=[item.GetPosition().x/1e6, item.GetPosition().y/1e6], layers={})
        for name in layers:
            layer = board.GetLayerID(name)
            if item.IsOnLayer(layer):
                poly = pcbnew.SHAPE_POLY_SET()
                item.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(.001), pcbnew.ERROR_OUTSIDE)
                poly.Simplify()
                row["layers"][name] = polygons(poly)
        if row["kind"] == "PAD":
            row.update(ref=item.GetParentFootprint().GetReference(), pin=item.GetNumber(),
                       drill_mm=[item.GetDrillSize().x/1e6, item.GetDrillSize().y/1e6],
                       npth=int(item.GetAttribute()) == int(pcbnew.PAD_ATTRIB_NPTH))
        elif row["kind"] == "PCB_TRACK":
            row.update(end_mm=[item.GetEnd().x/1e6, item.GetEnd().y/1e6], width_mm=item.GetWidth()/1e6)
        rows.append(row)
    known = {r["uuid"] for r in rows}
    assert all(set(members) <= known for members in groups.values())
    zones = []
    for z in board.Zones():
        for name in layers:
            layer = board.GetLayerID(name)
            if z.IsOnLayer(layer):
                keep = z.GetIsRuleArea()
                zones.append(dict(net=z.GetNetname(), layer=name, keepout=keep,
                                  prohibit_tracks=bool(z.GetDoNotAllowTracks()) if keep else False,
                                  prohibit_vias=bool(z.GetDoNotAllowVias()) if keep else False,
                                  polygons=polygons(z.Outline() if keep else z.GetFilledPolysList(layer))))
    outline = pcbnew.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    verify_hashes(before)
    result = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(), objects=rows,
                  groups=groups, zones=zones, outline=polygons(outline), copper_layers=layers, layer_count=board.GetCopperLayerCount(),
                  native_uncapped_opens=opens, draft_only=True, native_clearance_checks_performed=False, fabrication_released=False)
    dest.write_text(json.dumps(result, separators=(",", ":"))+"\n")
    print("Captured", len(rows), "native objects and", len(groups), "native control/rail islands; draft opens", opens)
