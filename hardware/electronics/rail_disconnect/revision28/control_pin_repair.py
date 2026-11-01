"""Reinstall complete eFuse small-pin bundles after passive placement repair."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .joint_escapes import EFUSES
from .repair import ROOT, Router


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    plans = [
        p
        for p in json.loads((ROOT / "generated/joint-escape-repair.json").read_text())["plans"]
        if p["ref"] in EFUSES and int(p["pin"]) in (1, 2, 3, 4, 8)
    ]
    legacy_landings=[(p['net'],p['points'][-1]) for p in plans]
    plans=[dict(p,points=p['points'][:-1]+[(134.15,6.35)]) if p['ref']=='U15' and int(p['pin'])==8 else p for p in plans]
    numbers = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    keep = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            net = numbers[str(first(node, "net")[1])]
            if node[0] == "segment" and first(node, "layer")[1] == "F.Cu":
                pts = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in ("start", "end")]
                drop = any(
                    net == p["net"]
                    and any(
                        abs(x - EFUSES[p["ref"]][0]) < 4 and abs(y - EFUSES[p["ref"]][1]) < 2.1
                        for x, y in pts
                    )
                    for p in plans
                )
            elif node[0] == "via":
                xy = tuple(float(v) - 100 for v in first(node, "at")[1:3])
                drop = any(net==n and __import__('math').dist(xy,pt)<.01 for n,pt in legacy_landings+[(p['net'],p['points'][-1]) for p in plans])
        if drop:
            removed.append(sexpr(node))
        else:
            keep.append(node)
    tree = keep
    rt = Router(tree)
    for plan in plans:
        rt.path(plan["net"], 0, plan["points"], 0.2)
        rt.via(plan["net"], plan["points"][-1])
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:control-pins:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/control-pin-bundles.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                plans=plans,
                removed_items=removed,
                protected_ids=ids,
                native_verified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Installed", len(plans), "complete physical small-pin bundles.")


if __name__ == "__main__":
    main()
