"""Actual protected-bulk return sheet paths; retain the C24 charging loop.

The B.Cu capacitor contact is an explicit unapproved solder-joint scenario.
No capacitor ESR/lead impedance, bars, contacts, P03 ground or dynamic load model
is supplied by this calculation. It is not an electrical qualification bound.
"""

import hashlib
import json
from pathlib import Path

from .copper import read_sexpr, solve_network
from .coupled import make_mesh, model_inputs, restrict_pad_contact_layer, restrict_stud_electrode

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "generated/u28-return-dual-plane-work"


def main():
    board = WORK / "generated/filled-u28-return-dual-plane1.kicad_pcb"
    native_path = WORK / "generated/native-pads.json"
    pads = json.loads(native_path.read_text())
    tree = read_sexpr(board.read_text())
    mesh = make_mesh(board, tree, "AGND", 0.1, pads, bounds=(156, 54.5), distributed_barrels=True)
    scenarios = [restrict_stud_electrode(mesh, tree, ref, 3.5) for ref in ("J7", "J8")]
    scenarios += [restrict_pad_contact_layer(mesh, ref, "2", "B.Cu") for ref in ("C20", "C24")]
    network = mesh.network()
    rows = []
    for ref, star in (("C20", "J7"), ("C24", "J8")):
        row = solve_network(
            network["u"],
            network["v"],
            network["g"],
            network["n"],
            network["electrodes"]([(ref, "2")]),
            network["electrodes"]([(star, "1")]),
        )
        row.update(capacitor_ground=ref + ".2", return_stud=star + ".1", grid_mm=0.1)
        rows.append(row)
    report = dict(
        scope=__doc__,
        paths=rows,
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (board, native_path, Path(__file__))
        },
        contact_scenarios=scenarios,
        model_inputs=model_inputs(distributed_barrels=True),
        source_and_protected_bulk_nets_unchanged=True,
        full_bar_contact_P03_and_dynamic_qualified=False,
        physical_and_fabrication_qualified=False,
    )
    (WORK / "generated/protected-bulk-return-diagnostic.json").write_text(json.dumps(report, indent=2) + "\n")
    print([(r["capacitor_ground"], r.get("status"), r.get("ohm")) for r in rows])


if __name__ == "__main__":
    main()
