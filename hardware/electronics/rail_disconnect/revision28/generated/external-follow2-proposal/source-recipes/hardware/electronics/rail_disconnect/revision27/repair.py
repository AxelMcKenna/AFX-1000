"""Route between native connected-component anchors in the E27 candidate."""

import argparse
import json
import math
from pathlib import Path

from ...common.sexpr import children, read_sexpr, sexpr
from ..revision26 import router as aid
from ..revision26.wire import PlaneRouter
from .diagonal import diagonal_connect

ROOT = Path(__file__).resolve().parent


class CachedRouter(PlaneRouter):
    def __init__(self, board):
        super().__init__(board)
        self.cached = {}

    def connect(self, source, target, width):
        blocked, _ = self.masks(source["net"], width)
        for endpoint in (source, target):
            ix, iy = (round(v / aid.STEP) for v in endpoint["xy"])
            for layer in endpoint["layers"]:
                if layer != 4:
                    blocked[layer, ix, iy] = False
        return diagonal_connect(self, source, target, width)

    def masks(self, net, width):
        key = (net, width)
        if key not in self.cached:
            if getattr(self, "allow_pour_clearance", False):
                blocked, via = aid.Router.masks(self, net, width)
                blocked[1] = True
                blocked[4] = True
                self.cached[key] = (blocked, via)
            else:
                blocked, via = super().masks(net, width)
                if getattr(self, "inner_escape", False):
                    blocked[1] = aid.Router.masks(self, net, width)[0][1]
                self.cached[key] = (blocked, via)
        return self.cached[key]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inner-escape", action="store_true")
    p.add_argument("--allow-pour-clearance", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--attempts", type=int, default=12)
    a = p.parse_args()
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    if a.reset:
        pcb.write_bytes((ROOT.parent / "revision26/rail_disconnect.kicad_pcb").read_bytes())
    aid.STEP = 0.125
    tree = read_sexpr(pcb.read_text())
    r = CachedRouter(tree)
    r.max_search_nodes = 100000
    r.search_bias = 1.7
    r.allow_pour_clearance = a.allow_pour_clearance
    r.inner_escape = a.inner_escape
    opens = json.loads((ROOT / "generated/open-components.json").read_text())

    def tasks(row):
        groups = row["components"]
        pairs = []
        for source in groups[0]:
            if not any(l in (0, 2, 3, 5) for l in source["layers"]):
                continue
            for target in groups[1]:
                if not any(l in (0, 2, 3, 5) for l in target["layers"]):
                    continue
                pairs.append((math.dist(source["xy"], target["xy"]), source, target))
        return sorted(pairs, key=lambda p: p[0])

    ordered = sorted([(tasks(row), row) for row in opens], key=lambda task: task[0][0][0] if task[0] else 999)
    result = []
    for candidates, row in ordered:
        net = row["net"]
        r.cached = {}
        width = (
            1
            if net in ("V5_REG", "V5_REG_SRC", "5V_DIG", "5V_DIG_SRC")
            else 0.5
            if net in ("N19", "N19_SRC", "N12", "N12_SRC", "P19", "P19_SRC", "P12", "P12_SRC")
            else 0.25
        )
        if width > 0.25 and any(len(component) <= 3 for component in row["components"]):
            width = 0.25
        good = False
        attempts = 0
        seen = set()
        for _, source, target in candidates:
            key = (
                tuple(round(v / aid.STEP) for v in source["xy"]),
                tuple(source["layers"]),
                tuple(round(v / aid.STEP) for v in target["xy"]),
                tuple(target["layers"]),
            )
            if key in seen:
                continue
            seen.add(key)
            attempts += 1
            if attempts > a.attempts:
                break
            source = dict(source, net=net)
            target = dict(target, net=net)
            if r.connect(source, target, width):
                good = True
                break
        result.append(dict(net=net, success=good, attempts=attempts))
        print(net, good, attempts, flush=True)
    pcb.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/repair.json").write_text(
        json.dumps(
            dict(
                attempts=result,
                routes=r.routes,
                segments=len(children(tree, "segment")),
                vias=len(children(tree, "via")),
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
