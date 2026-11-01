"""Actual KiCad global pad transforms and front courtyard overlap screen."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    path = ROOT / "processor_carrier.kicad_pcb"
    before = sha(path)
    b = pcbnew.LoadBoard(str(path))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    reports = []
    overlaps = []
    for ref, y in [("J14", 145.5), ("J15", 150.5)]:
        f = fps[ref]
        assert f.GetOrientationDegrees() == 90
        row = {}
        for p in f.Pads():
            xy = [p.GetPosition().x / 1e6, p.GetPosition().y / 1e6]
            expected = [258 if p.GetNumber() == "1" else 262, y]
            assert xy == expected, (ref, p.GetNumber(), xy)
            assert p.GetSize().x == p.GetSize().y == pcbnew.FromMM(
                3.4
            ) and p.GetDrillSize().x == p.GetDrillSize().y == pcbnew.FromMM(2.2)
            assert p.GetNetname().lstrip("/") == ("5V_DIG" if p.GetNumber() == "1" else "AGND")
            row[p.GetNumber()] = dict(
                native_mm=xy,
                world_mm=[xy[0] - 70, xy[1] - 58],
                actual_native_pad_orientation_degrees=p.GetOrientationDegrees(),
            )
        f.BuildCourtyardCaches()
        poly = f.GetCourtyard(pcbnew.F_Cu)
        assert poly.Area() > 0
        for other in fps.values():
            if other.GetReference() == ref:
                continue
            other.BuildCourtyardCaches()
            otherpoly = other.GetCourtyard(pcbnew.F_Cu)
            cross = pcbnew.SHAPE_POLY_SET()
            cross.BooleanIntersection(poly, otherpoly)
            if cross.Area() > 0:
                overlaps.append(
                    dict(port=ref, other=other.GetReference(), intersection_mm2=cross.Area() / 1e12)
                )
        reports.append(
            dict(
                ref=ref,
                footprint_orientation_degrees=90,
                pads=row,
                front_courtyard_area_mm2=poly.Area() / 1e12,
            )
        )
    assert not overlaps, overlaps
    assert before == sha(path)
    (ROOT / "generated/native-orientation.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=before,
                source_code_sha256=sha(Path(__file__)),
                native_version=pcbnew.GetBuildVersion(),
                ports=reports,
                front_courtyard_intersections=overlaps,
                whole_solder_service_and_wire_clearance_qualified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Native exactpadtransforms/courtyards clear", reports)


if __name__ == "__main__":
    run()
