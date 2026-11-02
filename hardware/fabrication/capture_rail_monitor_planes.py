"""Read E13 filled copper after native Unfracture; never refill or save the PCB."""

import hashlib
import json
import math
import sys
from pathlib import Path

from hardware.fabrication.capture_board import polygons


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    repo = Path(__file__).resolve().parents[2]
    source = repo / "hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/rail_monitor.kicad_pcb"
    output = repo / "hardware/fabrication/staging/rail-monitor-dc-inputs-01/unfractured-planes.json"
    assert not output.exists()
    digest = sha(source)
    board = pcbnew.LoadBoard(str(source))
    rows = []
    for zone in board.Zones():
        assert not zone.GetIsRuleArea()
        layer = zone.GetLayer()
        original = zone.GetFilledPolysList(layer)
        shape = pcbnew.SHAPE_POLY_SET(original)
        before = original.Area() / 1e12
        shape.Unfracture()
        after = shape.Area() / 1e12
        # Unfracture rejoins integer-grid intersections: do not claim bit-exact
        # contour area. Record the delta and reject material area changes.
        assert math.isclose(before, after, rel_tol=1e-8, abs_tol=1e-6), (before, after)
        rows.append(dict(uuid=zone.m_Uuid.AsString(), net=zone.GetNetname(),
                         layer=board.GetLayerName(layer), keepout=False,
                         native_area_before_mm2=before, native_area_after_mm2=after,
                         native_area_delta_mm2=after-before,
                         polygons=polygons(shape)))
    assert sha(source) == digest
    output.write_text(json.dumps(dict(
        source_sha256={str(source): digest, str(Path(__file__)): sha(Path(__file__)),
                       str(Path(__file__).with_name("capture_board.py")): sha(Path(__file__).with_name("capture_board.py"))},
        native_version=pcbnew.GetBuildVersion(), operation="SHAPE_POLY_SET copy then Unfracture",
        area_comparison_relative_tolerance=1e-8, area_comparison_absolute_tolerance_mm2=1e-6,
        PCB_refilled_or_saved=False, zones=rows, fabrication_approved=False,
    ), separators=(",", ":"))+"\n")
    print("Preserved", len(rows), "native planes and", sum(len(p["holes"]) for z in rows for p in z["polygons"]), "hole contours")


if __name__ == "__main__":
    run()
