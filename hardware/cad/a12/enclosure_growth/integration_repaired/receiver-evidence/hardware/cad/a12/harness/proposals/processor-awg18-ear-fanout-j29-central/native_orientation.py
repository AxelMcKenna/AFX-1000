"""Actual serialized J29 transform, native front courtyard and service bounds."""

import hashlib
import json
from pathlib import Path

import pcbnew

from hardware.electronics.common.sexpr import children, first, read_sexpr

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
    assert f.GetOrientationDegrees() % 360 == 0
    expected = {
        "1": ([175, 134], "AGND"),
        "2": ([175, 136.54], "POT_RAW_09"),
        "3": ([175, 139.08], "V3V3_ANALOG"),
    }
    rows = {}
    for p in f.Pads():
        point = [p.GetPosition().x / 1e6, p.GetPosition().y / 1e6]
        net = p.GetNetname().lstrip("/")
        assert (point, net) == expected[p.GetNumber()] and p.GetOrientationDegrees() % 360 == 0
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
    assert all(abs(x - y) < 1e-6 for x, y in zip(service, [102.735, 73.735, 107.265, 83.345]))
    # Native cache omits half the .01 mm serialization grid; retain actual saved extents too.
    tree = read_sexpr(path.read_text())
    sf = next(
        q
        for q in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J29"] for p in children(q, "property"))
    )
    rect = next(q for q in children(sf, "fp_rect") if first(q, "layer")[1] == "F.CrtYd")
    lo, hi = first(rect, "start")[1:], first(rect, "end")[1:]
    saved = [175 + float(lo[0]), 134 + float(lo[1]), 175 + float(hi[0]), 134 + float(hi[1])]
    saved_service = [saved[0] - 70 - 0.5, saved[1] - 58 - 0.5, saved[2] - 70 + 0.5, saved[3] - 58 + 0.5]
    assert all(abs(x - y) < 1e-7 for x, y in zip(saved_service, [102.73, 73.73, 107.27, 83.35]))
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
                cached_service_world_xy=service,
                serialized_Fcourtyard_native_mm=saved,
                inherited_service_world_xy=saved_service,
                front_courtyard_intersections=hits,
                full_service_tool_hardware_check_passed=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("ActualJ29angle0 transform verified", service)


if __name__ == "__main__":
    run()
