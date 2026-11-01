"""Actual native lid/seat/fin projection and cut-wall finite-volume geometry.

The conductive replacement remains a proposal. Planar metal components and
shared faces retain real apertures; cassette/boss thermal bridges get no credit.
"""

import json
import math
import re
import struct
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent


def triangles(path):
    raw = path.read_bytes()
    if len(raw) >= 84:
        n = struct.unpack("<I", raw[80:84])[0]
        if len(raw) == 84 + 50 * n:
            dt = np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
            return np.asarray(np.frombuffer(raw, offset=84, count=n, dtype=dt)["v"], float)
    points = np.array(
        [[float(v) for v in q] for q in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", raw.decode())]
    )
    assert len(points) % 3 == 0
    return points.reshape(-1, 3, 3)


def planar(path, z):
    tri = triangles(path)
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    selected = tri[(np.max(abs(tri[:, :, 2] - z), axis=1) < 1e-4) & (cross[:, 2] > 1e-10)]
    pieces = [Polygon(t[:, :2]) for t in selected]
    p = unary_union(pieces)
    assert p.is_valid and not p.is_empty
    rawarea = sum(x.area for x in pieces)
    assert abs(rawarea - p.area) < 1e-4, (path, rawarea, p.area)
    return p


def polygons(p):
    if p.is_empty:
        return []
    if p.geom_type == "Polygon":
        return [p] if p.area > 1e-10 else []
    return [q for x in p.geoms for q in polygons(x)]


def layout():
    cfg = {}
    for line in (ROOT / "sources/layout.scad").read_text().splitlines():
        if " = " in line:
            key, value = line.split(" = ", 1)
            cfg[key] = json.loads(value.rstrip(";"))
    return cfg


def cap_shape(c):
    _, kind, x, y, w, h, a, b = c
    if kind == "knob":
        return Point(x, y).buffer(w / 2, quad_segs=128)
    if kind == "sector":
        angle = np.linspace(math.radians(a), math.radians(b), 257)
        outer = [(x + h * math.cos(t), y + h * math.sin(t)) for t in angle]
        inner = [(x + w * math.cos(t), y + w * math.sin(t)) for t in angle[::-1]]
        return Polygon(outer + inner)
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def build(contract, grid):
    nx, ny = grid
    W = contract["base"]["width"]
    D = contract["base"]["depth"]
    H = contract["walls"]["height"]
    xe = np.linspace(0, W, nx + 1)
    ye = np.linspace(0, D, ny + 1)
    panel = planar(ROOT / "sources/lid.stl", 45.6)
    seat = planar(ROOT / "sources/shell.stl", 43.6)
    dimensions = json.load(open(ROOT / "sources/dimensions.json"))
    # No unimplemented fastener/boss conduction is credited.
    bosses = unary_union(
        [Point(*p).buffer(4.2, quad_segs=128) for p in dimensions["candidate_shell_fasteners_xy"]]
    )
    contact = seat.intersection(panel).difference(bosses)
    caps = unary_union([cap_shape(c) for c in layout()["caps"]])
    roots = planar(ROOT / "sources/fins.stl", 56)
    polys = []
    cells = {}
    centres = []
    areas = []
    topareas = []
    rootareas = []
    for j in range(ny):
        for i in range(nx):
            pieces = polygons(panel.intersection(box(xe[i], ye[j], xe[i + 1], ye[j + 1])))
            cells[j, i] = []
            for p in pieces:
                cells[j, i].append(len(polys))
                polys.append(p)
                centres.append((p.centroid.x, p.centroid.y))
                areas.append(p.area * 1e-6)
                rootareas.append(p.intersection(roots).area * 1e-6)
                topareas.append(p.difference(caps).difference(roots).area * 1e-6)
    assert abs(sum(areas) * 1e6 - panel.area) < 1e-4
    assert abs(sum(rootareas) * 1e6 - panel.intersection(roots).area) < 1e-5
    neighbors = []
    for j in range(ny):
        for i in range(nx):
            for ii, jj, dist in [(i + 1, j, W / nx), (i, j + 1, D / ny)]:
                if ii >= nx or jj >= ny:
                    continue
                for a in cells[j, i]:
                    for b in cells[jj, ii]:
                        shared = polys[a].intersection(polys[b])
                        assert shared.area < 1e-8
                        if shared.length > 1e-9:
                            neighbors.append((a, b, shared.length, dist))
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    uv = np.array([(a, b) for a, b, L, d in neighbors])
    u, v = uv.T
    adjacency = coo_matrix((np.ones(2 * len(u)), (np.r_[u, v], np.r_[v, u])), shape=(len(polys), len(polys)))
    lid_components, _ = connected_components(adjacency, directed=False)
    assert lid_components == 1, "Actual native lid sheet became disconnected in discretization"
    owners = {node: cell for cell, ids in cells.items() for node in ids}
    assert all(owners[a] != owners[b] for a, b, L, d in neighbors)
    tree = STRtree(polys)
    finareas = np.zeros(len(polys))
    rawvertical = 0
    for tri in triangles(ROOT / "sources/fins.stl"):
        cr = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        area = np.linalg.norm(cr) / 2
        if abs(cr[2]) > 1e-8 or area < 1e-10:
            continue
        xy = tri[:, :2]
        a, b = max(((p, q) for p in xy for q in xy), key=lambda pq: np.linalg.norm(pq[0] - pq[1]))
        line = LineString([a, b])
        assert line.length > 0
        shares = []
        for q in tree.query(line, predicate="intersects"):
            q = int(q)
            if rootareas[q] <= 1e-18:
                continue
            length = line.intersection(polys[q]).length
            if length > 1e-10:
                shares.append((q, length))
        total = sum(x[1] for x in shares)
        assert total >= line.length * (1 - 1e-6), ("Unattached actual fin root", line.length, total)
        # A line coincident with a cell boundary is divided, not counted twice.
        for q, length in shares:
            finareas[q] += area * 1e-6 * length / total
        rawvertical += area * 1e-6
    assert abs(finareas.sum() - rawvertical) < 1e-12
    cut = contract["walls"]
    ze = sorted(set([*np.linspace(0, H, cut["coarse_vertical_cells"] + 1), 3.8, 8.0, 16.0, 31.0]))
    face_specs = {
        "N": (sorted(set([*xe, 26.0, 308.0])), [[26, 3.8, 308, 31]]),
        "E": (list(ye), []),
        "S": (
            sorted(set([*xe, *[v for slot in cut["front_slots_xz"] for v in [slot[0], slot[2]]]])),
            cut["front_slots_xz"],
        ),
        "W": (list(ye), []),
    }
    wall = []
    index = {}
    wedges = {}
    for face, (se, cuts) in face_specs.items():
        wedges[face] = se
        for z in range(len(ze) - 1):
            for s in range(len(se) - 1):
                sc = (se[s] + se[s + 1]) / 2
                zc = (ze[z] + ze[z + 1]) / 2
                if any(a < sc < b and lo < zc < hi for a, lo, b, hi in cuts):
                    continue
                index[face, s, z] = len(wall)
                wall.append(
                    dict(
                        face=face,
                        s=s,
                        z=z,
                        lo=se[s],
                        hi=se[s + 1],
                        bottom=ze[z],
                        top=ze[z + 1],
                        width=se[s + 1] - se[s],
                        dz=ze[z + 1] - ze[z],
                    )
                )
    wall_neighbors = []
    for key, a in index.items():
        face, s, z = key
        r = wall[a]
        for k, typ in [((face, s + 1, z), "lateral"), ((face, s, z + 1), "vertical")]:
            if k in index:
                b = index[k]
                q = wall[b]
                distance = (r["width"] + q["width"]) / 2 if typ == "lateral" else (r["dz"] + q["dz"]) / 2
                wall_neighbors.append((a, b, typ, r["dz"] if typ == "lateral" else r["width"], distance))
    # Continuous integral corners are a declared thin-wall scenario, no cassette bridge.
    for z in range(len(ze) - 1):
        for f, si, g, sj in [
            ("N", len(wedges["N"]) - 2, "E", 0),
            ("E", len(wedges["E"]) - 2, "S", len(wedges["S"]) - 2),
            ("S", 0, "W", len(wedges["W"]) - 2),
            ("W", 0, "N", 0),
        ]:
            if (f, si, z) in index and (g, sj, z) in index:
                a = index[f, si, z]
                b = index[g, sj, z]
                wall_neighbors.append(
                    (a, b, "corner", wall[a]["dz"], (wall[a]["width"] + wall[b]["width"]) / 2)
                )
    base_links = []
    for (face, s, z), wi in index.items():
        if z != 0:
            continue
        row = wall[wi]
        mid = (row["lo"] + row["hi"]) / 2
        if face in ["N", "S"]:
            i = min(nx - 1, int(mid / (W / nx)))
            j = 0 if face == "N" else ny - 1
            normal = D / ny
        else:
            j = min(ny - 1, int(mid / (D / ny)))
            i = nx - 1 if face == "E" else 0
            normal = W / nx
        base_links.append((j * nx + i, wi, row["width"], normal, row["dz"]))
    P = sum(q[2] for q in base_links)
    assert abs(P - 2 * (W + D)) < 1e-8
    partitions = {
        "N": Polygon([(0, 0), (W, 0), (W - D / 2, D / 2), (D / 2, D / 2)]),
        "E": Polygon([(W, 0), (W, D), (W - D / 2, D / 2)]),
        "S": Polygon([(0, D), (D / 2, D / 2), (W - D / 2, D / 2), (W, D)]),
        "W": Polygon([(0, 0), (D / 2, D / 2), (0, D)]),
    }
    top_links = []
    contact_area = 0
    for face, part in partitions.items():
        cp = contact.intersection(part)
        se = wedges[face]
        for s in range(len(se) - 1):
            strip = box(se[s], 0, se[s + 1], D) if face in ["N", "S"] else box(0, se[s], W, se[s + 1])
            patch = cp.intersection(strip)
            if patch.is_empty or patch.area < 1e-10:
                continue
            wi = index[face, s, len(ze) - 2]
            for li in tree.query(patch, predicate="intersects"):
                li = int(li)
                p = patch.intersection(polys[li])
                A = p.area
                if A <= 1e-10:
                    continue
                x, y = p.centroid.x, p.centroid.y
                cx, cy = centres[li]
                normal = {"N": y, "S": D - y, "W": x, "E": W - x}[face]
                inplane = abs(cy - y) if face in ["N", "S"] else abs(cx - x)
                top_links.append((wi, li, A, normal, inplane))
                contact_area += A
    assert abs(contact_area - contact.area) < 1e-5, (contact_area, contact.area)
    actualwall = sum(q["width"] * q["dz"] for q in wall)
    expectedwall = 2 * (W + D) * H - 282 * 27.2 - 9 * 3 * 8
    assert abs(actualwall - expectedwall) < 1e-7
    metadata = dict(
        grid=list(grid),
        native_lid_metal_area_mm2=panel.area,
        cell_component_metal_area_mm2=sum(areas) * 1e6,
        lid_components=len(polys),
        lid_sheet_graph_components=int(lid_components),
        no_link_between_separate_same_cell_components=True,
        lid_nodes_with_multiple_components=sum(len(q) > 1 for q in cells.values()),
        actual_fin_vertical_area_m2=rawvertical,
        distributed_fin_vertical_area_m2=float(finareas.sum()),
        actual_fin_root_overlap_m2=sum(rootareas),
        contact_area_mm2=contact_area,
        base_contact_length_mm=P,
        wall_nodes=len(wall),
        wall_remaining_area_mm2=actualwall,
        wall_removed_area_mm2=282 * 27.2 + 9 * 3 * 8,
        rear_cassette_bridge_credited=False,
        fin_radiation_extra_credit=False,
        all_apertures_retained=True,
        all_separate_cell_metal_components_separate_nodes=True,
        wall_cut_boundaries_aligned=True,
    )
    return dict(
        lid_polys=polys,
        lid_neighbors=neighbors,
        lid_centres=centres,
        lid_areas=np.array(areas),
        lid_exposed=np.array(topareas),
        lid_roots=np.array(rootareas),
        lid_fin=finareas,
        wall=wall,
        wall_neighbors=wall_neighbors,
        base_links=base_links,
        top_links=top_links,
        metadata=metadata,
    )
