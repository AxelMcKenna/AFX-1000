"""Install explicitly noncrossing, cap-aware native pin fanout bundles.

All displaced tracks/barrels are recorded; no finding is exempted. Native DRC
on the resulting actual geometry remains the acceptance gate for each bundle.
"""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .integrate_positive import ROOT, board_net, native_parts, write_schematic
from .repair import Router

EFUSES = {
    "U13": (41.5, 5.5),
    "U14": (41.5, 10.5),
    "U32": (41.5, 15.5),
    "U15": (131, 5.5),
    "U16": (131, 10.5),
    "U17": (131, 15.5),
    "U33": (135, 20.5),
}
IC_REFS = ("U12", "U21", "U25", "U27")


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    parts = native_parts()
    by = {p["ref"]: p for p in parts}
    write_schematic(parts)
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    # The relocated spare gate preserves the exact safe-request Boolean logic.
    for ref in ("U25", "U27"):
        fp = next(
            fp
            for fp in children(tree, "footprint")
            if any(p[1] == "Reference" and p[2] == ref for p in children(fp, "property"))
        )
        for pad in children(fp, "pad"):
            pin = next(p for p in by[ref]["pins"] if str(p["number"]) == str(pad[1]))
            name = board_net(by[ref], pin)
            if name not in nets:
                nets[name] = max(nets.values()) + 1
                tree.append([a("net"), a(str(nets[name])), name])
            first(pad, "net")[1:] = [
                a(str(nets[name])),
                name if name.startswith("unconnected-") else "/" + name,
            ]
    old = Router(tree)
    removed = []
    # Use complete pin bundles: the earlier greedy single-pin escapes could
    # fence in adjacent PG pins even when every individual segment was legal.
    regions = [(x - 3.9, y - 2.05, x + 4.4, y + 2.05) for x, y in EFUSES.values()]
    bundle_pads = [p for ref in IC_REFS for p in old.by_ref[ref]]
    c52 = old.by_ref["C52"]
    old_c52 = [p["xy"] for p in c52]
    kept = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            keys = ("at",) if node[0] == "via" else ("start", "end")
            pts = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
            # Local IC fanouts live on their component face. Through barrels
            # in those pin corridors must also be cleared before bundling.
            side = None if node[0] == "via" else str(first(node, "layer")[1])
            drop = any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts for x0, y0, x1, y1 in regions)
            if not drop:
                drop = any(
                    math.dist(pt, p["xy"]) < 2.7
                    and (side is None or side == ("F.Cu" if 0 in p["layers"] else "B.Cu"))
                    for pt in pts
                    for p in bundle_pads
                )
            drop |= any(math.dist(pt, q) < 0.02 for pt in pts for q in old_c52)
        if drop:
            removed.append(sexpr(node))
        else:
            kept.append(node)
    tree = kept
    # 0.05mm clears the actual U33 OUT top barrel by .249mm rather than .199.
    fp = next(
        fp
        for fp in children(tree, "footprint")
        if any(p[1] == "Reference" and p[2] == "C52" for p in children(fp, "property"))
    )
    first(fp, "at")[1] = a("236.75")
    rt = Router(tree)
    # Actual timing/source pad barrels, reused by the shared same-net escapes.
    for ref in ("C39", "C41", "C43", "C45", "C47", "C49", "C51", "C52"):
        for p in rt.by_ref[ref]:
            rt.via(p["net"], (43.8, 11.6) if ref == "C41" and p["pin"] == "1" else p["xy"])
    plans = []
    for ref, (cx, cy) in EFUSES.items():
        for p in rt.by_ref[ref]:
            pin = int(p["pin"])
            if pin in (5, 6, 10, 11, 12):
                continue
            x, y = p["xy"]
            sx = -1 if x < cx else 1
            sy = -1 if y < cy else 1
            if pin in (1, 4, 7):
                pts = [
                    p["xy"],
                    (cx + sx * 1.6, y),
                    (cx + sx * 2.15, cy + sy * 1.225),
                    (cx + sx * 2.15, cy + sy * 1.5),
                ]
            else:
                pts = [p["xy"], (cx + sx * 2.875, y), (cx + sx * 3.15, cy + sy * 0.5)]
            custom = {
                ("U13", 7): [(43.3, 6.175), (43.3, 6.8)],
                ("U13", 9): [(43.1, 5.275), (43.8, 4.575), (43.8, 3.6)],
                ("U14", 1): [(39.9, 9.825), (39.0, 9.4)],
                ("U14", 7): [(43.01, 11.175), (43.01, 12.4), (45.05, 12.4)],
                ("U14", 9): [(43.1, 10.275), (43.1, 9.2), (43.1, 8.8)],
                ("U14", 8): [(46.5, 10.725), (46.5, 10.75)],
                ("U15", 7): [(132.6, 6.175), (132.6, 6.8), (135.4, 6.8)],
                ("U17", 7): [(132.6, 16.175), (132.6, 16.5), (135.35, 16.5)],
                ("U17", 8): [(133.8, 15.725)],
                ("U17", 9): [(132.5, 15.275), (133.2, 14.575), (134.15, 14.575)],
                ("U32", 3): [(37.7, 15.725)],
            }
            if (ref, pin) in custom:
                pts = [p["xy"]] + custom[ref, pin]
            rt.path(p["net"], 0, pts, 0.2)
            rt.via(p["net"], pts[-1])
            plans.append(dict(ref=ref, pin=pin, net=p["net"], layer="F.Cu", points=pts))
        # Duplicate IN/OUT lands are joined only within this one device.
        for pin, dx in ((5, -0.476), (6, 0.476)):
            net = next(p["net"] for p in rt.by_ref[ref] if p["pin"] == str(pin))
            pts = [(cx + dx, cy - 1.4), (cx + dx, cy + 1.4)]
            rt.path(net, 0, pts, 0.5)
            for pt in pts:
                rt.via(net, pt)
    for ref in IC_REFS:
        for p in rt.by_ref[ref]:
            if p["net"].startswith("unconnected-"):
                continue
            pin = int(p["pin"])
            x, y = p["xy"]
            layer = p["layers"][0]
            if ref == "U25":
                custom = {
                    3: [(137.65, 13.85)],
                    4: [(137, 14.1), (136.75, 13.85)],
                    5: [(136.35, 14.25), (136.75, 13.85)],
                    7: [(135.05, 13.5)],
                    8: [(135.05, 10.5)],
                    9: [(135.7, 11.1)],
                }
                pts = [p["xy"]] + custom.get(
                    pin, [(x, y + (1 if y > 12 else -1) * (p["size"][1] / 2 + 0.575 + pin % 2))]
                )
            else:
                centre = sum(q["xy"][0] for q in rt.by_ref[ref]) / len(rt.by_ref[ref])
                pts = [p["xy"], (x + (1 if x > centre else -1) * (p["size"][0] / 2 + 0.575 + pin % 2), y)]
            if ref == "U21" and pin == 1:
                pts = [p["xy"], (110.2, 16.45), (109.6, 16.2)]
            rt.path(p["net"], layer, pts, 0.2)
            rt.via(p["net"], pts[-1])
            plans.append(dict(ref=ref, pin=pin, net=p["net"], layer=layer, points=pts))
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:joint-escape:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/joint-escape-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_items=removed,
                plans=plans,
                protected_ids=ids,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "joint bundle",
        len(plans),
        "pins;",
        len(removed),
        "removed;",
        len(ids),
        "new copper items",
        flush=True,
    )


if __name__ == "__main__":
    main()
