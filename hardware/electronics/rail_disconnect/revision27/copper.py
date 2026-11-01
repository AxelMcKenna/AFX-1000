"""Diagnostic sheet-resistance mesh of native filled copper; not qualification."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import transform

ROOT = Path(__file__).resolve().parent
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
RHO20 = 1.724e-5  # ohm mm
ALPHA = 0.00393


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


def solve_network(u, v, g, n, source, sink):
    """Unit-voltage conductance solution, including finite barrel conductance."""
    connected = Union(n)
    for a, b in zip(u, v):
        connected.join(int(a), int(b))
    source = np.unique(source)
    sink = np.unique(sink)
    if not len(source) or not len(sink):
        return dict(status="electrode_not_resolved")
    if not any(connected.root(int(a)) == connected.root(int(b)) for a in source for b in sink):
        return dict(status="mesh_disconnected")
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

    free = ~boundary & (degree > 0)
    b = -matrix(voltage)
    b[~free] = 0
    correction = np.zeros(n)
    residual = b.copy()
    z = np.divide(residual, degree, out=np.zeros(n), where=free)
    p = z.copy()
    rz = float(residual @ z)
    iterations = 0
    for iterations in range(1, 5001):
        ap = matrix(p)
        ap[~free] = 0
        den = float(p @ ap)
        if den <= 0:
            break
        scale = rz / den
        correction += scale * p
        residual -= scale * ap
        if np.linalg.norm(residual) <= max(1e-11, np.linalg.norm(b) * 1e-9):
            break
        z = np.divide(residual, degree, out=np.zeros(n), where=free)
        new = float(residual @ z)
        p = z + (new / rz) * p
        rz = new
    voltage += correction
    current = float(np.sum(matrix(voltage)[source]))
    relative = float(np.linalg.norm(residual) / max(np.linalg.norm(b), 1e-30))
    if current <= 0 or relative > 1e-7:
        return dict(status="solver_not_converged", relative_residual=relative, iterations=iterations)
    return dict(
        status="diagnostic_estimate",
        ohm=1 / current,
        iterations=iterations,
        relative_residual=relative,
        nodes=n,
        edges=len(u),
    )


class Mesh:
    def __init__(self, tree, net, step):
        self.step = step
        self.net = net
        self.x = (np.arange(math.ceil(156 / step)) + 0.5) * step
        self.y = (np.arange(math.ceil(45.25 / step)) + 0.5) * step
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
                for layer in layers:
                    self.mask[layer] |= region
                self.pads[(ref, str(pad[1]))] = (tuple(layers), region)
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

    def resistance(self, source, target, thickness=0.07, temp=85, plating=0.025):
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
                # Layer depths are an explicit placeholder because the board has
                # no defined dielectric stackup; never treat this as qualification.
                length = (lb - la) * 1.6 / 5
                area = math.pi * ((drill / 2 + plating) ** 2 - (drill / 2) ** 2)
                uu.append(mapping[a])
                vv.append(mapping[b])
                gg.append(area / (rho * length))

        def electrodes(pairs):
            allids = []
            for ref, pin in pairs:
                layers, region = self.pads[(ref, str(pin))]
                for layer in layers:
                    p = ids[layer][region & self.mask[layer]]
                    allids.extend(mapping[p])
            return np.array(allids, dtype=int)

        return solve_network(
            np.asarray(uu, dtype=int),
            np.asarray(vv, dtype=int),
            np.asarray(gg),
            n,
            electrodes(source),
            electrodes(target),
        )


def analyze(board, steps=(0.2, 0.1)):
    tree = read_sexpr(board.read_text())
    cases = [
        ("digital_source", "5V_DIG_SRC", [("J2", "1")], [("Q11", "3"), ("Q13", "3")]),
        ("digital_common", "5V_DIG_COMMON", [("Q11", "1"), ("Q13", "1")], [("Q12", "1"), ("Q14", "1")]),
        ("digital_output", "5V_DIG", [("Q12", "3"), ("Q14", "3")], [("J4", "1")]),
        ("analog_source", "V5_REG_SRC", [("J1", "6")], [("Q9", "3")]),
        ("analog_common", "V5_REG_COMMON", [("Q9", "1")], [("Q10", "1")]),
        ("analog_output", "V5_REG", [("Q10", "3")], [("J3", "6")]),
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
    for domain in ("analog", "digital"):
        rows = []
        for i, step in enumerate(steps):
            values = [result[domain + "_" + part][i] for part in ("source", "common", "output")]
            if all(v["status"] == "diagnostic_estimate" for v in values):
                resistance = sum(v["ohm"] for v in values)
                rows.append(
                    dict(
                        grid_mm=step,
                        positive_path_ohm=resistance,
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
        parallel_switch_terminals_forced_equipotential=True,
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
            "Parallel switch terminal groups are equipotential electrodes, not a bound on unequal/diagonal branch currents",
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
            ("analog_header_return", ("J1", "2"), ("J3", "2")),
            ("digital_header_return", ("J2", "2"), ("J4", "2")),
            ("protected_star_pair_resistance", ("J3", "2"), ("J4", "2")),
        ]:
            row = mesh.resistance([a], [b])
            row["grid_mm"] = step
            rows.setdefault(name, []).append(row)
            print(name, row, flush=True)
    return dict(
        board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        paths=rows,
        real_attachment_lands_present=False,
        full_strap_resistance_qualified=False,
        common_ground_transfer_qualified=False,
        scope="Same diagnostic assumptions as copper.py; existing header pair resistance only, not unimplemented stud contacts or multiport transfer impedance",
        build_ready=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", default=".2,.1")
    p.add_argument("--returns", action="store_true")
    a = p.parse_args()
    board = ROOT / "generated/filled.kicad_pcb"
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
