"""Read actual filled-zone polygons, with native hole contours preserved."""

import hashlib
import json
import sys
from pathlib import Path

if sys.platform == "linux":
    import pcbnew

    from hardware.electronics.rail_disconnect.revision28 import native_pad_geometry

ROOT = Path(__file__).resolve().parent


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    folder = ROOT/"staging/e28-copper-audit"
    capture = json.loads((folder/"capture.json").read_text())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == capture["source_sha256"][str(source)]
    destination = folder/"planes.json"
    assert not destination.exists()
    board = pcbnew.LoadBoard(str(source))
    rows = []
    for zone in board.Zones():
        if zone.GetIsRuleArea():
            continue
        for name in ("F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","In5.Cu","In6.Cu","B.Cu"):
            layer = board.GetLayerID(name)
            if not zone.IsOnLayer(layer):
                continue
            poly = zone.GetFilledPolysList(layer)
            rows.append(dict(uuid=zone.m_Uuid.AsString(),net=zone.GetNetname().lstrip("/"),layer=name,
                polygons=[dict(outer=native_pad_geometry.points(poly.COutline(i)),
                    holes=[native_pad_geometry.points(poly.CHole(i,j)) for j in range(poly.HoleCount(i))])
                    for i in range(poly.OutlineCount())]))
    destination.write_text(json.dumps(dict(source_pcb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        native_filled_zone_polygons=rows,holes_preserved=True,physical_qualified=False),indent=2)+"\n")
    print("Captured",len(rows),"native filled-zone/layer shapes")


if __name__ == "__main__":
    run()
