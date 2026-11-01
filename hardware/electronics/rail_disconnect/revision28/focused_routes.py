"""Route genuine native via anchors on declared E28 inner signal corridors."""

import argparse
import json
import math
import uuid

from ...common.sexpr import a, children, read_sexpr, sexpr
from ..revision26 import router as aid
from .manufacturer import ROOT
from .repair import Router


def main(attempts=4, step=0.1, max_nodes=250000):
    path = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(path.read_text())
    aid.STEP = step
    aid.CLEARANCE = 0.20  # Router adds a separate0.02mm search guard; native rule remains0.20.
    rt = Router(tree)
    rt.inner_escape = True
    rt.allow_pour_clearance = False
    rt.max_search_nodes = max_nodes
    rt.search_bias = 2.0
    opens = json.loads((ROOT / "generated/open-components.json").read_text())
    result = []
    for row in opens:
        rt.cached = {}
        net = row["net"]
        ends = []
        for group in row["components"]:
            anchors = [p for p in group if p["kind"] == "PCB_VIA"]
            if not anchors:
                anchors = [p for p in group if any(l in (1, 4) for l in p["layers"])]
            if not anchors:
                # A genuine bare surface pad can often reach another native
                # pad/track on the same face without manufacturing a new drill.
                anchors = [p for p in group if p["kind"] == "PAD"] or list(group)
            ends.append(anchors)
        pairs = sorted(
            ((math.dist(a["xy"], b["xy"]), a, b) for a in ends[0] for b in ends[1]), key=lambda x: x[0]
        )
        good = False
        count = 0
        seen = set()
        searches = []
        for _, src, dst in pairs:
            key = tuple(src["xy"]), tuple(dst["xy"])
            if key in seen:
                continue
            seen.add(key)
            count += 1
            if count > attempts:
                break
            s = dict(src, net=net, layers=tuple(src["layers"]))
            t = dict(dst, net=net, layers=tuple(dst["layers"]))
            connected = rt.connect(s, t, 0.2)
            searches.append(rt.last_search.copy())
            if connected:
                good = True
                break
        result.append(
            dict(
                net=net,
                connected=good,
                attempts=count,
                actual_via_anchors=[len(g) for g in ends],
                searches=searches,
            )
        )
        print(
            net,
            good,
            count,
            [len(g) for g in ends],
            searches[-1] if searches else "no via anchor",
            flush=True,
        )
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:focused:{index}:{sexpr(node)}")))]
            )
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/focused-inner-routes.json").write_text(
        json.dumps(dict(attempts=result, routes=rt.routes), indent=2) + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempts", type=int, default=4)
    p.add_argument("--step", type=float, default=0.1)
    p.add_argument("--max-nodes", type=int, default=250000)
    args = p.parse_args()
    main(args.attempts, args.step, args.max_nodes)
