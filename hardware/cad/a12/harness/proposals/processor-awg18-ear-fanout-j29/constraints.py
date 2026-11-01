"""Read-only native proposed-J29 pose and neighboring geometry, no pose adoption."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-ear-fanout-spaced/processor_carrier.kicad_pcb"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bounds(poly):
    pts = [
        poly.COutline(i).CPoint(k)
        for i in range(poly.OutlineCount())
        for k in range(poly.COutline(i).PointCount())
    ]
    return (
        [
            min(p.x for p in pts) / 1e6,
            min(p.y for p in pts) / 1e6,
            max(p.x for p in pts) / 1e6,
            max(p.y for p in pts) / 1e6,
        ]
        if pts
        else None
    )


def run():
    before = sha(SOURCE)
    assert before == "e415660388344af08fb372d11ed011381e951cd021a1aa45b913900f0b9784c2"
    b = pcbnew.LoadBoard(str(SOURCE))
    fp = {f.GetReference(): f for f in b.GetFootprints()}
    f = fp["J29"]
    original = dict(
        at_mm=[f.GetPosition().x / 1e6, f.GetPosition().y / 1e6],
        angle=f.GetOrientationDegrees(),
        pads={p.GetNumber(): [p.GetPosition().x / 1e6, p.GetPosition().y / 1e6] for p in f.Pads()},
    )
    f.SetOrientationDegrees(-90)
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(240.4), pcbnew.FromMM(157.8)))
    f.BuildCourtyardCaches()
    court = f.GetCourtyard(pcbnew.F_Cu)
    box = bounds(court)
    proposed_pads = {
        p.GetNumber(): dict(
            native_mm=[p.GetPosition().x / 1e6, p.GetPosition().y / 1e6],
            world_mm=[p.GetPosition().x / 1e6 - 70, p.GetPosition().y / 1e6 - 58],
            net=p.GetNetname().lstrip("/"),
            native_pad_angle_degrees=p.GetOrientationDegrees(),
        )
        for p in f.Pads()
    }
    assert (
        proposed_pads["1"]["native_mm"] == [240.4, 157.8]
        and proposed_pads["2"]["native_mm"] == [237.86, 157.8]
        and proposed_pads["3"]["native_mm"] == [235.32, 157.8]
    )
    intersects = []
    neighbors = []
    for other in b.GetFootprints():
        if other.GetReference() == "J29":
            continue
        other.BuildCourtyardCaches()
        for layer, name in [(pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")]:
            p = other.GetCourtyard(layer)
            bb = bounds(p)
            if bb and bb[2] > 231 and bb[0] < 244 and bb[3] > 154 and bb[1] < 163:
                neighbors.append(dict(ref=other.GetReference(), face=name, courtyard_native_mm=bb))
            if layer == pcbnew.F_Cu:
                cross = pcbnew.SHAPE_POLY_SET()
                cross.BooleanIntersection(court, p)
                if cross.Area() > 0:
                    intersects.append(dict(ref=other.GetReference(), intersection_mm2=cross.Area() / 1e12))
    service = [box[0] - 70 - 0.5, box[1] - 58 - 0.5, box[2] - 70 + 0.5, box[3] - 58 + 0.5]
    report = dict(
        scope=__doc__,
        source_pcb_sha256=before,
        code_sha256=sha(Path(__file__)),
        native_version=pcbnew.GetBuildVersion(),
        original=original,
        proposed_footprint_at_native_mm=[240.4, 157.8],
        proposed_footprint_angle_degrees=-90,
        actual_native_proposed_pads=proposed_pads,
        actual_Fcourtyard_native_mm=box,
        inherited_service_box_world_xy=service,
        neighbor_courtyards=neighbors,
        proposed_front_courtyard_intersections=intersects,
        source_modified=False,
        full_native_routing_checked=False,
        service_collision_checked=False,
        pose_adopted=False,
        physical_qualified=False,
    )
    assert before == sha(SOURCE)
    (ROOT / "generated/constraints.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
