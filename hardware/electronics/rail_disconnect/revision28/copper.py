"""Diagnostic sheet-resistance mesh of native filled copper; not qualification."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import transform
from .generate import STACKUP

ROOT = Path(__file__).resolve().parent
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
RHO20 = STACKUP["trace_resistivity_max_20c_ohm_m"] * 1000  # ohm mm, unaccepted process requirement
RHO_BARREL20 = STACKUP["barrel_resistivity_max_20c_ohm_m"] * 1000
ALPHA = STACKUP["temperature_coefficient_max_per_c"]


class Union:
    def __init__(self, n):
        self.parent = list(range(n))

    def root(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def join(self, a, b):
        self.parent[self.root(a)] = self.root(b)


def solve_network(u, v, g, n, source, sink, details=False):
    """Residual-checked unit-voltage network solve, including finite barrels.

    SciPy's sparse LU is used when available; the NumPy PCG fallback remains
    explicit in the receipt. Floating unexcited components are excluded from
    the free-node system, rather than treating a singular solve as convergence.
    """
    connected = Union(n)
    for a, b in zip(u, v):
        connected.join(int(a), int(b))
    source = np.unique(source)
    sink = np.unique(sink)
    if not len(source) or not len(sink):
        return dict(status="electrode_not_resolved")
    source_roots = {connected.root(int(a)) for a in source}
    sink_roots = {connected.root(int(a)) for a in sink}
    if not source_roots & sink_roots:
        return dict(status="mesh_disconnected")
    if np.intersect1d(source, sink).size:
        return dict(status="overlapping_source_sink_electrodes")
    boundary = np.zeros(n, dtype=bool)
    boundary[source] = True
    boundary[sink] = True
    voltage = np.zeros(n)
    voltage[source] = 1
    degree = np.bincount(u, weights=g, minlength=n) + np.bincount(v, weights=g, minlength=n)

    def matrix(x):
        return (
            degree * x
            - np.bincount(u, weights=g * x[v], minlength=n)
            - np.bincount(v, weights=g * x[u], minlength=n)
        )

    boundary_roots = source_roots | sink_roots
    excited = np.fromiter((connected.root(i) in boundary_roots for i in range(n)), dtype=bool, count=n)
    free = ~boundary & (degree > 0) & excited
    rhs = -matrix(voltage)
    rhs[~free] = 0
    indices = np.flatnonzero(free)
    iterations = 0
    solver = "boundary_only"
    solver_version = None
    try:
        import scipy
        from scipy.sparse import coo_matrix
        from scipy.sparse.linalg import spsolve
    except ImportError:
        scipy = None
    if len(indices) and scipy is not None:
        index = np.full(n, -1, dtype=int)
        index[indices] = np.arange(len(indices))
        both = free[u] & free[v]
        row = np.concatenate((np.arange(len(indices)), index[u[both]], index[v[both]]))
        col = np.concatenate((np.arange(len(indices)), index[v[both]], index[u[both]]))
        data = np.concatenate((degree[indices], -g[both], -g[both]))
        sparse = coo_matrix((data, (row, col)), shape=(len(indices), len(indices))).tocsc()
        voltage[indices] += spsolve(sparse, rhs[indices], permc_spec="MMD_AT_PLUS_A", use_umfpack=False)
        solver = "scipy.sparse.linalg.spsolve/SuperLU"
        solver_version = scipy.__version__
    elif len(indices):
        solver = "numpy_jacobi_pcg"
        correction = np.zeros(n)
        residual = rhs.copy()
        z = np.divide(residual, degree, out=np.zeros(n), where=free)
        direction = z.copy()
        rz = float(residual @ z)
        for iterations in range(1, 20001):
            ap = matrix(direction)
            ap[~free] = 0
            den = float(direction @ ap)
            if den <= 0:
                break
            scale = rz / den
            correction += scale * direction
            residual -= scale * ap
            if np.linalg.norm(residual) <= max(1e-11, np.linalg.norm(rhs) * 1e-9):
                break
            z = np.divide(residual, degree, out=np.zeros(n), where=free)
            new = float(residual @ z)
            direction = z + (new / rz) * direction
            rz = new
        voltage += correction
    residual = matrix(voltage)
    residual[~free] = 0
    current = float(np.sum(matrix(voltage)[source]))
    relative = float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1e-30))
    metadata = dict(
        solver=solver,
        solver_version=solver_version,
        iterations=iterations,
        relative_residual=relative,
        excited_free_nodes=len(indices),
        floating_unexcited_nodes=int(np.count_nonzero(~excited)),
    )
    if not np.isfinite(current) or current <= 0 or not np.isfinite(relative) or relative > 1e-7:
        return dict(status="solver_not_converged", **metadata)
    result = dict(status="diagnostic_estimate", ohm=1 / current, nodes=n, edges=len(u), **metadata)
    if details:
        result["voltage"] = voltage
        result["current_at_one_volt"] = current
    return result


class Mesh:
    def __init__(self, tree, net, step, bounds=(156, 45.25)):
        assert step > 0 and len(bounds) == 2 and all(value > 0 for value in bounds)
        self.step = step
        self.net = net
        self.x = (np.arange(math.ceil(bounds[0] / step)) + 0.5) * step
        self.y = (np.arange(math.ceil(bounds[1] / step)) + 0.5) * step
        self.mask = np.zeros((6, len(self.x), len(self.y)), dtype=bool)
        self.holes = []
        self.pads = {}

        def netname(node):
            return str(first(node, "net")[-1]).lstrip("/") if children(node, "net") else ""

        for zone in children(tree, "zone"):
            if netname(zone) != net:
                continue
            for poly in children(zone, "filled_polygon"):
                pts = [(float(p[1]) - 100, float(p[2]) - 100) for p in first(poly, "pts")[1:]]
                layer = LAYERS.index(str(first(poly, "layer")[1]))
                self.polygon(layer, pts)
        for track in children(tree, "segment"):
            if netname(track) != net:
                continue
            a = tuple(float(v) - 100 for v in first(track, "start")[1:3])
            b = tuple(float(v) - 100 for v in first(track, "end")[1:3])
            width = float(first(track, "width")[1])
            layer = LAYERS.index(str(first(track, "layer")[1]))
            self.line(layer, a, b, width)
        for fp in children(tree, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            angle = float(first(fp, "at")[3]) if len(first(fp, "at")) > 3 else 0
            for pad in children(fp, "pad"):
                if netname(pad) != net:
                    continue
                xy = tuple(v - 100 for v in transform(fp, first(pad, "at")[1:3]))
                size = tuple(map(float, first(pad, "size")[1:3]))
                size = size[::-1] if int(angle) % 180 else size
                ls = first(pad, "layers")[1:]
                layers = range(6) if "*.Cu" in ls else [i for i, l in enumerate(LAYERS) if l in ls]
                region = (abs(self.x[:, None] - xy[0]) <= size[0] / 2) & (
                    abs(self.y[None, :] - xy[1]) <= size[1] / 2
                )
                if pad[3] == "circle":
                    region = (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 <= (
                        size[0] / 2
                    ) ** 2
                elif pad[3] == "custom":
                    # E28 terminal annulus: use its actual circular primitive,
                    # never the tiny anchor or an ideal solid-pad electrode.
                    assert int(angle) % 360 == 0, "Custom-pad rotation not implemented"
                    primitive = first(first(pad, "primitives"), "gr_circle")
                    center = tuple(map(float, first(primitive, "center")[1:3]))
                    end = tuple(map(float, first(primitive, "end")[1:3]))
                    radius = math.dist(center, end)
                    halfwidth = float(first(primitive, "width")[1]) / 2
                    d2 = (self.x[:, None] - xy[0] - center[0]) ** 2 + (
                        self.y[None, :] - xy[1] - center[1]
                    ) ** 2
                    region = (d2 <= (radius + halfwidth) ** 2) & (d2 >= (radius - halfwidth) ** 2)
                for layer in layers:
                    self.mask[layer] |= region
                    terminal = self.pads.setdefault((ref, str(pad[1])), {})
                    if layer not in terminal:
                        terminal[layer] = region.copy()
                    else:
                        terminal[layer] |= region
                if children(pad, "drill"):
                    drill = float(first(pad, "drill")[1])
                    self.holes.append((xy, drill, min(size) / 2))
        for via in children(tree, "via"):
            if netname(via) != net:
                continue
            xy = tuple(float(v) - 100 for v in first(via, "at")[1:3])
            size = float(first(via, "size")[1])
            drill = float(first(via, "drill")[1])
            circle = (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 <= size * size / 4
            self.mask |= circle
            self.holes.append((xy, drill, size / 2))
        for xy, drill, _ in self.holes:
            circle = (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 < drill * drill / 4
            self.mask[:, circle] = False

    def polygon(self, layer, pts):
        if not pts:
            return
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        ix = np.flatnonzero((self.x >= x0) & (self.x <= x1))
        iy = np.flatnonzero((self.y >= y0) & (self.y <= y1))
        if not len(ix) or not len(iy):
            return
        x = self.x[ix, None]
        y = self.y[None, iy]
        inside = np.zeros((len(ix), len(iy)), dtype=bool)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if abs(a[1] - b[1]) > 1e-12:
                inside ^= ((a[1] > y) != (b[1] > y)) & (x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0])
        self.mask[layer][np.ix_(ix, iy)] |= inside

    def line(self, layer, a, b, width):
        radius = width / 2
        ix = np.flatnonzero((self.x >= min(a[0], b[0]) - radius) & (self.x <= max(a[0], b[0]) + radius))
        iy = np.flatnonzero((self.y >= min(a[1], b[1]) - radius) & (self.y <= max(a[1], b[1]) + radius))
        if not len(ix) or not len(iy):
            return
        x = self.x[ix, None]
        y = self.y[None, iy]
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = dx * dx + dy * dy
        t = np.clip(((x - a[0]) * dx + (y - a[1]) * dy) / length, 0, 1) if length else 0
        self.mask[layer][np.ix_(ix, iy)] |= (x - a[0] - t * dx) ** 2 + (
            y - a[1] - t * dy
        ) ** 2 <= radius * radius

    def network(self, thickness=0.07, temp=85, plating=0.025):
        ids = np.full(self.mask.shape, -1, dtype=int)
        ids[self.mask] = np.arange(np.count_nonzero(self.mask))
        n = int(np.count_nonzero(self.mask))
        rings = []
        union = Union(n)
        for xy, drill, radius in self.holes:
            circle = (self.x[:, None] - xy[0]) ** 2 + (self.y[None, :] - xy[1]) ** 2 <= radius * radius
            rows = []
            for layer in range(6):
                cells = ids[layer][circle & self.mask[layer]]
                if len(cells):
                    for i in cells[1:]:
                        union.join(int(cells[0]), int(i))
                    rows.append((layer, int(cells[0])))
            rings.append((drill, rows))
        representatives = np.array([union.root(i) for i in range(n)])
        _, mapping = np.unique(representatives, return_inverse=True)
        n = int(mapping.max() + 1) if len(mapping) else 0
        uu = []
        vv = []
        gg = []
        rho = RHO20 * (1 + ALPHA * (temp - 20))
        sheet = thickness / rho
        for axis in (1, 2):
            one = [slice(None)] * 3
            two = [slice(None)] * 3
            one[axis] = slice(None, -1)
            two[axis] = slice(1, None)
            a, b = ids[tuple(one)], ids[tuple(two)]
            valid = (a >= 0) & (b >= 0)
            u = mapping[a[valid]]
            v = mapping[b[valid]]
            keep = u != v
            uu.extend(u[keep])
            vv.extend(v[keep])
            gg.extend([sheet] * int(keep.sum()))
        for drill, rows in rings:
            for (la, a), (lb, b) in zip(rows, rows[1:]):
                # Conservative maximum layer separation scales the declared
                # candidate stackup to its maximum laminate thickness. Fabricator
                # acceptance and process coupons remain required.
                depths = STACKUP["copper_center_nominal_depth_mm"]
                length = (
                    (depths[lb] - depths[la])
                    * STACKUP["laminate_thickness_mm"]["maximum"]
                    / STACKUP["laminate_thickness_mm"]["nominal"]
                )
                area = math.pi * ((drill / 2 + plating) ** 2 - (drill / 2) ** 2)
                uu.append(mapping[a])
                vv.append(mapping[b])
                barrel_rho = RHO_BARREL20 * (1 + ALPHA * (temp - 20))
                gg.append(area / (barrel_rho * length))

        def electrodes(pairs):
            allids = []
            for ref, pin in pairs:
                for layer, region in self.pads[(ref, str(pin))].items():
                    p = ids[layer][region & self.mask[layer]]
                    allids.extend(mapping[p])
            return np.array(allids, dtype=int)

        return dict(
            u=np.asarray(uu, dtype=int),
            v=np.asarray(vv, dtype=int),
            g=np.asarray(gg),
            n=n,
            electrodes=electrodes,
        )

    def resistance(self, source, target, thickness=0.07, temp=85, plating=0.025):
        network = self.network(thickness, temp, plating)
        return solve_network(
            network["u"],
            network["v"],
            network["g"],
            network["n"],
            network["electrodes"](source),
            network["electrodes"](target),
        )


def analyze(board, steps=(0.2, 0.1)):
    tree = read_sexpr(board.read_text())
    cases = []
    for domain, refs, netin, netout, source, load in (
        ("analog", ("U13", "U14", "U32"), "V5_REG_SRC", "V5_REG", ("J10", "1"), ("J3", "6")),
        ("digital", ("U15", "U16", "U17", "U33"), "5V_DIG_SRC", "5V_DIG", ("J11", "1"), ("J4", "1")),
    ):
        for ref in refs:
            cases += [
                (domain + "_" + ref + "_input", netin, [source], [(ref, "5"), (ref, "12")]),
                (domain + "_" + ref + "_output", netout, [(ref, "6"), (ref, "11")], [load]),
            ]

    result = {}
    for label, net, source, target in cases:
        result[label] = []
        for step in steps:
            mesh = Mesh(tree, net, step)
            row = mesh.resistance(source, target)
            row["grid_mm"] = step
            row["source_terminals"] = source
            row["target_terminals"] = target
            result[label].append(row)
            print(label, step, row, flush=True)
    sums = {}
    for domain, refs in (("analog", ("U13", "U14", "U32")), ("digital", ("U15", "U16", "U17", "U33"))):
        rows = []
        for ref in refs:
            for i, step in enumerate(steps):
                values = [result[domain + "_" + ref + "_" + side][i] for side in ("input", "output")]
                if all(v["status"] == "diagnostic_estimate" for v in values):
                    resistance = sum(v["ohm"] for v in values)
                    rows.append(
                        dict(
                            ref=ref,
                            grid_mm=step,
                            board_path_estimate_ohm=resistance,
                            p02_allocation_ohm=0.003,
                            estimate_exceeds_allocation=resistance > 0.003,
                            qualified=False,
                        )
                    )
        sums[domain] = rows

    return dict(
        numpy_version=np.__version__,
        positive_path_sums=sums,
        geometry_diagnostic_completed=True,
        parallel_switch_terminals_forced_equipotential=False,
        worst_diagonal_current_sharing_qualified=False,
        board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        copper_thickness_mm_assumption=0.07,
        plating_mm_assumption=0.025,
        copper_temperature_c_assumption=85,
        dielectric_stackup_defined=bool(children(first(tree, "setup"), "stackup")),
        reference_plane_depths_qualified=False,
        method="Cell-center finite-volume sheet mesh of native filled polygons, actual tracks/lands, finite cylindrical via barrels; ideal within-layer plated annuli and terminal contacts",
        limitations=[
            "Cell-center discretization is diagnostic, not a certified resistance bound",
            "Rounded land shapes are rectangularized; within-layer annuli are ideal conductors",
            "Each single-chip IN5/12 and OUT6/11 terminal pair is treated as an equipotential electrode; different parallel chips are never shorted into a common electrode. These individual branch path estimates are not a coupled sharing proof",
            "No manufacturing stackup, copper/plating tolerance or solder/contact spreading qualification",
            "No electromagnetic frequency/noise/thermal extraction; MOSFET channels excluded",
            "Finite mesh requires convergence and native connectivity independently; do not replace failed native checks with this model",
        ],
        paths=result,
        actual_copper_extraction_completed=False,
        copper_loss_qualified=False,
        build_ready=False,
    )


def analyze_returns(board, steps=(0.4, 0.2)):
    tree = read_sexpr(board.read_text())
    rows = {}
    for step in steps:
        mesh = Mesh(tree, "AGND", step)
        for name, a, b in [
            ("analog_force_return", ("J3", "2"), ("J7", "1")),
            ("digital_force_return", ("J4", "2"), ("J8", "1")),
            ("protected_star_pair_resistance", ("J3", "2"), ("J4", "2")),
        ]:
            row = mesh.resistance([a], [b])
            row["grid_mm"] = step
            rows.setdefault(name, []).append(row)
            print(name, row, flush=True)
    return dict(
        board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        paths=rows,
        real_attachment_lands_present=True,
        full_strap_resistance_qualified=False,
        common_ground_transfer_qualified=False,
        scope="Same diagnostic assumptions as copper.py; actual implemented stud/force-pad pair resistance; contact spreading and full bar/contact resistance are not certified by this sheet model",
        build_ready=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", default=".2,.1")
    p.add_argument("--returns", action="store_true")
    p.add_argument("--board", type=Path, default=ROOT / "generated/filled-latest.kicad_pcb")
    a = p.parse_args()
    board = a.board
    report = analyze_returns(board) if a.returns else analyze(board, tuple(map(float, a.steps.split(","))))
    repo = ROOT.parents[3]
    report["source_sha256"] = {
        str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            Path(__file__),
            board,
            repo / "hardware/electronics/common/sexpr.py",
            repo / "hardware/electronics/output_stage/check_placement.py",
        ]
    }
    (
        ROOT / ("generated/return-diagnostic.json" if a.returns else "generated/copper-diagnostic.json")
    ).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
