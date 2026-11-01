"""Contact-face-correct negative conductor diagnostics, excluding MOSFETs.

Header contacts are engineering F-face scenarios, not selected mated parts.
Source/common/protected copper is modeled separately; no semiconductor gate,
hot RDS(on), source, harness, return, startup or system voltage pass follows.
"""

import argparse
import hashlib
import json
from pathlib import Path

from .copper import read_sexpr, solve_network
from .coupled import make_mesh, model_inputs, restrict_pad_contact_layer

ROOT = Path(__file__).resolve().parent
PATHS = {
    "N12_SRC": (("J1", "5"), ("Q7", "3")),
    "N12_COMMON": (("Q7", "1"), ("Q8", "1")),
    "N12": (("Q8", "3"), ("J3", "5")),
    "N19_SRC": (("J1", "3"), ("Q3", "3")),
    "N19_COMMON": (("Q3", "1"), ("Q4", "1")),
    "N19": (("Q4", "3"), ("J3", "3")),
}


def analyze(board, pads_path, steps, output):
    pads = json.loads(pads_path.read_text())
    tree = read_sexpr(board.read_text())
    rows = []
    for step in steps:
        for net, (one, two) in PATHS.items():
            mesh = make_mesh(board, tree, net, step, pads, bounds=(156, 54.5), distributed_barrels=True)
            contacts = [restrict_pad_contact_layer(mesh, ref, pin, "F.Cu") for ref, pin in (one, two)]
            network = mesh.network()
            result = solve_network(
                network["u"],
                network["v"],
                network["g"],
                network["n"],
                network["electrodes"]([one]),
                network["electrodes"]([two]),
            )
            result.update(
                net=net,
                terminals=[one, two],
                grid_mm=step,
                contact_scenarios=contacts,
                source_pcb_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
                native_pads_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
            )
            rows.append(result)
            report = dict(
                scope=__doc__,
                paths=rows,
                model_inputs=model_inputs(distributed_barrels=True),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                header_contact_part_and_resistance_accepted=False,
                MOSFET_gate_bias_hot_RDSon_accepted=False,
                negative_copper_voltage_and_system_qualified=False,
            )
            output.write_text(json.dumps(report, indent=2) + "\n")
            print(net, step, result.get("status"), result.get("ohm"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("pads", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--steps", default=".1,.05")
    args = parser.parse_args()
    analyze(args.board, args.pads, tuple(map(float, args.steps.split(","))), args.output)
