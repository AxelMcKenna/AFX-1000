"""Capture unchanged audio copper and native islands in isolated Linux KiCad."""

import json
import sys
from pathlib import Path

from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha


def capture(source, output, expected_opens, nets, applied):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication.capture_board import polygons

    assert output.is_dir() and applied.is_file()
    dest = output / "native-inputs.json"
    assert not dest.exists()
    inputs = [source / p for p in ("audio_core.kicad_pcb", "routing-handoff.json", "drc.json")]
    before = relative_hashes([*inputs, applied, Path(__file__)])
    report = json.loads((source / "drc.json").read_text())
    assert report["violations"] == report["ignored_checks"] == []
    assert report["schematic_parity"] == [dict(description="Missing footprint U201 (ES9292QPRO)", items=[], severity="warning", type="missing_footprint")]
    board = pcbnew.LoadBoard(str(source / "audio_core.kicad_pcb"))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    assert conn.GetUnconnectedCount(False) == len(report["unconnected_items"]) == expected_opens
    items = [p for f in board.GetFootprints() for p in f.Pads()] + list(board.GetTracks())
    rows, groups, seen = [], {}, set()
    layers = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")
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
                  groups=groups, zones=zones, outline=polygons(outline), copper_layers=layers,
                  native_uncapped_opens=expected_opens, fabrication_released=False)
    dest.write_text(json.dumps(result, separators=(",", ":"))+"\n")
    assert sha(applied) == before[str(applied.relative_to(Path(__file__).resolve().parents[2]))]
    print("Captured", len(rows), "native objects and", len(groups), "supply islands")
