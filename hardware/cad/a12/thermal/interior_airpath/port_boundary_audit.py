"""Identify every raw exact-Boolean void residue against authored cut faces."""

import json
import math
import struct

from .stage import OUT, ROOT, sha, write


def edges():
    polygons = []
    for x, y, w, h, r in [(38, 164, 72, 19, 1), (231.5, 154, 45, 29, 1)]:
        pts = []
        for cx, cy, start in [
            (x + r, y + r, 180),
            (x + w - r, y + r, 270),
            (x + w - r, y + h - r, 0),
            (x + r, y + h - r, 90),
        ]:
            pts += [
                (
                    cx + r * math.cos(math.radians(start + 90 * i / 24)),
                    cy + r * math.sin(math.radians(start + 90 * i / 24)),
                )
                for i in range(25)
            ]
        polygons.append(pts)
    polygons.append(
        [
            (93.0871 + 6 * math.cos(2 * math.pi * i / 256), 168.9352 + 6 * math.sin(2 * math.pi * i / 256))
            for i in range(256)
        ]
    )
    return [e for p in polygons for e in zip(p, p[1:] + p[:1])]


def distance(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / (vx * vx + vy * vy)))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def build():
    if (ROOT / "handoff.json").exists() or (OUT / "raw-port-boundary-recheck.json").exists():
        raise RuntimeError("Boundary-audit output is immutable")
    target = OUT / "initial-ports/inlet_solid_void_collision.stl"
    data = target.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    boundary = edges()
    rows = {"Z-plane": 0, "XY-cut-facet": 0, "not-certified": 0}
    worst = 0
    bad = []
    for i in range(count):
        raw = struct.unpack_from("<12fH", data, 84 + 50 * i)
        p = [raw[3:6], raw[6:9], raw[9:12]]
        zd = min(max(abs(v[2] - z) for v in p) for z in [-6.2, 0, 2.8])
        if zd <= 0.00002:
            rows["Z-plane"] += 1
            worst = max(worst, zd)
            continue
        xy = min(max(distance(v, a, b) for v in p) for a, b in boundary)
        if xy <= 0.00002:
            rows["XY-cut-facet"] += 1
            worst = max(worst, xy)
            continue
        rows["not-certified"] += 1
        bad.append(dict(index=i, vertices=p, best_z_distance=zd, best_XY_facet_distance=xy))
    report = dict(
        raw_triangles=count,
        triangle_classification=rows,
        max_certified_surface_distance_mm=worst,
        classification_distance_mm=0.00002,
        exact_source_cut_construction="96-vertex R1 roundedrectcorners plus256-vertex R6 island; Zseats−6.2/0/2.8",
        nonboundary_triangles=bad,
        raw_collision_accepted=False,
        proposed_test_only_interior_guard="ErodevoidXYby20nm andexcludeZendfacesby20nm; allactualparts/windows unchanged",
        source_sha256={
            "port_boundary_audit.py": sha(ROOT / "port_boundary_audit.py"),
            "geometry.scad": sha(ROOT / "geometry.scad"),
            "raw_stl": sha(target),
        },
        physical_qualified=False,
        thermal_qualified=False,
    )
    m = json.loads((ROOT / "history/initial-port-inputs/reconstruction-map.json").read_text())["input_bytes"]
    original = ROOT / m[str(ROOT / "geometry.scad")]["copy"]
    report["source_sha256"]["original_geometry_copy"] = sha(original)
    report["source_sha256"].pop("geometry.scad")
    report["original_geometry_copy"] = str(original.relative_to(ROOT))
    report["original_root_approved_report_sha256"] = sha(OUT / "raw-port-boundary-audit.json")
    write(OUT / "raw-port-boundary-recheck.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in ["raw_triangles", "triangle_classification", "max_certified_surface_distance_mm"]
            }
        )
    )


if __name__ == "__main__":
    build()
