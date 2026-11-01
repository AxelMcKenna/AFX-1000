"""Remove legacy nonforce signal cages in an explicitly isolated project.

Every removed native object is retained verbatim. Actual force, terminal,
gate/timing/feedback contracts and local pad-attached return/auxiliary barrels
remain fixed. A higher initial open count is expected; only subsequent native
closure and full copper/return evidence can accept a resulting design.
"""

import hashlib
import json

from ...common.sexpr import children, first, read_sexpr, sexpr
from .lock_contract import build
from .repair import ROOT, Router


def main():
    assert "generated" in ROOT.parts, "Reset is allowed only in an isolated working project"
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    contract = build(path, ROOT)
    protected = {r["uuid"] for r in contract["locked_copper"]}
    reasons = {r["uuid"]: r["reasons"] for r in contract["locked_copper"]}
    for name in ("c40-return-connection", "analog-load-stitching", "analog-force-ladder"):
        recipe = ROOT / "generated" / (name + ".json")
        if recipe.exists():
            for uid in json.loads(recipe.read_text()).get("protected_ids", []):
                protected.add(uid)
                reasons.setdefault(uid, []).append("actual local repair " + name)
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    # Keep return/auxiliary barrels physically attached to local SMD lands,
    # including quiet local decoupling and package heat-spreading attachments.
    for node in children(tree, "via"):
        net = names[str(first(node, "net")[1])]
        if net not in ("AGND", "V2V5_AUX"):
            continue
        point = tuple(float(v) - 100 for v in first(node, "at")[1:3])
        if any(
            p["net"] == net
            and not p.get("through")
            and all(abs(point[i] - p["xy"][i]) <= p["size"][i] / 2 + 0.01 for i in (0, 1))
            for p in rt.pads
        ):
            uid = str(first(node, "uuid")[1])
            protected.add(uid)
            reasons.setdefault(uid, []).append("actual pad-attached local return/auxiliary barrel")
    removed = []
    kept = []
    locked = []
    for node in tree:
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            uid = str(first(node, "uuid")[1])
            literal = sexpr(node)
            row = dict(
                uuid=uid,
                kind=str(node[0]),
                net=names[str(first(node, "net")[1])],
                native_object_sha256=hashlib.sha256(literal.encode()).hexdigest(),
                native_object=literal,
            )
            if uid not in protected:
                removed.append(row)
                continue
            row["reasons"] = sorted(set(reasons[uid]))
            locked.append(row)
        kept.append(node)
    assert removed and locked
    contract.update(
        source_pcb_sha256=hashlib.sha256((sexpr(kept) + "\n").encode()).hexdigest(),
        source_pcb=str(path),
        locked_copper=locked,
        unlocked_nonforce_copper=[],
    )
    path.write_text(sexpr(kept) + "\n")
    out = ROOT / "generated"
    (out / "clean-signal-lock-contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    (out / "removed-legacy-nonforce-cages.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(before).hexdigest(),
                candidate_pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_objects=removed,
                retained_copper_count=len(locked),
                removed_native_count=len(removed),
                original_track_via_count=len(locked) + len(removed),
                no_footprint_or_terminal_placement_changes=True,
                all_actual_force_objects_retained=True,
                coupled_return_and_contact_correct_force_recheck_required=True,
                routing_candidate_accepted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Retained", len(locked), "protected native objects; removed", len(removed), "legacy nonforce objects"
    )


if __name__ == "__main__":
    main()
