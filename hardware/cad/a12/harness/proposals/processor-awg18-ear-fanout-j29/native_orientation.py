"""Actual serialized J29 transform, native front courtyard and service bounds."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bounds(poly):
    pts = [
        poly.COutline(i).CPoint(k)
        for i in range(poly.OutlineCount())
        for k in range(poly.COutline(i).PointCount())
    ]
    return [
        min(p.x for p in pts) / 1e6,
        min(p.y for p in pts) / 1e6,
        max(p.x for p in pts) / 1e6,
        max(p.y for p in pts) / 1e6,
    ]


def run():
    path = ROOT / "processor_carrier.kicad_pcb"
    h = sha(path)
    b = pcbnew.LoadBoard(str(path))
    f = next(f for f in b.GetFootprints() if f.GetReference() == "J29")
    assert f.GetOrientationDegrees() % 360 == 270
    expected = {
        "1": ([240.4, 157.8], "AGND"),
        "2": ([237.86, 157.8], "POT_RAW_09"),
        "3": ([235.32, 157.8], "V3V3_ANALOG"),
    }
    rows = {}
    for p in f.Pads():
        point = [p.GetPosition().x / 1e6, p.GetPosition().y / 1e6]
        net = p.GetNetname().lstrip("/")
        assert (point, net) == expected[p.GetNumber()] and p.GetOrientationDegrees() % 360 == 270
        rows[p.GetNumber()] = dict(
            native_mm=point,
            world_mm=[point[0] - 70, point[1] - 58],
            net=net,
            native_angle=p.GetOrientationDegrees(),
        )
    f.BuildCourtyardCaches()
    court = f.GetCourtyard(pcbnew.F_Cu)
    bb = bounds(court)
    hits = []
    for other in b.GetFootprints():
        if other.GetReference() == "J29":
            continue
        other.BuildCourtyardCaches()
        poly = other.GetCourtyard(pcbnew.F_Cu)
        cross = pcbnew.SHAPE_POLY_SET()
        cross.BooleanIntersection(court, poly)
        if cross.Area() > 0:
            hits.append(dict(ref=other.GetReference(), area_mm2=cross.Area() / 1e12))
    assert not hits, hits
    service = [bb[0] - 70 - 0.5, bb[1] - 58 - 0.5, bb[2] - 70 + 0.5, bb[3] - 58 + 0.5]
    assert all(abs(x - y) < 1e-6 for x, y in zip(service, [163.055, 97.535, 172.665, 102.065]))
    assert h == sha(path)
    (ROOT / "generated/native-orientation.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=h,
                source_code_sha256=sha(Path(__file__)),
                native_version=pcbnew.GetBuildVersion(),
                actual_J29_pinmap_verified=True,
                actual_pads=rows,
                actual_Fcourtyard_native_mm=bb,
                inherited_service_world_xy=service,
                front_courtyard_intersections=hits,
                full_service_tool_hardware_check_passed=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("ActualJ29minus90 transform verified", service)


if __name__ == "__main__":
    run()
