"""Routing-only convex partition of exact filled planes; native proof required.

Run with Shapely 2.1.2 in isolated task scratch. A constrained triangulation
retains boundary/hole edges; convex merges only join adjacent triangles. No
buffer, simplification, repair, rounded vertex or native PCB edit is permitted.
"""

import argparse
import collections
import hashlib
import json
import re
import shutil
from pathlib import Path

import shapely

from ...common.sexpr import children, first, read_sexpr
from .select_native_open_nets import span


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertices(poly):
    result = []
    for x, y in list(poly.exterior.coords)[:-1]:
        assert abs(x - round(x)) < 1e-5 and abs(y - round(y)) < 1e-5
        result.append((round(x), round(y)))
    return result


def convex(poly):
    if poly.geom_type != "Polygon" or poly.interiors:
        return False
    p = vertices(poly)
    turns = [
        (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        for a, b, c in zip(p, p[1:] + p[:1], p[2:] + p[:2])
    ]
    return all(t >= 0 for t in turns) or all(t <= 0 for t in turns)


def partition(poly):
    # Native unions may contain zero-width vertex touches, which GEOS labels
    # non-simple. Do not repair/buffer them. Constrained triangles retain the
    # exact boundary; native integer union equivalence remains mandatory.
    pieces = list(shapely.constrained_delaunay_triangles(poly).geoms)
    assert pieces and all(p.geom_type == "Polygon" and not p.interiors for p in pieces)
    edges = collections.defaultdict(list)
    for i, triangle in enumerate(pieces):
        pts = vertices(triangle)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            edges[tuple(sorted((a, b)))].append(i)
    neighbors = [set() for p in pieces]
    pending = collections.deque()
    for members in edges.values():
        assert len(members) <= 2
        if len(members) == 2:
            a, b = members
            neighbors[a].add(b)
            neighbors[b].add(a)
            pending.append((a, b))
    parent = list(range(len(pieces)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    while pending:
        a, b = (root(i) for i in pending.popleft())
        if a == b:
            continue
        joined = pieces[a].union(pieces[b])
        if not convex(joined):
            continue
        parent[b] = a
        pieces[a] = joined
        neighbors[a] = {root(i) for i in neighbors[a] | neighbors[b]} - {a}
        for i in neighbors[a]:
            pending.append((a, i))
    result = [pieces[i] for i in range(len(pieces)) if root(i) == i]
    combined = shapely.union_all(result)
    assert abs(combined.area - poly.area) < 1e3
    if poly.is_valid:
        assert combined.symmetric_difference(poly).area < 1e-3
    return result, len(pieces)


def main(reference, workspace):
    reference, workspace = Path(reference).resolve(), Path(workspace).resolve()
    base = Path(__file__).resolve().parent / "generated"
    assert reference.is_relative_to(base) and workspace.is_relative_to(base)
    assert not workspace.exists()
    workspace.mkdir()
    # Copy only frozen export inputs; preserve failed baselines in their source
    # workspace rather than reusing/overwriting their sessions or logs.
    for p in reference.iterdir():
        if p.is_file() and not p.name.startswith(("baseline", "routed-")):
            shutil.copy2(p, workspace / p.name)
    shutil.copytree(reference / "source", workspace / "source")
    metadata_path = workspace / "export.json"
    meta = json.loads(metadata_path.read_text())
    dsn = workspace / meta["dsn_filename"]
    assert sha(dsn) == meta["dsn_sha256"]
    before = dsn.read_text()
    ranges = [span(before, m.end() - len("(plane")) for m in re.finditer(r"(?m)^[ \t]*\(plane\b", before)]
    replacements, rows = [], []
    for start, end in ranges:
        node = read_sexpr(before[start:end])
        outer = first(node, "polygon")

        def points(p):
            values = list(map(float, p[3:]))
            assert len(values) % 2 == 0
            return [(round(values[i] * 1000), round(values[i + 1] * 1000)) for i in range(0, len(values), 2)]

        poly = shapely.Polygon(points(outer), [points(first(w, "polygon")) for w in children(node, "window")])
        pieces, triangles = partition(poly)
        layer, net = str(outer[1]), str(node[1])
        definitions = []
        for piece in pieces:
            pts = vertices(piece)
            definitions.append(
                "    (plane %s (polygon %s 0 %s))"
                % (json.dumps(net), layer, " ".join("%.3f %.3f" % (x / 1000, y / 1000) for x, y in pts))
            )
        replacements.append("\n".join(definitions))
        rows.append(
            dict(
                net=net,
                layer=layer,
                source_native_area_mm2=poly.area / 1e12,
                native_contour_is_simple=bool(poly.is_valid),
                native_contour_topology=shapely.is_valid_reason(poly),
                triangles=triangles,
                convex_pieces=len(pieces),
            )
        )
    chunks, cursor = [], 0
    for (start, end), replacement in zip(ranges, replacements):
        chunks.extend((before[cursor:start], replacement))
        cursor = end
    chunks.append(before[cursor:])
    text = "".join(chunks)
    report = dict(
        reference_export_sha256=sha(reference / "export.json"),
        source_dsn_sha256=meta["dsn_sha256"],
        rows=rows,
        shapely_version=shapely.__version__,
        geos_version=shapely.geos_version_string,
        helper_sha256=sha(Path(__file__)),
        geometric_repairs_or_buffers_used=False,
        all_nonplane_dsn_bytes_preserved=True,
        native_integer_union_verified=False,
        native_baseline_required=True,
        physical_qualified=False,
    )
    report_path = workspace / "triangulated-plane-adapter.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    (workspace / "export-before-convex-partition.json").write_text(json.dumps(meta, indent=2) + "\n")
    name = "afx-" + hashlib.sha256((meta["design_name"] + sha(report_path)).encode()).hexdigest()[:24]
    output = workspace / (name + ".dsn")
    output.write_text(text)
    meta.update(
        design_name=name,
        dsn_filename=output.name,
        dsn_sha256=sha(output),
        triangulated_plane_adapter_sha256=sha(report_path),
    )
    metadata_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("Exact filled planes partitioned into", sum(r["convex_pieces"] for r in rows), "convex pieces")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference")
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.reference, args.workspace)
