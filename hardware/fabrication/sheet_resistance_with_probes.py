"""DC sheet-resistance screen on a square finite-volume resistor grid.

Uniform isotropic sheet, unit ohms/square, ideal equipotential contacts.
Cells are conservatively selected inside the supplied polygon, but discretized
ports prevent interpreting the answer as a rigorous resistance upper bound.
Optional regional probes report face-normal sheet current and regional dissipation.
No thickness, via-barrel, temperature-rise or current-rating model is implied.
"""
import math

import numpy as np
from scipy.ndimage import label
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from shapely import contains_xy


def solve_sheet(copper, source_ports, sink_ports, step_mm, origin_mm=(0., 0.), probe_regions=None):
    """Return dimensionless squares and per-port fractions of terminal current.

Ports map names to physical contact polygons. Disconnected copper that touches
at most one terminal has zero DC current and is omitted from the linear solve.
Each retained nearest-neighbour cell edge has one ohm resistance; shared edge
length and node spacing both equal step_mm. Contacts clamp nodes to 1 V/0 V.
"""
    if step_mm <= 0 or copper.is_empty or not source_ports or not sink_ports:
        raise ValueError('Positive step, copper and both terminal port sets are required')
    if set(source_ports) & set(sink_ports):
        raise ValueError('Port names must be unique across terminals')
    h = step_mm
    x0, y0, x1, y1 = copper.bounds
    ox, oy = origin_mm
    xs = ox+(np.arange(math.floor((x0-ox)/h), math.ceil((x1-ox)/h))+.5)*h
    ys = oy+(np.arange(math.floor((y0-oy)/h), math.ceil((y1-oy)/h))+.5)*h
    xx, yy = np.meshgrid(xs, ys)
    # The centre's circumscribed cell disc must fit; entire retained cells
    # therefore lie within copper. This intentionally shrinks raster boundaries.
    domain = contains_xy(copper.buffer(-h/math.sqrt(2)), xx, yy)
    port_masks = {name: domain & contains_xy(poly, xx, yy)
                  for name, poly in (source_ports | sink_ports).items()}
    if any(not mask.any() for mask in port_masks.values()):
        raise ValueError('At least one port has no mesh nodes; refine the mesh')
    used = np.zeros(domain.shape, dtype=bool)
    for mask in port_masks.values():
        if (mask & used).any():
            raise ValueError('Discretized contact ports overlap')
        used |= mask
    source = np.logical_or.reduce([port_masks[n] for n in source_ports])
    sink = np.logical_or.reduce([port_masks[n] for n in sink_ports])
    components, _ = label(domain)
    common = set(np.unique(components[source])) & set(np.unique(components[sink]))
    common.discard(0)
    if not common:
        raise ValueError('No copper path joins the two terminals')
    active = np.isin(components, list(common))
    ids = np.full(active.shape, -1, dtype=np.int64)
    count = int(active.sum())
    ids[active] = np.arange(count)
    u, v = [], []
    for aa, bb in [(ids[:, :-1], ids[:, 1:]), (ids[:-1, :], ids[1:, :])]:
        ok = (aa >= 0) & (bb >= 0)
        u.append(aa[ok]); v.append(bb[ok])
    u, v = np.concatenate(u), np.concatenate(v)
    degree = np.bincount(np.r_[u, v], minlength=count)
    rows = np.r_[np.arange(count), u, v]
    cols = np.r_[np.arange(count), v, u]
    data = np.r_[degree, -np.ones(2*len(u))]
    laplace = coo_matrix((data, (rows, cols)), shape=(count, count)).tocsr()
    voltage = np.zeros(count)
    voltage[ids[active & source]] = 1.
    fixed = (source | sink)[active]
    free = np.flatnonzero(~fixed)
    rhs = -(laplace @ voltage)[free]
    voltage[free] = spsolve(laplace[free][:, free], rhs)
    current = laplace @ voltage
    source_current = float(current[ids[active & source]].sum())
    sink_current = -float(current[ids[active & sink]].sum())
    energy = float(np.sum((voltage[u]-voltage[v])**2))
    residual = float(np.max(np.abs(current[free]))) if len(free) else 0.
    if not (source_current > 0 and np.isfinite(voltage).all() and
            abs(source_current-sink_current) < 1e-7*source_current and
            abs(source_current-energy) < 1e-7*source_current and residual < 1e-9):
        raise ArithmeticError('KCL or dissipated-energy verification failed')
    if voltage.min() < -1e-8 or voltage.max() > 1+1e-8:
        raise ArithmeticError('Passive network maximum principle failed')
    ports = {}
    for name, mask in port_masks.items():
        terminal_sign = 1 if name in source_ports else -1
        ports[name] = dict(active_nodes=int((mask & active).sum()),
                           fraction=float(terminal_sign*current[ids[mask & active]].sum()/source_current))
    probes = {}
    if probe_regions:
        node_x, node_y = xx[active], yy[active]
        mid_x, mid_y = (node_x[u]+node_x[v])/2, (node_y[u]+node_y[v])/2
        edge_current_per_terminal_amp = np.abs(voltage[u]-voltage[v])/source_current
        horizontal = np.abs(node_x[u]-node_x[v]) > h/2
        for name, region in probe_regions.items():
            selected = contains_xy(region, mid_x, mid_y)
            if not selected.any():
                raise ValueError('Probe region has no conducting mesh edges: '+name)
            flux = edge_current_per_terminal_amp[selected]/h
            probes[name] = dict(conducting_edges=int(selected.sum()),
                maximum_edge_normal_A_per_mm_per_terminal_A=float(flux.max()),
                percentile_95_edge_normal_A_per_mm_per_terminal_A=float(np.percentile(flux,95)),
                maximum_horizontal_A_per_mm_per_terminal_A=float((edge_current_per_terminal_amp[selected & horizontal]/h).max(initial=0)),
                maximum_vertical_A_per_mm_per_terminal_A=float((edge_current_per_terminal_amp[selected & ~horizontal]/h).max(initial=0)),
                regional_dissipation_squares_at_terminal_A1=float(np.sum(edge_current_per_terminal_amp[selected]**2)),
                interpretation='Absolute face-normal sheet current at mesh-edge midpoints; not vector current-density magnitude or a thermal/current rating.')
    return dict(probes=probes, step_mm=h, origin_mm=list(origin_mm), active_nodes=count,
                discarded_zero_current_nodes=int((domain & ~active).sum()),
                mesh_copper_area_mm2=float(domain.sum()*h*h), exact_copper_area_mm2=copper.area,
                resistance_squares=1/source_current, source_current_at_unit_voltage=source_current,
                current_balance_relative_error=abs(source_current-sink_current)/source_current,
                energy_relative_error=abs(source_current-energy)/source_current,
                maximum_interior_KCL_error=residual, ports=ports)
