"""Separate R58−0.2mm Y candidate for the source-wire joint study.

Retain J4, all routing/vias/force geometry and every other footprint. Native
checks plus exact pad/barrel containment establish whether trace repair is
necessary. This does not adopt the wire candidate or qualify its assembly.
"""

import hashlib
import json

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT


def main():
    assert "generated" in ROOT.parts, "Use an isolated project only"
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    fp = next(
        f
        for f in children(tree, "footprint")
        if next(p[2] for p in children(f, "property") if p[1] == "Reference") == "R58"
    )
    at = first(fp, "at")
    assert list(map(float, at[1:])) == [252, 108.5, 0]
    assert first(fp, "layer")[1] == "F.Cu"
    old = sexpr(fp)
    at[2] = a("108.3")
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/r58-joint-clearance.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                candidate_pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                old_native_footprint=old,
                new_native_footprint=sexpr(fp),
                old_pose_board_mm=[152, 8.5, 0],
                new_pose_board_mm=[152, 8.3, 0],
                old_pose_housing_xy_mm=[160, 117],
                new_pose_housing_xy_mm=[160, 116.8],
                all_actual_tracks_and_vias_retained=True,
                trace_or_via_repairs_performed=0,
                j4_and_force_geometry_unchanged=True,
                router_guard_policy_unchanged=True,
                exact_native_contact_and_all_severity_verification_required=True,
                wire_candidate_adopted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Moved only R58Y−0.2mm; original vias/tracks unchanged pending native contact proof")


if __name__ == "__main__":
    main()
