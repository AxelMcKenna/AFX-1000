"""Read-only native copper outline at the sliver checker's approximation."""

import json
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.capture_nf import polygons

if sys.platform == "linux":
    import pcbnew

ROOT = Path(__file__).resolve().parent


def run():
    assert sys.platform == "linux"
    source = ROOT/"staging/rail-monitor-sliver-native-01/rail_monitor.kicad_pcb"
    output = source.parent/"sliver-outline.json"
    assert not output.exists()
    digest = sha(source)
    # KiCad10 include/base_units.h: ARC_LOW_DEF_MM=0.02. The constant
    # is not exposed by pcbnew's Python binding. This only sets the read-only
    # diagnostic approximation; native DRC settings remain unchanged.
    error = pcbnew.FromMM(.02)
    print("Native ARC_LOW_DEF",error,flush=True)
    assert error is not None
    board = pcbnew.LoadBoard(str(source))
    poly = pcbnew.SHAPE_POLY_SET()
    items = [p for fp in board.GetFootprints() for p in fp.Pads()]+list(board.GetTracks())
    assert not any(z.IsOnLayer(pcbnew.F_Cu) for z in board.Zones())
    for item in items:
        if item.IsOnLayer(pcbnew.F_Cu):
            item.TransformShapeToPolygon(poly,pcbnew.F_Cu,0,error,pcbnew.ERROR_INSIDE)
    poly.Simplify()
    assert sha(source) == digest
    output.write_text(json.dumps(dict(source_sha256={str(source):digest,str(Path(__file__)):sha(Path(__file__))},
        layer="F.Cu",native_inside_approximation_error_IU=error,polygons=polygons(poly),
        diagnostic_only=True,fabrication_released=False))+"\n")


if __name__ == "__main__":
    run()
