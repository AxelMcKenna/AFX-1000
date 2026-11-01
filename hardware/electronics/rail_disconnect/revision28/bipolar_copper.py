"""Native compound-pad force-path comparison; no hot-FET or physical pass.

All actual pad shapes come from a source-hashed KiCad export. This adapter does
not alter shared copper.py or replace Q5B compound lands by ideal rectangles.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr
from .coupled import model_inputs, restrict_pad_contact_layer
from .native_mesh import NativePadMesh


def analyze(board, pads, steps=(0.1, 0.05), rails=("P12", "N12")):
    assert pads["source_pcb_sha256"] == hashlib.sha256(board.read_bytes()).hexdigest()
    tree = read_sexpr(board.read_text())
    cases = {
        "P19": ("Q2", "1", 0.026),
        "N19": ("Q4", "3", 0.026),
        "P12": ("Q6", "4", 0.151),
        "N12": ("Q8", "5", 0.151),
    }
    rows = []
    for rail in rails:
        fet, pin, current = cases[rail]
        for step in steps:
            original = NativePadMesh(tree, rail, step, pads)
            assert (fet, "3") in original.pads and ("J3", pin) in original.pads
            for face in ("F.Cu", "B.Cu"):
                mesh = copy.copy(original)
                mesh.pads = {key: dict(value) for key, value in original.pads.items()}
                contact = restrict_pad_contact_layer(mesh, "J3", pin, face)
                result = mesh.resistance([(fet, "3")], [("J3", pin)])
                result.update(
                    rail=rail,
                    grid_mm=step,
                    source_terminal=[fet, "3"],
                    load_terminal=["J3", pin],
                    load_contact_scenario=contact,
                    external_current_allocation_a=current,
                    voltage_drop_at_external_allocation_v=(
                        result["ohm"] * current if result["status"] == "diagnostic_estimate" else None
                    ),
                    native_pad_geometry_used=True,
                    physical_qualified=False,
                    source_pcb_sha256=pads["source_pcb_sha256"],
                )
                rows.append(result)
                print(rail, step, face, result["status"], result.get("ohm"), flush=True)
    return dict(
        source_pcb_sha256=pads["source_pcb_sha256"],
        rows=rows,
        physical_qualified=False,
        certified_resistance_upper_bound=False,
        model_inputs=model_inputs(),
        limitations=[
            "Native curved pad polygons use a 0.001 mm inscribed approximation; mesh sensitivity remains required.",
            "Candidate finished copper, resistivity, temperature and via-wall bounds are unaccepted process requirements.",
            "Within-layer plated annuli and component electrodes remain idealized; solder, contact and package distribution are unqualified.",
            "Only protected output copper is calculated here; FET RDS(on), source/common copper, harness, returns, load monitors and dynamic behavior remain separate.",
            "External-current figures exclude the complete local bleed/controller ledger and do not prove full source-to-load regulation.",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("pads", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--steps", default=".1,.05")
    parser.add_argument("--rails", default="P12,N12")
    args = parser.parse_args()
    result = analyze(
        args.board,
        json.loads(args.pads.read_text()),
        tuple(map(float, args.steps.split(","))),
        tuple(args.rails.split(",")),
    )
    result["pad_geometry_sha256"] = hashlib.sha256(args.pads.read_bytes()).hexdigest()
    result["analysis_tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + "\n")
