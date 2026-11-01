"""Read actual pad, drill and keepout geometry for NEW local-via candidates."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]


def points(chain):
    return [[chain.CPoint(i).x / 1e6, chain.CPoint(i).y / 1e6] for i in range(chain.PointCount())]


def polygons(poly):
    return [dict(outer=points(poly.COutline(i)), holes=[points(poly.CHole(i, h)) for h in range(poly.HoleCount(i))])
            for i in range(poly.OutlineCount())]


def main():
    source = ROOT / "negative_startup_physical.kicad_pcb"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    board = pcbnew.LoadBoard(str(source))
    rows = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            layer_shapes = {}
            for name in LAYERS:
                layer = board.GetLayerID(name)
                if not pad.IsOnLayer(layer):
                    continue
                poly = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(.001), pcbnew.ERROR_INSIDE)
                poly.Simplify()
                layer_shapes[name] = polygons(poly)
            drill, pos = pad.GetDrillSize(), pad.GetPosition()
            rows.append(dict(ref=fp.GetReference(), pin=pad.GetNumber(), uuid=pad.m_Uuid.AsString(),
                             net=pad.GetNetname(), layers=layer_shapes,
                             side="B.Cu" if fp.IsFlipped() else "F.Cu",
                             position_mm=[pos.x / 1e6, pos.y / 1e6],
                             drill_mm=[drill.x / 1e6, drill.y / 1e6],
                             SMD=int(pad.GetAttribute()) == int(pcbnew.PAD_ATTRIB_SMD)))
    keepouts = [dict(name=z.GetZoneName(), layer=board.GetLayerName(z.GetLayer()),
                     polygons=polygons(z.Outline())) for z in board.Zones() if z.GetIsRuleArea()]
    assert len(keepouts) == 36
    result = dict(source_PCB_sha256=digest, source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  pad_polygons_maximum_inside_approximation_error_mm=.001,
                  planning_additional_geometry_allowance_mm=.002,
                  pads=rows, keepouts=keepouts, physical_qualified=False)
    out = ROOT / "generated/power-via-pad-geometry.json"
    assert not out.exists(), "Preserve earlier geometric inputs"
    out.write_text(json.dumps(result, indent=2) + "\n")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    print("Actual native", len(rows), "pad shapes and36 layer keepouts exported; source unchanged")


if __name__ == "__main__":
    main()
