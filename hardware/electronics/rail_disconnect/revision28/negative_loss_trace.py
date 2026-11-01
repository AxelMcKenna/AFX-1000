"""Trace actual negative-source sheet/barrel loss before choosing another repair."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import label

from .copper import LAYERS, read_sexpr, solve_network
from .coupled import make_mesh, restrict_pad_contact_layer

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "generated/u28-negative-force-arms-work"


def main():
    board = WORK / "generated/filled-negative-force-arms1.kicad_pcb"
    pads_path = WORK / "generated/native-pads.json"
    tree = read_sexpr(board.read_text())
    mesh = make_mesh(
        board,
        tree,
        "N19_SRC",
        0.05,
        json.loads(pads_path.read_text()),
        bounds=(156, 54.5),
        distributed_barrels=True,
    )
    contacts = [restrict_pad_contact_layer(mesh, ref, pin, "F.Cu") for ref, pin in (("J1", "3"), ("Q3", "3"))]
    network = mesh.network()
    result = solve_network(
        network["u"],
        network["v"],
        network["g"],
        network["n"],
        network["electrodes"]([("J1", "3")]),
        network["electrodes"]([("Q3", "3")]),
        details=True,
    )
    assert result["status"] == "diagnostic_estimate"
    voltage = result.pop("voltage")
    current = result.pop("current_at_one_volt")
    coordinates = np.column_stack(np.nonzero(mesh.mask))
    assert len(coordinates) == network["n"]
    physical = np.column_stack((coordinates[:, 0], mesh.x[coordinates[:, 1]], mesh.y[coordinates[:, 2]]))
    one, two = physical[network["u"]], physical[network["v"]]
    power_at_one_amp = ((voltage[network["u"]] - voltage[network["v"]]) / current) ** 2 * network["g"]
    total = float(power_at_one_amp.sum())
    assert abs(total - result["ohm"]) / result["ohm"] < 1e-7
    bins = {}
    midpoint = (one + two) / 2
    for index, point in enumerate(midpoint):
        same_layer = one[index, 0] == two[index, 0]
        key = (int(point[0]) if same_layer else -1, int(point[1] // 4), int(point[2] // 4))
        bins[key] = bins.get(key, 0) + float(power_at_one_amp[index])
    rows = [
        dict(
            layer=LAYERS[k[0]] if k[0] >= 0 else "barrel-between-layers",
            box_board_mm=[4 * k[1], 4 * k[2], 4 * k[1] + 4, 4 * k[2] + 4],
            resistance_contribution_ohm=value,
        )
        for k, value in sorted(bins.items(), key=lambda q: -q[1])[:30]
    ]
    ids = np.full(mesh.mask.shape, -1, dtype=np.int64)
    ids[mesh.mask] = np.arange(network["n"])
    labels, count = label(mesh.mask[5])
    components = []
    for number in range(1, count + 1):
        cells = np.column_stack(np.nonzero(labels == number))
        if len(cells) < 20:
            continue
        values = voltage[ids[5, cells[:, 0], cells[:, 1]]]
        components.append(
            dict(
                cells=len(cells),
                box_board_mm=[
                    float(mesh.x[cells[:, 0]].min()),
                    float(mesh.y[cells[:, 1]].min()),
                    float(mesh.x[cells[:, 0]].max()),
                    float(mesh.y[cells[:, 1]].max()),
                ],
                voltage_range_at_one_volt=[float(values.min()), float(values.max())],
            )
        )
    report = dict(
        scope=__doc__,
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (board, pads_path, Path(__file__))
        },
        solver=result,
        contact_scenarios=contacts,
        edge_energy_identity_ohm=total,
        top_loss_regions=rows,
        back_layer_connected_regions=sorted(components, key=lambda q: -q["cells"]),
        physical_or_resistance_bound_qualified=False,
    )
    (WORK / "generated/N19-source-loss-trace.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(rows[:12], indent=2))


if __name__ == "__main__":
    main()
