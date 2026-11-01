"""Rebind the explicit protected inventory to a native-checked routing chunk.

Original protected UUIDs and physical package contracts stay fixed. New force /
gate / timing geometry and physically repaired new fanout objects become fixed;
remaining new signal routes stay movable. Every literal source object is hashed.
"""

import copy
import hashlib
import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .repair import ROOT


def main(previous_contract, label):
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    source = pcb.read_bytes()
    receipt_path = ROOT / "generated" / ("native-" + label + ".json")
    receipt = json.loads(receipt_path.read_text())
    assert receipt["pcb_sha256"] == hashlib.sha256(source).hexdigest()
    drc = ROOT / "generated" / ("drc-" + label + ".json")
    raw = json.loads(drc.read_text())
    assert receipt["drc_sha256"] == hashlib.sha256(drc.read_bytes()).hexdigest()
    assert not any(v["severity"] == "error" for v in raw["violations"])
    assert not receipt["counts"]["erc"] and not receipt["counts"]["schematic_parity"]
    prior_path = Path(previous_contract)
    prior = json.loads(prior_path.read_text())
    protected = {r["uuid"]: r["reasons"] for r in prior["locked_copper"]}
    tree = read_sexpr(source.decode())
    nodes = [n for tag in ("segment", "via") for n in children(tree, tag)]
    allids = {str(first(n, "uuid")[1]) for n in nodes}
    assert set(protected) <= allids, "Original protected UUID missing"
    repairs = {}
    for name in ("router-width-repair", "router-clearance-repair"):
        path = ROOT / "generated" / (name + ".json")
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for row in data.get("changed", []):
            repairs[row["uuid"]] = name
        for row in data.get("changed_native_objects", []):
            uid = str(first(read_sexpr(row["after"]), "uuid")[1])
            repairs[uid] = name
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    locked = []
    movable = []
    for node in nodes:
        uid = str(first(node, "uuid")[1])
        key = str(first(node, "net")[1])
        net = names.get(key, key.lstrip("/"))
        reasons = list(protected.get(uid, [])) + list(prior["lock_net_pin_reasons"].get(net, []))
        if uid in repairs:
            reasons.append("physically repaired new route " + repairs[uid])
        literal = sexpr(node)
        row = dict(
            uuid=uid,
            kind=str(node[0]),
            net=net,
            native_object_sha256=hashlib.sha256(literal.encode()).hexdigest(),
        )
        if reasons:
            row.update(reasons=sorted(set(reasons)), native_object=literal)
            locked.append(row)
        else:
            movable.append(row)
    result = copy.deepcopy(prior)
    result.update(
        source_pcb=str(pcb),
        source_pcb_sha256=hashlib.sha256(source).hexdigest(),
        locked_copper=locked,
        unlocked_nonforce_copper=movable,
        previous_contract_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        fresh_native_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        routing_candidate_accepted=False,
        physical_qualified=False,
    )
    result["fixed_footprints"] = [
        dict(
            ref=next(p[2] for p in children(f, "property") if p[1] == "Reference"),
            native_object_sha256=hashlib.sha256(sexpr(f).encode()).hexdigest(),
        )
        for f in children(tree, "footprint")
    ]
    result["fixed_zone_outlines"] = [
        dict(
            uuid=str(first(z, "uuid")[1]), native_object_sha256=hashlib.sha256(sexpr(z).encode()).hexdigest()
        )
        for z in children(tree, "zone")
    ]
    (ROOT / "generated/continued-lock-contract.json").write_text(json.dumps(result, indent=2) + "\n")
    print(len(locked), "locked;", len(movable), "movable; nativechecked", receipt["counts"])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("previous_contract")
    p.add_argument("label")
    a = p.parse_args()
    main(a.previous_contract, a.label)
