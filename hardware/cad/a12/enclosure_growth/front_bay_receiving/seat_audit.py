"""Classify every raw seat-contact triangle; no mesh changes or repairs."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.interior_airpath.assembly import triangles

from .capture import ROOT, sha


def build():
    out = ROOT / "generated/mount3-seat-facet-audit.json"
    if out.exists():
        raise RuntimeError("New boundary audit required")
    folder = ROOT / "generated/native-mount3"
    rows = {}
    for name, planes in [
        ("own_PCB_seats_collision", [(1, 180.5), (2, 3.5)]),
        ("keeper_carrier_collision", [(2, 40.55), (2, 41.55)]),
        ("screw_carrier_receiving_collision", [(2, 45.6)]),
        ("screw_lid_bore_collision", [(2, 45.6)]),
    ]:
        p = folder / (name + ".stl")
        ts = triangles(p)
        maximum = 0
        not_boundary = 0
        for tri in ts:
            distance = min(max(abs(v[axis] - value) for v in tri) for axis, value in planes)
            maximum = max(maximum, distance)
            if distance > 2e-5:
                not_boundary += 1
        rows[name] = dict(
            triangles=len(ts),
            same_plane_per_triangle=True,
            declared_planes_axis_value=planes,
            maximum_deviation_mm=maximum,
            nonboundary_triangles=not_boundary,
            source_sha256=sha(p),
        )
    assert all(v["nonboundary_triangles"] == 0 for v in rows.values())
    out.write_text(
        json.dumps(
            dict(
                cases=rows,
                raw_geometry_retained=True,
                no_triangle_deleted_repaired_reoriented=True,
                only_nominal_correlated_seats_not_Z_tolerance_approval=True,
                source_sha256={
                    str(Path(__file__)): sha(Path(__file__)),
                    str(folder / "verification.json"): sha(folder / "verification.json"),
                },
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    build()
