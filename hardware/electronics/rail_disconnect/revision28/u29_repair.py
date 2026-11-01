"""Joint U29 bottom-row escape repair; larger C0G case moves0.45mm south."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .relocate import main as move
from .repair import ROOT, Router


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    move({"C43": (124, 14.70, 0, "B")}, "u29-timing-cap-clearance")
    placed = json.loads((ROOT / "generated/u29-timing-cap-clearance.json").read_text())["placements"]["C43"]
    assert placed == [124, 14.70, 0, "B"], ("Unexpected capacitor fallback", placed)
    tree = read_sexpr(path.read_text())
    kept = []
    removed = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            keys = ("at",) if node[0] == "via" else ("start", "end")
            pts = [tuple(float(v) - 100 for v in first(node, k)[1:3]) for k in keys]
            onface = node[0] == "via" or first(node, "layer")[1] == "B.Cu"
            drop = onface and any(121 <= x <= 127.6 and 11.25 <= y <= 13.7 for x, y in pts)
        if drop:
            removed.append(sexpr(node))
        else:
            kept.append(node)
    tree = kept
    rt = Router(tree)
    plans = {
        "1": [(127.1, 12.05)],
        "2": [(125.25, 13.25), (127.3, 13.25)],
        "3": [(124.75, 13.15), (122, 13.15)],
        "4": [(122.7, 12.05)],
    }
    actual = []
    for pin, tail in plans.items():
        p = next(p for p in rt.by_ref["U29"] if p["pin"] == pin)
        points = [p["xy"]] + tail
        rt.path(p["net"], 5, points, 0.2)
        rt.via(p["net"], points[-1])
        actual.append(dict(pin=pin, net=p["net"], points_mm=points, face="B.Cu"))
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U29joint:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/u29-joint-escape-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_items=removed,
                actual_escapes=actual,
                protected_ids=ids,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
