"""Certify every rejected raw mate facet against named source contact surfaces."""

import json
import math
import struct

from .port_boundary_audit import distance
from .stage import OUT, ROOT, sha, write

PLANES = {
    "M3_hardware_nominal_mates": (2, [-28.2, -27.7, -26.7, -26.2, -12.2]),
    "M2_hardware_nominal_mates": (1, [139, 144]),
    "upper_gasket_base": (2, [-6.2]),
    "upper_gasket_tray": (2, [-6.7]),
    "frame_gasket_tray": (2, [-25.2]),
    "frame_gasket_fan": (2, [-24.7]),
    "meter_gasket_wall_plate": (1, [141.5, 142]),
    "feedthrough_wall": (1, [142, 144]),
}


def polygon_edges(cx, cy, r):
    p = [
        (cx + r * math.cos(2 * math.pi * i / 96), cy + r * math.sin(2 * math.pi * i / 96)) for i in range(96)
    ]
    return list(zip(p, p[1:] + p[:1]))


def build():
    target = OUT / "raw-mating-surface-audit.json"
    if (ROOT / "handoff.json").exists() or target.exists():
        raise RuntimeError("Mating audit output is immutable")
    report = {}
    for name, (axis, planes) in PLANES.items():
        p = OUT / "mating-raw" / (name + ".stl")
        blob = p.read_bytes()
        count = struct.unpack_from("<I", blob, 80)[0]
        classes = {"named-plane": 0, "named-cylinder-facet": 0, "uncertified": 0}
        bad = []
        worst = 0
        curves = []
        if name == "frame_gasket_tray":
            curves = [
                (polygon_edges(cx + x, cy + y, 3.1), (0, 1), 2, [-25.2, -24.7])
                for cx, cy in [[80, 165.5], [254, 165.5]]
                for x in [-16, 16]
                for y in [-16, 16]
            ]
        if name == "feedthrough_wall":
            curves = [(polygon_edges(x, -10, 2.2), (0, 2), 1, [142, 144]) for x in [46, 235.5]]
        for i in range(count):
            raw = struct.unpack_from("<12fH", blob, 84 + 50 * i)
            tri = [raw[3:6], raw[6:9], raw[9:12]]
            pd = min(max(abs(v[axis] - plane) for v in tri) for plane in planes)
            if pd <= 0.00002:
                classes["named-plane"] += 1
                worst = max(worst, pd)
                continue
            best = float("inf")
            for edges, axes, along, interval in curves:
                if any(v[along] < interval[0] - 0.00002 or v[along] > interval[1] + 0.00002 for v in tri):
                    continue
                best = min(
                    best, min(max(distance((v[axes[0]], v[axes[1]]), a, b) for v in tri) for a, b in edges)
                )
            if best <= 0.00002:
                classes["named-cylinder-facet"] += 1
                worst = max(worst, best)
                continue
            classes["uncertified"] += 1
            bad.append(dict(index=i, vertices=tri, best_plane_distance=pd, best_cylinder_distance=best))
        report[name] = dict(
            triangles=count,
            classes=classes,
            max_certified_distance_mm=worst,
            uncertified=bad,
            source_planes=dict(axis=axis, positions=planes),
            cylinder_facets_fn=96 if curves else None,
            raw_STL_sha256=sha(p),
        )
    write(
        target,
        dict(
            cases=report,
            all_raw_triangles_certified=all(not r["uncertified"] for r in report.values()),
            certification_distance_mm=0.00002,
            source_sha256={
                "mating_audit.py": sha(ROOT / "mating_audit.py"),
                "mating.scad": sha(ROOT / "mating.scad"),
                "generated/checks.scad": sha(OUT / "checks.scad"),
            },
            raw_mating_receipt_sha256=sha(OUT / "mating-raw/verification.json"),
            raw_mates_accepted=False,
            physical_qualified=False,
            fabrication_released=False,
        ),
    )
    print(
        json.dumps(
            {
                n: dict(
                    triangles=r["triangles"],
                    classes=r["classes"],
                    max_distance_mm=r["max_certified_distance_mm"],
                )
                for n, r in report.items()
            }
        )
    )


if __name__ == "__main__":
    build()
