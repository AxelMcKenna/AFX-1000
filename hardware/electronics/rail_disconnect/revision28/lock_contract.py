"""Explicit source-bound copper locks for a reversible routing experiment.

Locked geometry is identified from actual component pin contracts and recorded
repair objects. The unlocked geometry remains subject to fresh native checks,
force-polygon comparison, local-loop inspection and copper extraction.
"""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from ..revision26.layout import POWER_NETS
from .positive import components
from .repair import ROOT


def build(source, recipe_root=None):
    recipe_root = ROOT if recipe_root is None else recipe_root
    tree = read_sexpr(source.read_text())
    parts = {part["ref"]: part for part in components()}
    reasons = {net: ["actual force source/protected conductor"] for net in POWER_NETS}

    def add(net, reason):
        if net and net not in ("AGND", "V2V5_AUX"):
            reasons.setdefault(net, []).append(reason)

    critical = set()
    for ref in ("U1", "U2", "U3", "U4"):
        assert parts[ref]["part"] == "SI8751AB-ISR"
        for pin in parts[ref]["pins"]:
            if str(pin["number"]) in ("2", "5", "6", "7", "8"):
                critical.add(pin["net"])
                add(pin["net"], ref + "." + str(pin["number"]) + " " + pin["name"])
    # Follow actual local R/C gate/MCAP networks one component hop. This does
    # not classify an arbitrary name containing GATE as a timing contract.
    for part in parts.values():
        if not part["ref"].startswith(("R", "C")):
            continue
        if any(pin["net"] in critical for pin in part["pins"]):
            for pin in part["pins"]:
                add(pin["net"], "retained gate/MCAP/TT passive " + part["ref"])
    for pin in parts["U8"]["pins"]:
        if str(pin["number"]) in ("1", "2", "6", "7"):
            add(pin["net"], "actual OPA2333 inverter output/feedback pin U8." + str(pin["number"]))
    setting = set()
    for ref in ("U13", "U14", "U32", "U15", "U16", "U17", "U33"):
        assert parts[ref]["part"] == "TPS259482LYWP"
        for pin in parts[ref]["pins"]:
            if str(pin["number"]) in ("7", "9"):
                setting.add(pin["net"])
                add(pin["net"], ref + "." + str(pin["number"]) + " " + pin["name"])
    for part in parts.values():
        if part["ref"].startswith(("R", "C")) and any(pin["net"] in setting for pin in part["pins"]):
            for pin in part["pins"]:
                add(pin["net"], "actual eFuse setting passive " + part["ref"])
    recorded = {}
    for name in (
        "terminal-stitching",
        "force-stem-repair",
        "inverter-local-feedback",
        "control-pin-bundles",
        "first-bias-escape-repair",
        "first-dvdt-escape-repair",
    ):
        path = recipe_root / f"generated/{name}.json"
        if path.exists():
            for uid in json.loads(path.read_text()).get("protected_ids", []):
                recorded.setdefault(uid, []).append("explicit repair " + name)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    locked, unlocked = [], []
    for node in tree:
        if not isinstance(node, list) or not node or node[0] not in ("segment", "via"):
            continue
        uid = str(first(node, "uuid")[1])
        net = names[str(first(node, "net")[1])]
        why = reasons.get(net, []) + recorded.get(uid, [])
        row = dict(
            uuid=uid,
            kind=str(node[0]),
            net=net,
            native_object_sha256=hashlib.sha256(sexpr(node).encode()).hexdigest(),
        )
        if why:
            row.update(reasons=sorted(set(why)), native_object=sexpr(node))
            locked.append(row)
        else:
            unlocked.append(row)
    return dict(
        source_pcb=str(source),
        source_pcb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        locked_copper=locked,
        unlocked_nonforce_copper=unlocked,
        lock_net_pin_reasons={net: sorted(set(why)) for net, why in sorted(reasons.items())},
        fixed_footprints=[
            dict(
                ref=next(p[2] for p in children(fp, "property") if p[1] == "Reference"),
                native_object_sha256=hashlib.sha256(sexpr(fp).encode()).hexdigest(),
            )
            for fp in children(tree, "footprint")
        ],
        fixed_zone_outlines=[
            dict(
                uuid=str(first(zone, "uuid")[1]),
                native_object_sha256=hashlib.sha256(sexpr(zone).encode()).hexdigest(),
            )
            for zone in children(tree, "zone")
        ],
        explicit_acceptance=[
            "Every locked track/via object, footprint/pad/mount pose and zone outline must survive unchanged.",
            "Actual filled force zones require independent native polygon subtraction; zone-outline equality is insufficient.",
            "Retained gate, MCAP, feedback and eFuse setting loops require inspection; this inventory does not qualify their original layout.",
            "Unfiltered native opens, all-severity/all-track DRC, parity and ERC must be checked after import.",
            "New full conductor and coupled return extraction, startup/SOA, thermal, dynamic, fit and fabrication reviews remain mandatory.",
        ],
        physical_qualified=False,
        routing_candidate_accepted=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build(args.source)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(len(result["locked_copper"]), "locked;", len(result["unlocked_nonforce_copper"]), "unlocked")
