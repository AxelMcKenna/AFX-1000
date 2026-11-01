"""Native source-terminal to first MOSFET-drain copper diagnostic.

This excludes contact, FET channels, common/protected copper, load/return and
complete local bleed/control currents. It never certifies end-to-end regulation.
"""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr
from .coupled import model_inputs, restrict_pad_contact_layer
from .native_mesh import NativePadMesh

PORTS = {"P19": ("1", "Q1"), "N19": ("3", "Q3"), "P12": ("4", "Q5"), "N12": ("5", "Q7")}


def analyze(board, pads, rail, steps=(0.1, 0.05)):
    assert pads["source_pcb_sha256"] == hashlib.sha256(board.read_bytes()).hexdigest()
    pin, fet = PORTS[rail]
    rows = []
    tree = read_sexpr(board.read_text())
    for step in steps:
        for face in ("F.Cu", "B.Cu"):
            mesh = NativePadMesh(tree, rail + "_SRC", step, pads)
            contact = restrict_pad_contact_layer(mesh, "J1", pin, face)
            row = mesh.resistance([("J1", pin)], [(fet, "3")])
            row.update(
                rail=rail,
                grid_mm=step,
                source_terminal=["J1", pin],
                fet_drain_terminal=[fet, "3"],
                source_contact=contact,
            )
            rows.append(row)
            print(rail, step, face, row["status"], row.get("ohm"), flush=True)
    return dict(
        source_pcb_sha256=pads["source_pcb_sha256"],
        rows=rows,
        model_inputs=model_inputs(),
        certified_resistance_upper_bound=False,
        complete_bipolar_rail_qualified=False,
        physical_qualified=False,
        limitations=__doc__,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board", type=Path)
    p.add_argument("pads", type=Path)
    p.add_argument("rail", choices=PORTS)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    x = analyze(a.board, json.loads(a.pads.read_text()), a.rail)
    a.output.write_text(json.dumps(x, indent=2) + "\n")
