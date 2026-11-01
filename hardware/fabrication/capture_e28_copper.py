"""Capture conservative native copper shapes around the 33 retained track stubs.

Targets use ERROR_OUTSIDE and supporting electrodes use ERROR_INSIDE. Source
drills remain unchanged. This exports evidence only; it does not edit the PCB.
"""

import hashlib
import json
import sys
from pathlib import Path

if sys.platform == "linux":
    import pcbnew

    from hardware.electronics.rail_disconnect.revision28 import native_pad_geometry

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/"hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06"
OUTPUT = REPO/"hardware/fabrication/staging/e28-copper-audit"
LAYERS = ("F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","In5.Cu","In6.Cu","B.Cu")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygon(item, layer, outside=False):
    shape = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(shape, layer, 0, pcbnew.FromMM(.001),
                                 pcbnew.ERROR_OUTSIDE if outside else pcbnew.ERROR_INSIDE)
    shape.Simplify()
    return [dict(outer=native_pad_geometry.points(shape.COutline(i)),
                 holes=[native_pad_geometry.points(shape.CHole(i,j)) for j in range(shape.HoleCount(i))])
            for i in range(shape.OutlineCount())]


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    assert not OUTPUT.exists()
    pcb, drc = SOURCE/"rail_disconnect.kicad_pcb", SOURCE/"drc.json"
    hashes = {str(p):sha(p) for p in (pcb,drc)}
    report = json.loads(drc.read_text())
    assert not report["unconnected_items"] and not report["schematic_parity"]
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    connection.RecalculateRatsnest()
    assert connection.GetUnconnectedCount(False) == 0
    tracks = list(board.GetTracks())
    objects = {item.m_Uuid.AsString(): item for item in tracks}
    targets = [v["items"][0]["uuid"] for v in report["violations"] if v["type"] == "track_dangling"]
    assert len(targets) == 33
    metadata = []
    for item in tracks:
        bounds = item.GetBoundingBox()
        metadata.append((item,item.GetNetname(),[bounds.GetLeft(),bounds.GetTop(),bounds.GetRight(),bounds.GetBottom()]))
    cache = {}
    target_rows = []
    for identifier in targets:
        item = objects[identifier]
        layer = item.GetLayer()
        bounds = item.GetBoundingBox()
        window = (bounds.GetLeft()-2000,bounds.GetTop()-2000,bounds.GetRight()+2000,bounds.GetBottom()+2000)
        neighbors = []
        for other,net,b in metadata:
            if net != item.GetNetname() or other.m_Uuid.AsString() == identifier or not other.IsOnLayer(layer):
                continue
            if b[2] < window[0] or b[0] > window[2] or b[3] < window[1] or b[1] > window[3]:
                continue
            key = other.m_Uuid.AsString()+":"+board.GetLayerName(layer)
            if key not in cache:
                cache[key] = dict(uuid=other.m_Uuid.AsString(),net=net.lstrip("/"),layer=board.GetLayerName(layer),
                                  kind=other.GetClass(),polygons=polygon(other,layer))
            neighbors.append(key)
        target_rows.append(dict(uuid=identifier,net=item.GetNetname().lstrip("/"),layer=board.GetLayerName(layer),
                                polygons=polygon(item,layer,True),supporting_objects=neighbors))
    vias = []
    for finding in report["violations"]:
        if finding["type"] != "via_dangling":
            continue
        item = objects[finding["items"][0]["uuid"]]
        position = item.GetPosition()
        vias.append(dict(uuid=item.m_Uuid.AsString(),net=item.GetNetname().lstrip("/"),
            position_mm=[position.x/1e6,position.y/1e6],drill_mm=item.GetDrillValue()/1e6,
            connected_layers=[name for name in LAYERS if connection.IsConnectedOnLayer(item,board.GetLayerID(name))]))
    native_pad_geometry.LAYERS = LAYERS
    pads = native_pad_geometry.export(pcb)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"pads.json").write_text(json.dumps(pads,indent=2)+"\n")
    (OUTPUT/"capture.json").write_text(json.dumps(dict(source_sha256=hashes,
        native_version=pcbnew.GetBuildVersion(),target_track_polygons_error="outside0.001mm",
        support_polygons_error="inside0.001mm",targets=target_rows,supporting_copper=cache,
        dangling_vias=vias,source_unchanged=True,physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    assert all(sha(Path(p)) == h for p,h in hashes.items())
    print("Captured33 track stubs,",len(cache),"nearby electrodes and19 via layer-connectivity records")


if __name__ == "__main__":
    run()
