"""Source-bound simultaneous current/energy diagnostic for the actual 5V copper."""

import hashlib
import json
from pathlib import Path

import numpy as np
from mesh import Mesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve

from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent


def run():
    pcb = ROOT / "generated/filled.kicad_pcb"
    pads = json.loads((ROOT / "generated/pads.json").read_text())
    m = Mesh(read_sexpr(pcb.read_text()), pads, "5V_DIG", 0.1)
    n = m.network([0.035] * 4, [0.0175, 0.2525, 1.3475, 1.5825], temp=100)
    u, v, g, count = [n[k] for k in ["u", "v", "g", "n"]]
    source = n["electrode"]("J1.1", "B.Cu")
    loads = {"R1.1": 1.0, "J11.2": 0.764}
    rhs = np.zeros(count)
    for ref, current in loads.items():
        ns = n["electrode"](ref, "F.Cu")
        rhs[ns] += current / len(ns)
    rhs[source] -= sum(loads.values()) / len(source)
    _, labels = connected_components(
        coo_matrix((np.ones(2 * len(u)), (np.r_[u, v], np.r_[v, u])), shape=(count, count)).tocsr(),
        directed=False,
    )
    active = labels == labels[source[0]]
    active[source[0]] = False
    indices = np.flatnonzero(active)
    index = np.full(count, -1)
    index[indices] = np.arange(len(indices))
    degree = np.bincount(u, weights=g, minlength=count) + np.bincount(v, weights=g, minlength=count)
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
    volt = np.zeros(count)
    volt[indices] = spsolve(matrix, rhs[indices], permc_spec="MMD_AT_PLUS_A", use_umfpack=False)
    res = (
        degree * volt
        - np.bincount(u, weights=g * volt[v], minlength=count)
        - np.bincount(v, weights=g * volt[u], minlength=count)
        - rhs
    )
    assert abs(res).max() < 1e-7
    sourcevoltage = volt[source].mean()
    loss = g * (volt[u] - volt[v]) ** 2
    pos = np.argwhere(m.mask)
    x = m.x[pos[:, 1]]
    y = m.y[pos[:, 2]]
    mx = (x[u] + x[v]) / 2
    my = (y[u] + y[v]) / 2
    hist, xe, ye = np.histogram2d(mx, my, bins=[np.arange(110, 151, 2), np.arange(102, 126, 2)], weights=loss)
    tiles = []
    for i, j in zip(*np.nonzero(hist)):
        tiles.append(
            dict(
                native_bbox_mm=[float(xe[i]), float(ye[j]), float(xe[i + 1]), float(ye[j + 1])],
                dissipation_w=float(hist[i, j]),
            )
        )
    port_power = sum(
        current * (volt[n["electrode"](ref, "F.Cu")].mean() - sourcevoltage) for ref, current in loads.items()
    )
    assert np.isclose(loss.sum(), port_power, rtol=1e-7)
    report = dict(
        source_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        loads_a=loads,
        grid_mm=0.1,
        copper_mm=0.035,
        temperature_c=100,
        all_5v_copper_dissipation_w=float(loss.sum()),
        terminal_power_identity_w=float(port_power),
        maximum_kcl_residual_a=float(abs(res).max()),
        highest_local_energy_tiles=sorted(tiles, key=lambda t: t["dissipation_w"], reverse=True)[:20],
        physical_qualified=False,
    )
    (ROOT / "generated/5v-energy-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    run()
