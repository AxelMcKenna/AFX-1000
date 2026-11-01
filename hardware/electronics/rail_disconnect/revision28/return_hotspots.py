"""Diagnostic spatial Joule-loss attribution for the actual J4 to J8 return.

No resistance bound, current density, temperature or ampacity proof follows.
The shared sheet/barrel extraction assumptions remain explicitly unaccepted.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .copper import read_sexpr, solve_network
from .coupled import make_mesh, model_inputs, restrict_pad_contact_layer, restrict_stud_electrode


def analyze(board, pads_path, output, step=0.1):
    pads = json.loads(pads_path.read_text())
    tree = read_sexpr(board.read_text())
    mesh = make_mesh(board, tree, "AGND", step, pads, (156, 54.5), True)
    contacts = [restrict_stud_electrode(mesh, tree, r, 3.5) for r in ("J7", "J8")]
    contacts += [restrict_pad_contact_layer(mesh, r, "2", "F.Cu") for r in ("J3", "J4")]
    network = mesh.network()
    result = solve_network(
        network["u"],
        network["v"],
        network["g"],
        network["n"],
        network["electrodes"]([("J4", "2")]),
        network["electrodes"]([("J8", "1")]),
        details=True,
    )
    assert result["status"] == "diagnostic_estimate"
    voltage = result.pop("voltage")
    current = result.pop("current_at_one_volt")
    xyz = np.column_stack(np.nonzero(mesh.mask))
    assert len(xyz) == network["n"]
    u, v, g = (network[k] for k in ("u", "v", "g"))
    delta = voltage[u] - voltage[v]
    energy = g * delta**2 / current**2
    midx = (mesh.x[xyz[u, 1]] + mesh.x[xyz[v, 1]]) / 2
    midy = (mesh.y[xyz[u, 2]] + mesh.y[xyz[v, 2]]) / 2
    bins = np.floor(midx).astype(int) * 1000 + np.floor(midy).astype(int)
    unique, inverse = np.unique(bins, return_inverse=True)
    losses = np.bincount(inverse, weights=energy)
    ranked = sorted(zip(unique, losses), key=lambda row: -row[1])
    top = [
        dict(local_mm_bin=[int(b // 1000), int(b % 1000), 1, 1], loss_contribution_ohm=float(loss))
        for b, loss in ranked[:100]
    ]
    edge_order = np.argsort(energy)[-100:][::-1]
    edges = []
    for index in edge_order:
        ends = []
        for endpoint in (u[index], v[index]):
            z, x, y = xyz[endpoint]
            ends.append(dict(layer=int(z), local_mm=[float(mesh.x[x]), float(mesh.y[y])]))
        edges.append(
            dict(
                ends=ends,
                loss_contribution_ohm=float(energy[index]),
                one_amp_current_fraction=float(g[index] * delta[index] / current),
            )
        )
    report = dict(
        source_filled_pcb_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        native_pads_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        grid_mm=step,
        model_inputs=model_inputs(True),
        contact_scenarios=contacts,
        result=result,
        total_energy_ohm=float(energy.sum()),
        energy_vs_terminal_resistance_error_ohm=float(energy.sum() - result["ohm"]),
        top_spatial_bins=top,
        top_edges=edges,
        spatial_ranking_is_mesh_diagnostic_only=True,
        physical_qualified=False,
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(ohm=result["ohm"], top_bins=top[:15])), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("pads", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--step", type=float, default=0.1)
    args = parser.parse_args()
    analyze(args.board, args.pads, args.output, args.step)
