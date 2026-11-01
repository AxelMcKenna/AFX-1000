"""Read-only KiCad polygon export for the actual FOUR E19 copper layers."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")


def points(chain):
    return [[chain.CPoint(i).x / 1e6, chain.CPoint(i).y / 1e6] for i in range(chain.PointCount())]


def export(source):
    board = pcbnew.LoadBoard(str(source))
    rows = []
    actual = [board.GetLayerName(layer) for layer in board.GetEnabledLayers().CuStack()]
    assert actual == list(LAYERS), actual
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNetname():
                continue
            layers = {}
            for name in LAYERS:
                layer = board.GetLayerID(name)
                if not pad.IsOnLayer(layer):
                    continue
                poly = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_INSIDE)
                poly.Simplify()
                layers[name] = [
                    dict(
                        outer=points(poly.COutline(i)),
                        holes=[points(poly.CHole(i, h)) for h in range(poly.HoleCount(i))],
                    )
                    for i in range(poly.OutlineCount())
                ]
            if layers:
                drill, pos = pad.GetDrillSize(), pad.GetPosition()
                rows.append(
                    dict(
                        ref=fp.GetReference(),
                        pin=pad.GetNumber(),
                        net=pad.GetNetname().lstrip("/"),
                        uuid=pad.m_Uuid.AsString(),
                        layers=layers,
                        position_mm=[pos.x / 1e6, pos.y / 1e6],
                        drill_mm=[drill.x / 1e6, drill.y / 1e6],
                        size_mm=[pad.GetSize().x / 1e6, pad.GetSize().y / 1e6],
                    )
                )
    return dict(
        source_pcb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        actual_layers=actual,
        native_version=pcbnew.GetBuildVersion(),
        native_curve_error_mm=0.001,
        native_curve_error_inside=True,
        pads=rows,
        source_modified=False,
        physical_qualified=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = export(args.source)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Native actual four-layer pads", len(result["pads"]))
