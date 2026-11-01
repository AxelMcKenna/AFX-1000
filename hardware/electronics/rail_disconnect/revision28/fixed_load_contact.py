"""Compare widened copper with an unchanged external contact electrode.

The actual conducting pad, annulus and barrel remain finite. The declared
0.85 mm contact radius is the original 1.7 mm pad envelope, not a guaranteed
fillet/contact bound. Only a process-local callback is adapted; shared model
source and every actual board file remain untouched.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from . import coupled


def main(board, pads, output, steps, radius=0.85):
    board, pads, output = Path(board), Path(pads), Path(output)
    assert output.resolve().is_relative_to(coupled.MODULE_ROOT / "generated")
    assert 0.5 < radius <= 0.85
    geometry = json.loads(pads.read_text())
    original = coupled.restrict_pad_contact_layer

    def fixed(mesh, ref, pin, layer):
        result = original(mesh, ref, pin, layer)
        assert (ref, str(pin)) == ("J3", "6")
        row = next(p for p in geometry["pad_polygons"] if p["ref"] == ref and p["pin"] == str(pin))
        x, y = [v - 100 for v in row["position_mm"]]
        region = mesh.pads[(ref, str(pin))][0]
        old_count = int(np.count_nonzero(region))
        contact = region & ((mesh.x[:, None] - x) ** 2 + (mesh.y[None, :] - y) ** 2 <= radius**2)
        assert np.any(contact)
        mesh.pads[(ref, str(pin))][0] = contact
        result.update(
            fixed_contact_radius_mm=radius,
            full_pad_electrode_cells=old_count,
            restricted_contact_electrode_cells=int(np.count_nonzero(contact)),
            actual_conducting_pad_and_barrel_unchanged=True,
            external_contact_or_filleting_bound_accepted=False,
        )
        return result

    coupled.restrict_pad_contact_layer = fixed
    rows = []
    try:
        for step in steps:
            row = coupled.positive(board, "analog", step, 3.5, "F.Cu", geometry, (156, 45.25), True)
            row.update(
                fixed_load_contact_reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                native_pad_geometry_sha256=hashlib.sha256(pads.read_bytes()).hexdigest(),
                expanded_pad_area_not_clamped_as_contact=True,
                external_contact_radius_scenario_mm=radius,
                physical_qualified=False,
            )
            rows.append(row)
            output.write_text(json.dumps(rows, indent=2) + "\n")
            print(step, row["status"], row.get("copper_plus_unequal_chip_penalty_ohm"), flush=True)
    finally:
        coupled.restrict_pad_contact_layer = original


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board", type=Path)
    p.add_argument("pads", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--steps", default=".1,.05")
    args = p.parse_args()
    main(args.board, args.pads, args.output, list(map(float, args.steps.split(","))))
