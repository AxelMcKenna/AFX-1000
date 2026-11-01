"""Locate loss in actual finite copper, without changing model/source files.

Per-cell dissipation is a diagnostic for choosing the next physical repair.
It is not an ampacity, temperature or certified resistance bound. Real
distributed annular and barrel edges are included, not ideal rectangles.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from . import coupled


def main(board, pads, output, step=0.1):
    board, pads, output = Path(board), Path(pads), Path(output)
    assert output.resolve().is_relative_to(coupled.MODULE_ROOT / "generated")
    geometry = json.loads(pads.read_text())
    meshes, networks, captured = [], [], {}
    make, solve = coupled.make_mesh, coupled.solve_network

    def make_record(*args, **kwargs):
        mesh = make(*args, **kwargs)
        meshes.append(mesh)
        network = mesh.network

        def record(*a, **kw):
            result = network(*a, **kw)
            networks.append(result)
            return result

        mesh.network = record
        return mesh

    def solve_record(*args, **kwargs):
        result = solve(*args, **kwargs)
        assert result["status"] == "diagnostic_estimate" and "voltage" in result
        captured["voltage"] = result["voltage"]
        captured["current"] = result["current_at_one_volt"]
        return result

    coupled.make_mesh, coupled.solve_network = make_record, solve_record
    try:
        result = coupled.positive(board, "analog", step, 3.5, "F.Cu", geometry, (156, 45.25), True)
    finally:
        coupled.make_mesh, coupled.solve_network = make, solve
    assert len(meshes) == len(networks) == 2
    one, two = networks
    offset = one["n"]
    union = coupled.Union(one["n"] + two["n"])
    for ref in ("U13", "U14", "U32"):
        for net, pins, base in ((one, ("5", "12"), 0), (two, ("6", "11"), offset)):
            ids = np.unique(net["electrodes"]([(ref, pin) for pin in pins])) + base
            for node in ids[1:]:
                union.join(int(ids[0]), int(node))
    roots = np.array([union.root(i) for i in range(one["n"] + two["n"])])
    _, mapping = np.unique(roots, return_inverse=True)
    rows, totals = [], []
    for name, mesh, net, base in zip(("input", "output"), meshes, networks, (0, offset)):
        assert net["n"] == np.count_nonzero(mesh.mask), (
            "Requires actual distributed nodes, not shorted annuli"
        )
        voltage = captured["voltage"][mapping[base : base + net["n"]]]
        edge_energy = net["g"] * (voltage[net["u"]] - voltage[net["v"]]) ** 2 / captured["current"] ** 2
        cell_energy = np.bincount(net["u"], weights=edge_energy / 2, minlength=net["n"]) + np.bincount(
            net["v"], weights=edge_energy / 2, minlength=net["n"]
        )
        z, x, y = np.nonzero(mesh.mask)
        # One millimetre bins retain layer identity and sum actual edge energy.
        positions = np.column_stack((z, np.floor(mesh.x[x]).astype(int), np.floor(mesh.y[y]).astype(int)))
        bins, index = np.unique(positions, axis=0, return_inverse=True)
        sums = np.bincount(index, weights=cell_energy)
        totals.append(float(np.sum(sums)))
        for rank in np.argsort(sums)[::-1][:100]:
            layer, xx, yy = bins[rank]
            rows.append(
                dict(
                    domain=name,
                    layer=coupled.LAYERS[layer],
                    board_bin_lower_left_mm=[int(xx), int(yy)],
                    bin_size_mm=1,
                    contribution_ohm=float(sums[rank]),
                )
            )
    assert abs(sum(totals) - result["actual_copper_energy_estimate_ohm"]) < 1e-10
    report = dict(
        source_pcb_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
        native_pad_geometry_sha256=hashlib.sha256(pads.read_bytes()).hexdigest(),
        reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        diagnostic=result,
        binning="Half of each physical sheet/barrel edge energy assigned to each real cell, summed in1mm layer-specific bins",
        full_energy_sum_ohm=sum(totals),
        rows=rows,
        physical_thermal_ampacity_and_bound_qualified=False,
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    for name in ("input", "output"):
        print(
            name,
            [
                (r["layer"], r["board_bin_lower_left_mm"], r["contribution_ohm"])
                for r in rows
                if r["domain"] == name
            ][:12],
            flush=True,
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board", type=Path)
    p.add_argument("pads", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--step", type=float, default=0.1)
    args = p.parse_args()
    main(args.board, args.pads, args.output, args.step)
