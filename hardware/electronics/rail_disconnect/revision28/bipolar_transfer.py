"""Finite bipolar copper-port diagnostic for the actual N12 sense repair.

Checks both force domains cut by that repair. External headers use declared
F/B contact scenarios, never an accepted connector/solder resistance. Package,
switch, controller, return, dynamics and process uncertainty remain outside it.
"""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr
from .copper import solve_network
from .coupled import make_mesh, model_inputs, restrict_pad_contact_layer

ROOT = Path(__file__).resolve().parent


def main(board, pads, output, steps):
    board, pads, output = Path(board), Path(pads), Path(output)
    assert output.resolve().is_relative_to(ROOT / "generated")
    geometry = json.loads(pads.read_text())
    tree = read_sexpr(board.read_text())
    rows = []
    for step in steps:
        for net, source, sink, external, allocation in (
            ("P12_SRC", ("J1", "4"), ("Q5", "3"), ("J1", "4"), 0.151),
            ("P19", ("Q2", "3"), ("J3", "1"), ("J3", "1"), 0.026),
        ):
            for face in ("F.Cu", "B.Cu"):
                mesh = make_mesh(board, tree, net, step, geometry, (156, 45.25), True)
                contact = restrict_pad_contact_layer(mesh, *external, face)
                network = mesh.network()
                result = solve_network(
                    network["u"],
                    network["v"],
                    network["g"],
                    network["n"],
                    network["electrodes"]([source]),
                    network["electrodes"]([sink]),
                )
                result.update(
                    net=net,
                    source_terminal=source,
                    sink_terminal=sink,
                    external_header_contact_scenario=contact,
                    grid_mm=step,
                    source_pcb_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
                    native_pad_geometry_sha256=hashlib.sha256(pads.read_bytes()).hexdigest(),
                    model_inputs=model_inputs(True),
                    external_load_only_a=allocation,
                    local_loads_package_switch_and_all_returns_excluded=True,
                    complete_source_to_load_or_resistance_bound_qualified=False,
                    physical_qualified=False,
                )
                if result["status"] == "diagnostic_estimate":
                    result["drop_at_external_only_load_v"] = allocation * result["ohm"]
                rows.append(result)
                output.write_text(json.dumps(rows, indent=2) + "\n")
                print(net, face, step, result["status"], result.get("ohm"), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board", type=Path)
    p.add_argument("pads", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--steps", default=".1,.05")
    args = p.parse_args()
    main(args.board, args.pads, args.output, list(map(float, args.steps.split(","))))
