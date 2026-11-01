"""Actual analog F.Cu power-stem widening; retain every original package land.

The native0.2mm minimum clearance stays unchanged. Process/etch/mask/assembly
acceptance and finite-annulus current/return extraction remain unqualified.
"""

import hashlib
import json

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT, Router


def main(width=0.55):
    assert 0.5 < width <= 0.55, "This explicit variant is bounded by adjacent native control-pad clearances"
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    changes = []
    for ref in ("U13", "U14", "U32"):
        for pin in ("5", "6"):
            pad = next(p for p in rt.by_ref[ref] if p["pin"] == pin)
            x = pad["xy"][0]
            cy = sum(p["xy"][1] for p in rt.by_ref[ref] if p["pin"] in ("5", "12")) / 2
            found = []
            for node in children(tree, "segment"):
                if first(node, "layer")[1] != "F.Cu" or names[str(first(node, "net")[1])] != pad["net"]:
                    continue
                if abs(float(first(node, "width")[1]) - 0.5) > 1e-9:
                    continue
                points = [tuple(float(v) - 100 for v in first(node, end)[1:3]) for end in ("start", "end")]
                if all(abs(p[0] - x) < 1e-7 and cy - 2.75 <= p[1] <= cy + 2.1 for p in points):
                    old = sexpr(node)
                    first(node, "width")[1] = a(str(width))
                    found.append(str(first(node, "uuid")[1]))
                    changes.append(dict(ref=ref, terminal=pin, before=old, after=sexpr(node)))
            assert found, ("Actual analog stem missing", ref, pin)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/widened-analog-stems.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                candidate_pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                original_width_mm=0.5,
                new_width_mm=width,
                changed_native_objects=changes,
                actual_package_lands_unchanged=True,
                holes_and_part_poses_unchanged=True,
                native_clearance_minimum_relaxed=False,
                actual_foreign_pour_changes_and_finite_annular_positive_return_extraction_required=True,
                etch_and_mask_process_accepted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Widened", len(changes), "actual analog power-stem segments to", width, "mm")


if __name__ == "__main__":
    main()
