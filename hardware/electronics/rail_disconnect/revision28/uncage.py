"""Fine-grid physical escapes from small native connected via components.

0.025mm local search resolves legal passages between staggered 0.600mm barrels
that a 0.100/0.125mm global grid can miss. A new real barrel is placed outside the
pin field, and every trace/barrel remains subject to unfiltered native DRC.
"""

import hashlib
import json
import math
import uuid

from ...common.sexpr import a, children, read_sexpr, sexpr
from .local_escapes import escape
from .repair import ROOT, Router


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    graph = ROOT / "generated/open-components.json"
    rows = json.loads(graph.read_text())
    seen = set()
    result = []
    for row in rows:
        for group, other in (
            (row["components"][0], row["components"][1]),
            (row["components"][1], row["components"][0]),
        ):
            vias = [p for p in group if p["kind"] == "PCB_VIA"]
            if not 1 <= len(vias) <= 3:
                continue
            key = (row["net"], tuple(sorted(p["uuid"] for p in vias)))
            if key in seen:
                continue
            seen.add(key)
            start = min(vias, key=lambda p: min(math.dist(p["xy"], q["xy"]) for q in other))
            assert len(start["layers"]) == 6
            net = row["net"]
            found = None
            reason = None
            # No logical plane shortcut: every selected face contains an actual
            # trace starting at this already-existing physical through barrel.
            for layer in (1, 4, 2, 3, 0, 5):
                candidate = dict(start, net=net, layers=(layer,))
                found, reason = escape(rt, candidate, maxdistance=4, min_distance=2.2)
                if found:
                    break
            result.append(
                dict(
                    net=net,
                    native_via_uuid=start["uuid"],
                    source=start["xy"],
                    route=found,
                    unmet_reason=reason,
                )
            )
            print(net, start["xy"], bool(found), found["layer"] if found else reason, flush=True)
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:uncage:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/fine-native-via-escapes.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                native_graph_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),
                escapes=result,
                protected_ids=ids,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
