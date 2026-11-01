"""Independent binary-STL face and directed-edge audit of PB02 exported parts."""

import hashlib
import json
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inspect(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count and count
    edge_faces = defaultdict(list)
    edges = Counter()
    directed = Counter()
    volumes = []
    degenerate = 0
    for i in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * i)
        a, b, c = row[3:6], row[6:9], row[9:12]
        ab = tuple(b[j] - a[j] for j in range(3))
        ac = tuple(c[j] - a[j] for j in range(3))
        cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
        degenerate += cross == (0.0, 0.0, 0.0)
        volumes.append(
            (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                + a[1] * (b[2] * c[0] - b[0] * c[2])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            )
            / 6
        )
        for u, v in [(a, b), (b, c), (c, a)]:
            edge = tuple(sorted([u, v]))
            edges[edge] += 1
            directed[(u, v)] += 1
            edge_faces[edge].append(i)
    neighbors = defaultdict(set)
    for faces in edge_faces.values():
        for i in faces:
            neighbors[i].update(j for j in faces if j != i)
    unseen = set(range(count))
    boundary_volumes = []
    while unseen:
        frontier = [unseen.pop()]
        component = []
        while frontier:
            i = frontier.pop()
            component.append(i)
            for j in neighbors[i].intersection(unseen):
                unseen.remove(j)
                frontier.append(j)
        boundary_volumes.append(math.fsum(volumes[i] for i in component))
    badshared = sum(n != 2 for n in edges.values())
    badoriented = sum(n != directed[(v, u)] for (u, v), n in directed.items())
    return dict(
        triangles=count,
        zero_area_faces=degenerate,
        non_two_shared_edges=badshared,
        unmatched_directed_edges=badoriented,
        connected_boundaries=len(boundary_volumes),
        signed_boundary_volumes_mm3=boundary_volumes,
        strict_closed_oriented_nonzero=not degenerate
        and not badshared
        and not badoriented
        and all(v > 0 for v in boundary_volumes),
    )


def main():
    geometry = json.loads((ROOT / "generated/geometry.json").read_text())
    records = {}
    for name in geometry["parts"]:
        p = ROOT / "generated" / (name + ".stl")
        assert sha(p) == geometry["artifact_sha256"][str(p.relative_to(REPO))]
        records[name] = dict(sha256=sha(p), **inspect(p))
    result = dict(
        scope=__doc__,
        all32_parts_strict_meshes=all(x["strict_closed_oriented_nonzero"] for x in records.values()),
        records=records,
        source_geometry_receipt_sha256=sha(ROOT / "generated/geometry.json"),
        script_sha256=sha(Path(__file__)),
        modified_or_repaired_meshes=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "mesh-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "strict meshes", sum(x["strict_closed_oriented_nonzero"] for x in records.values()), "/", len(records)
    )
    for name, row in records.items():
        if not row["strict_closed_oriented_nonzero"]:
            print(name, row)


if __name__ == "__main__":
    main()
