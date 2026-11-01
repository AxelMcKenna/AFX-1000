"""E19 FOUR-layer finite sheets, native pad shapes and finite cylindrical walls.

Cell-centre raster and nearest-wall-sector attachments are diagnostic approximations.
No E28 layer/material/stack defaults, pad shorts, artificial links or solid vias.
"""

import math

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu

from hardware.electronics.common.sexpr import children, first

LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")
RHO20 = 1.724e-5  # ohm mm, illustrative annealed-Cu material scenario
BARREL_RHO20 = 2.0e-5  # ohm mm, independent plated-Cu material scenario
ALPHA = 0.00393


def netname(obj):
    return str(first(obj, "net")[-1]).lstrip("/") if children(obj, "net") else ""


class Mesh:
    def __init__(self, tree, pads, net, step, phase_mm=(0.025, 0.025)):
        assert step > 0
        self.step = step
        self.phase_mm = phase_mm
        self.net = net
        self.pads = {}
        self.holes = []
        edges = [q for q in children(tree, "gr_line") if first(q, "layer")[1] == "Edge.Cuts"]
        points = [tuple(map(float, first(q, k)[1:3])) for q in edges for k in ("start", "end")]
        assert len(edges) == 6 and len(set(points)) == 6, "Unexpected outline; explicit domain audit required"
        self.bounds = (
            min(x for x, y in points),
            min(y for x, y in points),
            max(x for x, y in points),
            max(y for x, y in points),
        )
        x0, y0, x1, y1 = self.bounds
        self.x = x0 + phase_mm[0] + np.arange(math.ceil((x1 - x0) / step)) * step
        self.y = y0 + phase_mm[1] + np.arange(math.ceil((y1 - y0) / step)) * step
        self.mask = np.zeros((4, len(self.x), len(self.y)), bool)
        self.all_holes = []
        for z in children(tree, "zone"):
            if netname(z) != net:
                continue
            for poly in children(z, "filled_polygon"):
                self.mask[LAYERS.index(first(poly, "layer")[1])] |= self.polygon(
                    [tuple(map(float, p[1:3])) for p in first(poly, "pts")[1:]]
                )
        assert not any(netname(a) == net for a in children(tree, "arc")), (
            "Native copper arc raster not implemented"
        )
        for t in children(tree, "segment"):
            if netname(t) != net:
                continue
            a, b = [tuple(map(float, first(t, k)[1:3])) for k in ("start", "end")]
            self.mask[LAYERS.index(first(t, "layer")[1])] |= self.line(a, b, float(first(t, "width")[1]))
        for pad in pads["pads"]:
            dx, dy = pad["drill_mm"]
            if dx or dy:
                assert abs(dx - dy) < 1e-8, "Slot wall not implemented"
                self.all_holes.append((pad["position_mm"], dx))
            if pad["net"] != net:
                continue
            key = pad["ref"] + "." + pad["pin"]
            terminal = self.pads.setdefault(key, {})
            for layer, polys in pad["layers"].items():
                region = np.zeros(self.mask.shape[1:], bool)
                for p in polys:
                    piece = self.polygon(p["outer"])
                    for hole in p["holes"]:
                        piece &= ~self.polygon(hole)
                    region |= piece
                i = LAYERS.index(layer)
                self.mask[i] |= region
                terminal[i] = terminal.get(i, np.zeros_like(region)) | region
            if dx:
                assert set(pad["layers"]) == set(LAYERS), "Blind plated pad not supported"
                self.holes.append((pad["position_mm"], dx, min(pad["size_mm"]) / 2))
        for via in children(tree, "via"):
            assert first(via, "layers")[1:] == ["F.Cu", "B.Cu"], "Blind via not implemented"
            xy = tuple(map(float, first(via, "at")[1:3]))
            drill = float(first(via, "drill")[1])
            radius = float(first(via, "size")[1]) / 2
            self.all_holes.append((xy, drill))
            if netname(via) == net:
                ring = (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 <= radius**2
                self.mask |= ring[None, :, :]
                self.holes.append((xy, drill, radius))
        for xy, drill in self.all_holes:
            self.mask[:, (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 < drill**2 / 4] = (
                False
            )
        self.shape = self.mask.shape

    def polygon(self, pts):
        pts = np.array(pts, float)
        assert np.isfinite(pts).all()
        assert (
            (pts[:, 0] >= self.bounds[0] - 1e-6).all()
            and (pts[:, 0] <= self.bounds[2] + 1e-6).all()
            and (pts[:, 1] >= self.bounds[1] - 1e-6).all()
            and (pts[:, 1] <= self.bounds[3] + 1e-6).all()
        ), "Native copper clipped by domain"
        result = np.zeros(self.mask.shape[1:], bool)
        ix = np.flatnonzero((self.x >= pts[:, 0].min()) & (self.x <= pts[:, 0].max()))
        iy = np.flatnonzero((self.y >= pts[:, 1].min()) & (self.y <= pts[:, 1].max()))
        if not len(ix) or not len(iy):
            return result
        following = np.roll(pts, -1, axis=0)
        for j in iy:
            y = self.y[j]
            cross = (pts[:, 1] > y) != (following[:, 1] > y)
            a, b = pts[cross], following[cross]
            intersections = np.sort(a[:, 0] + (b[:, 0] - a[:, 0]) * (y - a[:, 1]) / (b[:, 1] - a[:, 1]))
            assert len(intersections) % 2 == 0, "Odd polygon scanline crossing count"
            for left, right in zip(intersections[::2], intersections[1::2]):
                result[(self.x >= left) & (self.x < right), j] = True
        return result

    def line(self, a, b, width):
        assert (
            min(a[0], b[0]) - width / 2 >= self.bounds[0]
            and max(a[0], b[0]) + width / 2 <= self.bounds[2]
            and min(a[1], b[1]) - width / 2 >= self.bounds[1]
            and max(a[1], b[1]) + width / 2 <= self.bounds[3]
        ), "Track copper clipped by domain"
        xx, yy = self.x[:, None], self.y[None, :]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = dx * dx + dy * dy
        t = np.clip(((xx - a[0]) * dx + (yy - a[1]) * dy) / d, 0, 1) if d else 0
        return (xx - a[0] - t * dx) ** 2 + (yy - a[1] - t * dy) ** 2 <= width**2 / 4

    def network(self, copper_mm, centroids_mm, wall_mm=0.025, temp=20, sectors=32):
        assert len(copper_mm) == len(centroids_mm) == 4
        assert all(t > 0 for t in copper_mm) and wall_mm > 0
        count = int(self.mask.sum())
        ids = np.full(self.mask.shape, -1, np.int32)
        ids[self.mask] = np.arange(count)
        us = []
        vs = []
        gs = []
        rho = RHO20 * (1 + ALPHA * (temp - 20))
        barrelrho = BARREL_RHO20 * (1 + ALPHA * (temp - 20))
        maxerror = 0
        for layer in range(4):
            for axis in [0, 1]:
                a, b = (
                    (ids[layer, :-1, :], ids[layer, 1:, :])
                    if axis == 0
                    else (ids[layer, :, :-1], ids[layer, :, 1:])
                )
                good = (a >= 0) & (b >= 0)
                us.append(a[good])
                vs.append(b[good])
                gs.append(np.full(good.sum(), copper_mm[layer] / rho))
        seen = set()
        bu = []
        bv = []
        bg = []
        for xy, drill, radius in self.holes:
            identity = (tuple(xy), drill)
            assert identity not in seen, "Duplicate barrel"
            seen.add(identity)
            ix = np.flatnonzero(abs(self.x - xy[0]) <= radius)
            iy = np.flatnonzero(abs(self.y - xy[1]) <= radius)
            angles = np.arange(sectors) * 2 * math.pi / sectors
            wr = drill / 2 + wall_mm / 2
            targets = np.column_stack((xy[0] + wr * np.cos(angles), xy[1] + wr * np.sin(angles)))
            terms = []
            for layer in range(4):
                xx, yy = np.meshgrid(self.x[ix], self.y[iy], indexing="ij")
                physical = self.mask[layer][np.ix_(ix, iy)] & (
                    (xx - xy[0]) ** 2 + (yy - xy[1]) ** 2 <= radius**2
                )
                cx, cy = np.nonzero(physical)
                assert len(cx), f"Unresolved {self.net} barrel annulus {xy}, layer{layer}; refine grid"
                pos = np.column_stack((self.x[ix[cx]], self.y[iy[cy]]))
                dist = ((targets[:, None, :] - pos[None, :, :]) ** 2).sum(axis=2)
                near = dist.argmin(axis=1)
                maxerror = max(maxerror, float(np.sqrt(dist[np.arange(sectors), near]).max()))
                terms.append(ids[layer, ix[cx[near]], iy[cy[near]]])
            area = math.pi * ((drill / 2 + wall_mm) ** 2 - (drill / 2) ** 2)
            lengths = np.diff(centroids_mm)
            heights = np.r_[lengths[0] / 2, (lengths[:-1] + lengths[1:]) / 2, lengths[-1] / 2]
            for layer, length in enumerate(lengths):
                bu.extend(terms[layer])
                bv.extend(terms[layer + 1])
                bg.extend([area / sectors / (barrelrho * length)] * sectors)
            for layer, height in enumerate(heights):
                a, b = terms[layer], np.roll(terms[layer], -1)
                good = a != b
                bu.extend(a[good])
                bv.extend(b[good])
                bg.extend([wall_mm * height / (barrelrho * wr * 2 * math.pi / sectors)] * int(good.sum()))
        if bu:
            us.append(np.array(bu))
            vs.append(np.array(bv))
            gs.append(np.array(bg))
        u, v, g = np.concatenate(us), np.concatenate(vs), np.concatenate(gs)

        def electrode(ref, face):
            assert face in LAYERS
            assert ref in self.pads, f"Missing native pad {ref}"
            layer = LAYERS.index(face)
            assert layer in self.pads[ref], f"{ref} absent on {face}"
            nodes = ids[layer][self.pads[ref][layer] & self.mask[layer]]
            assert len(nodes), f"Unresolved electrode {ref}"
            return nodes

        return dict(
            u=u,
            v=v,
            g=g,
            n=count,
            electrode=electrode,
            finite_holes=len(seen),
            maximum_wall_attachment_displacement_mm=maxerror,
            copper_area_per_layer_mm2={
                l: float(self.mask[i].sum() * self.step**2) for i, l in enumerate(LAYERS)
            },
        )


def response(network, source, drives, measures):
    """Uniform finite-face current electrodes; no equipotential pad/via shorts."""
    u, v, g, n = (network[k] for k in ["u", "v", "g", "n"])
    adj = coo_matrix((np.ones(len(u) * 2), (np.r_[u, v], np.r_[v, u])), shape=(n, n)).tocsr()
    _, labels = connected_components(adj, directed=False)
    src = network["electrode"](*source)
    labels0 = np.unique(labels[src])
    assert len(labels0) == 1, "Source electrode crosses disconnected components"
    active = labels == labels0[0]
    anchor = int(src[0])
    active[anchor] = False
    indices = np.flatnonzero(active)
    index = np.full(n, -1, int)
    index[indices] = np.arange(len(indices))
    degree = np.bincount(u, weights=g, minlength=n) + np.bincount(v, weights=g, minlength=n)
    good = active[u] & active[v]
    matrix = coo_matrix(
        (
            np.r_[degree[indices], -g[good], -g[good]],
            (
                np.r_[np.arange(len(indices)), index[u[good]], index[v[good]]],
                np.r_[np.arange(len(indices)), index[v[good]], index[u[good]]],
            ),
        ),
        shape=(len(indices), len(indices)),
    ).tocsc()
    lu = splu(matrix, permc_spec="MMD_AT_PLUS_A")
    columns = {}
    residuals = []
    measure_nodes = {key: network["electrode"](*p) for key, p in measures.items()}
    assert all((labels[ns] == labels0[0]).all() for ns in measure_nodes.values()), (
        "Measured pad is disconnected"
    )
    for name, pad in drives.items():
        ns = network["electrode"](*pad)
        assert (labels[ns] == labels0[0]).all(), f"Drive {name} disconnected"
        rhs = np.zeros(n)
        rhs[ns] += 1 / len(ns)
        rhs[src] -= 1 / len(src)
        voltage = np.zeros(n)
        voltage[indices] = lu.solve(rhs[indices])
        current = (
            degree * voltage
            - np.bincount(u, weights=g * voltage[v], minlength=n)
            - np.bincount(v, weights=g * voltage[u], minlength=n)
        )
        res = float(abs(current - rhs).max())
        assert res < 1e-7, (name, res)
        residuals.append(res)
        columns[name] = {
            key: float(voltage[m].mean() - voltage[src].mean()) for key, m in measure_nodes.items()
        }
    for a in drives:
        for b in drives:
            if a in measures and b in measures:
                assert math.isclose(columns[a][b], columns[b][a], abs_tol=1e-8), "Reciprocity failed"
    return dict(
        transfer_resistance_ohm=columns,
        max_absolute_kcl_residual_a=max(residuals),
        nodes=n,
        edges=len(u),
        resolved_component_nodes=len(indices) + 1,
        unexcited_floating_nodes=n - len(indices) - 1,
        source_face=source,
        drive_faces=drives,
        measure_faces=measures,
        uniform_face_current_injection=True,
        equipotential_pad_or_via_short_used=False,
    )
