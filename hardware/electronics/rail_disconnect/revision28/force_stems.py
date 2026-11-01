"""Rebuild finite power pin escapes around the actual local timing lands.

Each eFuse has two native IN and two OUT pads. No internal package short is
used to excuse an unconnected PCB terminal. All barrels/stems are physical.
"""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .joint_escapes import EFUSES
from .repair import ROOT, Router


def main(source=None):
    path = ROOT / "rail_disconnect.kicad_pcb" if source is None else Path(source)
    assert path.resolve().is_relative_to(ROOT.resolve())
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    prior = ROOT / "generated/force-stem-repair.json"
    previous_removed = []
    if prior.exists():
        record = json.loads(prior.read_text())
        if record.get("protected_ids"):
            ids = set(record["protected_ids"])
            kept = []
            for node in tree:
                if (
                    isinstance(node, list)
                    and node
                    and node[0] in ("segment", "via")
                    and children(node, "uuid")
                    and str(first(node, "uuid")[1]) in ids
                ):
                    previous_removed.append(sexpr(node))
                else:
                    kept.append(node)
            tree = kept
    rt = Router(tree)
    plans = []
    for ref, (cx, cy) in EFUSES.items():
        for pin, dx in ((5, -0.476), (6, 0.476)):
            net = next(p["net"] for p in rt.by_ref[ref] if p["pin"] == str(pin))
            x = cx + dx
            stem = [(x, cy - 1.4), (x, cy + 1.4)]
            barrels = list(stem)
            links = []
            if ref == "U14":
                stem = [(x, cy - 1.4), (x, cy + 0.7)]
                if pin == 5:
                    barrels = [(x, cy - 1.4), (x, cy - 2.05), (x, cy - 2.7)]
                    stem = [barrels[-1], (x, cy + 0.7)]
                else:
                    barrels = [(x, cy - 1.4), (x, cy - 2.05), (x, cy - 2.7)]
                    stem = [barrels[-1], (x, cy + 0.7)]
            elif ref == "U32" or ref == "U17" and pin == 6:
                stem = [(x, cy - 0.7), (x, cy + 2.05)]
                barrels = [(x, cy + 1.4), (x, cy + 2.05)]
                if ref == "U32" and pin == 5:
                    stem = [(x, cy - 0.7), (x, cy + 1.75)]
                    barrels = [(x, cy + 1.15), (x, cy + 1.75),(x-.674,cy+1.75)]
                    links=[barrels[1:]]
                elif ref=='U32':
                    barrels.append((x+.574,cy+1.4))
                    links=[[(x,cy+1.4),barrels[-1]]]
            elif ref == "U33":
                stem = [(x, cy - 1.4), (x, cy + 0.7)]
                if pin == 5:
                    barrels = [(x, cy - 1.4), (x - 0.674, cy - 1.4)]
                    links = [barrels]
                else:
                    barrels = [(x, cy - 1.4), (x, cy - 2.05)]
                    stem = [barrels[1], (x, cy + 0.7)]
            plans.append(dict(ref=ref, pin=pin, net=net, x=x, cy=cy, stem=stem, barrels=barrels, links=links))
    removed = list(previous_removed)
    keep = []
    net_ids = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            net = net_ids[str(first(node, "net")[1])]
            for plan in plans:
                if net != plan["net"]:
                    continue
                x, cy = plan["x"], plan["cy"]
                if node[0] == "segment" and str(first(node, "layer")[1]) == "F.Cu":
                    pts = [tuple(float(v) - 100 for v in first(node, key)[1:3]) for key in ("start", "end")]
                    drop = all(abs(p[0] - x) < 0.01 and cy - 2.06 <= p[1] <= cy + 2.06 for p in pts)
                elif node[0] == "via":
                    pt = tuple(float(v) - 100 for v in first(node, "at")[1:3])
                    obsolete = (
                        (ref := plan["ref"]) in ("U14", "U33")
                        and abs(pt[1] - (cy + 1.4)) < 0.01
                        or (ref == "U32" or ref == "U17" and plan["pin"] == 6)
                        and abs(pt[1] - (cy - 1.4)) < 0.01
                        or ref == "U32"
                        and plan["pin"] == 5
                        and abs(pt[1] - (cy + 1.4)) < 0.01
                    )
                    drop = obsolete and abs(pt[0] - x) < 0.01
                if drop:
                    break
        if drop:
            removed.append(sexpr(node))
        else:
            keep.append(node)
    tree = keep
    rt = Router(tree)
    for plan in plans:
        rt.path(plan["net"], 0, plan["stem"], 0.5)
        for link in plan["links"]:
            rt.path(plan["net"], 0, link, 0.5)
        for xy in plan["barrels"]:
            rt.via(plan["net"], xy)
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:force-stems:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    for node in children(tree, "via"):
        xy = tuple(float(v) - 100 for v in first(node, "at")[1:3])
        if any(
            any(abs(xy[0] - p[0]) < 1e-5 and abs(xy[1] - p[1]) < 1e-5 for p in plan["barrels"])
            and net_ids[str(first(node, "net")[1])] == plan["net"]
            for plan in plans
        ):
            uid = str(first(node, "uuid")[1])
            if uid not in ids:
                ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/force-stem-repair.json").write_text(
        json.dumps(
            dict(
                source_pcb_path=str(path),
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                actual_plans=plans,
                removed_items=removed,
                protected_ids=ids,
                finite_resistance_and_ampacity_accepted=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Rebuilt", len(plans), "actual .5 mm force stems with explicit native barrel landings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pcb", type=Path)
    main(parser.parse_args().source_pcb)
