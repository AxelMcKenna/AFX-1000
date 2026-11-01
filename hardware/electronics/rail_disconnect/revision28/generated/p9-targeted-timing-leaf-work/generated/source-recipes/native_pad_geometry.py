"""Export actual native copper-pad polygons, including compound Q5B lands.

Run with KiCad Python. No pad is replaced by its custom anchor or bounding box.
The original PCB is read only; this is geometry evidence, not qualification.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def points(chain):
    return [(chain.CPoint(i).x / 1e6, chain.CPoint(i).y / 1e6) for i in range(chain.PointCount())]


def export(source):
    board = pcbnew.LoadBoard(str(source))
    rows = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            net = pad.GetNetname().lstrip("/")
            if not net:
                continue
            layers = {}
            for name in LAYERS:
                layer = board.GetLayerID(name)
                if not pad.IsOnLayer(layer):
                    continue
                poly = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_INSIDE)
                poly.Simplify()
                outlines = []
                for index in range(poly.OutlineCount()):
                    outlines.append(
                        dict(
                            outer=points(poly.COutline(index)),
                            holes=[points(poly.CHole(index, hole)) for hole in range(poly.HoleCount(index))],
                        )
                    )
                if outlines:
                    layers[name] = outlines
            if not layers:
                continue
            drill, position, size = pad.GetDrillSize(), pad.GetPosition(), pad.GetSize()
            rows.append(
                dict(
                    ref=footprint.GetReference(),
                    pin=pad.GetNumber(),
                    net=net,
                    uuid=pad.m_Uuid.AsString(),
                    layers=layers,
                    position_mm=[position.x / 1e6, position.y / 1e6],
                    drill_mm=[drill.x / 1e6, drill.y / 1e6],
                    nominal_size_mm=[size.x / 1e6, size.y / 1e6],
                    attribute=int(pad.GetAttribute()),
                )
            )
    return dict(
        source_pcb=str(source),
        source_pcb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        native_version=pcbnew.GetBuildVersion(),
        exporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        method="Native PAD.TransformShapeToPolygon, ERROR_INSIDE, 0.001 mm maximum curve approximation error",
        pad_polygons=rows,
        physical_qualified=False,
        original_pcb_modified=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = export(args.source)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Exported", len(result["pad_polygons"]), "actual copper pad shapes")
