"""Read-only Linux capture with explicit retention of known native warnings."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

if sys.platform == "linux":
    import pcbnew

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "hardware/qualification/boards/thin_aux_boards/generated/NF/native-complete"
OUTPUT = REPO / "hardware/fabrication/staging/nf-routing-inputs"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygons(poly):
    def points(chain):
        return [[chain.CPoint(i).x / 1e6, chain.CPoint(i).y / 1e6] for i in range(chain.PointCount())]

    return [dict(outer=points(poly.COutline(i)), holes=[points(poly.CHole(i, j)) for j in range(poly.HoleCount(i))])
            for i in range(poly.OutlineCount())]


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--label", default=OUTPUT.name)
    parser.add_argument("--expected-opens", type=int, default=204)
    parser.add_argument("--expected-footprints", type=int, default=267)
    parser.add_argument("--board-name", default="negative_startup_physical")
    parser.add_argument("--allow-via-dangling", action="store_true")
    parser.add_argument("--allow-track-dangling", action="store_true")
    parser.add_argument("--allow-copper-sliver", action="store_true")
    args = parser.parse_args()
    assert args.source.resolve().is_relative_to(REPO)
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    output = OUTPUT.parent / args.label
    assert not output.exists()
    assert args.board_name and all(c.isalnum() or c == "_" for c in args.board_name)
    pcb, drc = args.source / (args.board_name+".kicad_pcb"), args.source / "drc.json"
    hashes = {str(p): sha(p) for p in (pcb, drc, Path(__file__))}
    report = json.loads(drc.read_text())
    assert not report["schematic_parity"]
    allowed_warnings = set()
    if args.allow_via_dangling:
        allowed_warnings.add("via_dangling")
    if args.allow_track_dangling:
        allowed_warnings.add("track_dangling")
    if args.allow_copper_sliver:
        allowed_warnings.add("copper_sliver")
    assert all(v["type"] in allowed_warnings and v["severity"] == "warning" for v in report["violations"])
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    assert connection.GetUnconnectedCount(False) == len(report["unconnected_items"]) == args.expected_opens
    assert len(list(board.GetFootprints())) == args.expected_footprints
    layers = ("F.Cu",*[f"In{i}.Cu" for i in range(1,board.GetCopperLayerCount()-1)],"B.Cu")
    items = [p for f in board.GetFootprints() for p in f.Pads()] + list(board.GetTracks())
    by_id = {p.m_Uuid.AsString(): p for p in items}
    assert len(by_id) == len(items)
    open_ids = {i["uuid"] for row in report["unconnected_items"] for i in row["items"]}
    open_nets = {by_id[uid].GetNetname() for uid in open_ids}
    groups, membership = {}, {}
    for uid, item in by_id.items():
        if item.GetNetname() not in open_nets or uid in membership:
            continue
        members = {uid} | {p.m_Uuid.AsString() for p in connection.GetConnectedItems(item)}
        members &= by_id.keys()
        assert all(by_id[key].GetNetname() == item.GetNetname() for key in members)
        key = min(members)
        groups[key] = sorted(members)
        membership.update({member: key for member in members})
    rows = []
    for uid, item in by_id.items():
        pos = item.GetPosition()
        row = dict(uuid=uid, net=item.GetNetname(), kind=item.GetClass(),
                   position_mm=[pos.x / 1e6, pos.y / 1e6], layers={}, group=membership.get(uid))
        for name in layers:
            layer = board.GetLayerID(name)
            if not item.IsOnLayer(layer):
                continue
            poly = pcbnew.SHAPE_POLY_SET()
            item.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(.001), pcbnew.ERROR_OUTSIDE)
            poly.Simplify()
            row["layers"][name] = polygons(poly)
        if row["kind"] == "PAD":
            row.update(ref=item.GetParentFootprint().GetReference(), pin=item.GetNumber(),
                       drill_mm=[item.GetDrillSize().x / 1e6, item.GetDrillSize().y / 1e6],
                       orientation_degrees=item.GetOrientation().AsDegrees(),
                       npth=int(item.GetAttribute()) == int(pcbnew.PAD_ATTRIB_NPTH))
        elif row["kind"] == "PCB_TRACK":
            end = item.GetEnd()
            row["end_mm"] = [end.x / 1e6, end.y / 1e6]
            row["width_mm"] = item.GetWidth() / 1e6
        rows.append(row)
    zones = []
    for zone in board.Zones():
        for name in layers:
            layer = board.GetLayerID(name)
            if not zone.IsOnLayer(layer):
                continue
            keepout = zone.GetIsRuleArea()
            poly = zone.Outline() if keepout else zone.GetFilledPolysList(layer)
            zones.append(dict(uuid=zone.m_Uuid.AsString(), net=zone.GetNetname(), layer=name,
                              keepout=keepout, prohibit_tracks=bool(zone.GetDoNotAllowTracks()) if keepout else False,
                              prohibit_vias=bool(zone.GetDoNotAllowVias()) if keepout else False,
                              polygons=polygons(poly)))
    outline = pcbnew.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    output.mkdir()
    result = dict(source_sha256=hashes, native_version=pcbnew.GetBuildVersion(),
                  native_uncapped_opens=args.expected_opens, objects=rows, zones=zones, groups=groups,
                  outline=polygons(outline), copper_layers=layers, obstacle_polygons_error="outside0.001mm",
                  retained_native_findings=report["violations"],
                  all_original_geometry_unchanged=True, physical_qualified=False, fabrication_released=False)
    (output / "capture.json").write_text(json.dumps(result, separators=(",", ":")) + "\n")
    assert all(sha(Path(p)) == digest for p, digest in hashes.items())
    print("Captured", len(rows), "objects,", len(groups), "open-net native clusters and", len(zones), "zone/layer shapes")


if __name__ == "__main__":
    run()
