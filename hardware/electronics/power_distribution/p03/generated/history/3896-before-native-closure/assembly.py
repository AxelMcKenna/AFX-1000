"""Repair explicit assembly-side constraints on the actual P03 native board.

Tall through-hole film references are front-only. Their native plated pin
coordinates and electrical nets must survive the face correction unchanged.
"""

import json

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard, transform
from .route import coded, named
from .spec import ROOT

FRONT_ONLY = {"C32", "C33"}


def constraints(tree):
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in FRONT_ONLY or any(p[2] == "thru_hole" for p in children(fp, "pad")):
            assert first(fp, "layer")[1] == "F.Cu", (
                f"{ref}: through-hole assembly cannot consume bottom floor allowance"
            )
    return {
        "front_only_through_hole_rule_checked": True,
        "assembled_height_and_seating_physically_verified": False,
    }


def repair(cli):
    path = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(path.read_text()))
    parts = {p["ref"]: p for p in json.loads((ROOT / "components.json").read_text())}
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    changes = []
    for fp in list(children(tree, "footprint")):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref not in FRONT_ONLY or first(fp, "layer")[1] == "F.Cu":
            continue
        at = first(fp, "at")
        pose = (float(at[1]) - 100, float(at[2]) - 100, float(at[3]) if len(at) > 3 else 0, "F")
        c = parts[ref]
        c = dict(
            c,
            value=c["part"],
            mpn=c["part"],
            nets={
                str(p[1]): str(first(p, "net")[-1]).lstrip("/")
                for p in children(fp, "pad")
                if children(p, "net")
            },
        )
        lib, name = c["footprint"].split(":")
        replacement = placed_footprint(
            c,
            pose,
            footprint_root(cli) / (lib + ".pretty") / (name + ".kicad_mod"),
            nets,
            namespace="rmx:P03:",
        )

        def padmap(obj):
            return {
                str(p[1]): transform(obj, first(p, "at")[1:3])
                for p in children(obj, "pad")
                if children(p, "net")
            }

        old, new = padmap(fp), padmap(replacement)
        assert old.keys() == new.keys()
        assert all(max(abs(a - b) for a, b in zip(old[k], new[k])) < 1e-6 for k in old), (
            "Tall-part face repair moved plated pins"
        )
        tree[tree.index(fp)] = replacement
        changes.append(
            dict(ref=ref, from_face="B", to_face="F", plated_pin_positions_unchanged=True, pose_mm=pose)
        )
        report = json.loads((ROOT / "generated/placement.json").read_text())
        report["poses"][ref] = list(pose)
        report["courtyards"][ref] = [v - 100 for v in courtyard(replacement, "F.CrtYd")]
        (ROOT / "generated/placement.json").write_text(json.dumps(report, indent=2) + "\n")
    constraints(tree)
    path.write_text(sexpr(named(tree)) + "\n")
    (ROOT / "generated/assembly-side-repair.json").write_text(
        json.dumps(
            dict(
                changes=changes,
                front_only=sorted(FRONT_ONLY),
                assembled_height_allowance_top_mm=13.6,
                actual_through_hole_lead_crop_and_seating_verified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(changes)


if __name__ == "__main__":
    import sys

    repair(sys.argv[1])
