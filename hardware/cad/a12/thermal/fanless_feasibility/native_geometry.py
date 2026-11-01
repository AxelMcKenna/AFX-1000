"""Independent saved native STL dimensions/areas; no collision or fit guarantee."""

import json
import re

from .analyze import OUT, ROOT, sha


def metadata(path):
    import math

    pts = [[float(v) for v in row] for row in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", path.read_text())]
    if len(pts) == 0 or len(pts) % 3:
        raise ValueError("Missing/incomplete required native solid")

    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

    def sub(a, b):
        return [u - v for u, v in zip(a, b)]

    from collections import Counter

    ids = {}
    parents = []

    def vid(point):
        key = tuple(round(v, 7) for v in point)
        if key not in ids:
            ids[key] = len(parents)
            parents.append(len(parents))
        return ids[key]

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    edges = Counter()
    balances = Counter()
    for i in range(0, len(pts), 3):
        tri = [vid(point) for point in pts[i : i + 3]]
        for a, b in zip(tri, tri[1:] + tri[:1]):
            e = tuple(sorted((a, b)))
            edges[e] += 1
            balances[e] += 1 if a < b else -1
            parents[root(a)] = root(b)
    components = len({root(i) for i in range(len(parents))})
    areas = []
    volumes = []
    lower = []
    for i in range(0, len(pts), 3):
        a, b, c = pts[i : i + 3]
        area = math.sqrt(sum(v * v for v in cross(sub(b, a), sub(c, a)))) / 2
        areas.append(area)
        volumes.append(sum(u * v for u, v in zip(a, cross(b, c))) / 6)
        if max(a[2], b[2], c[2]) <= -6.2 + 1e-8:
            lower.append(area)
    volume = abs(math.fsum(volumes))
    if not volume > 0 or not all(math.isfinite(v) for p in pts for v in p):
        raise ValueError("Empty/nonfinite native solid")
    return dict(
        sha256=sha(path),
        triangles=len(areas),
        zero_area_faces=sum(a <= 1e-12 for a in areas),
        bounds_mm=[
            [round(min(p[i] for p in pts), 9) for i in range(3)],
            [round(max(p[i] for p in pts), 9) for i in range(3)],
        ],
        edge_merge_resolution_mm=1e-7,
        connected_components=components,
        nonmanifold_edges=sum(count != 2 for count in edges.values()),
        inconsistent_oriented_edges=sum(value != 0 for value in balances.values()),
        volume_mm3=round(volume, 6),
        surface_area_mm2=round(math.fsum(areas), 6),
        downward_array_wetted_area_mm2=round(math.fsum(lower), 6),
        area_is_not_a_heat_transfer_coefficient=True,
    )


def main():
    rows = {name: metadata(OUT / (name + ".stl")) for name in ["bottom", "lid"]}
    # feet contact plate, not cooled plate. Foot fins already excluded toR12.
    import math

    rows["bottom"]["wetted_minus_four18mm_foot_disks_m2"] = (
        rows["bottom"]["downward_array_wetted_area_mm2"] - 4 * math.pi * 9**2
    ) * 1e-6
    a = dict(
        native_version="OpenSCAD2026.10.15",
        native_backend_requested="Manifold",
        actual_native_output_types={"bottom": "Manifold", "lid": "PolySet extrusion"},
        independent_edge_topology_checked=True,
        parts=rows,
        only_geometry_screen=True,
        fit_collision_or_thermal_qualification=False,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [OUT / "prototype.scad", ROOT / "native_geometry.py", OUT / "geometry-contract.json"]
        },
    )
    (OUT / "native-geometry.json").write_text(json.dumps(a, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
