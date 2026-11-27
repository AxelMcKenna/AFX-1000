"""Check delivered binary STL facets directly, with no mesh repair or hole filling."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(path):
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    assert len(raw) == 84 + count * 50, (path, "Not a complete binary STL")
    dtype = np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, count=count, offset=84)["vertices"].astype(float)
    assert np.isfinite(triangles).all(), (path, "Nonfinite vertex")
    areas2 = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1)
    assert np.all(areas2 > 1e-14), (path, "Degenerate triangles", int((areas2 <= 1e-14).sum()))
    vertices, ids = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = ids.reshape(-1, 3)
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    face_ids = np.tile(np.arange(count), 3)
    undirected = np.sort(directed, axis=1)
    _, edge_ids, incidence = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
    assert np.all(incidence == 2), (path, "Edges without exactly two incident facets", int((incidence != 2).sum()))
    signs = np.where(directed[:, 0] < directed[:, 1], 1, -1)
    balance = np.bincount(edge_ids, weights=signs)
    assert np.all(balance == 0), (path, "Inconsistent edge winding")
    edge_faces = face_ids[np.argsort(edge_ids)].reshape(-1, 2)
    parent = list(range(count))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in edge_faces:
        a, b = find(int(a)), find(int(b))
        if a != b:
            parent[b] = a
    components = len({find(i) for i in range(count)})
    assert components == 1, (path, "Disconnected solids", components)
    volume = float(np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum()/6)
    assert volume > 0, (path, "Nonpositive signed volume")
    bounds = [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()]
    assert bounds[0][2] >= -1e-5, (path, "Below print bed", bounds)
    return dict(file=str(path.relative_to(ROOT)), sha256=sha(path), triangles=count,
                exact_vertex_count=len(vertices), edges=int(len(incidence)), connected_components=components,
                zero_area_facets=0, bad_edge_incidence=0, inconsistent_edge_winding=0,
                signed_volume_mm3=volume, bounds_mm=bounds,
                extents_mm=(vertices.max(axis=0)-vertices.min(axis=0)).tolist())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stl_directory", type=Path)
    p.add_argument("--expected-count", type=int, default=67)
    p.add_argument("--output", default="delivery-independent-review.json")
    a = p.parse_args()
    paths = sorted(a.stl_directory.rglob("*.stl"))
    assert len(paths) == a.expected_count, (len(paths), a.expected_count)
    meshes = [inspect(path.resolve()) for path in paths]
    output = ROOT / a.output
    assert not output.exists(), "Keep successful reviews immutable"
    output.write_text(json.dumps(dict(scope="Independent direct binary STL delivery inspection; no repairs applied",
        review_script_sha256=sha(Path(__file__)), capture_sha256=sha(ROOT/"capture.json"),
        mesh_count=len(meshes), meshes=meshes,
        limits=["Edge topology and signed volume checks do not prove absence of every possible self-intersection",
                "Separate native CAD tests cover the declared assembly collision cases",
                "No measured printer, physical fit, material, electrical or thermal qualification"]), indent=2)+"\n")
    print(json.dumps(dict(report=str(output), meshes_passed=len(meshes))))


if __name__ == "__main__":
    main()
