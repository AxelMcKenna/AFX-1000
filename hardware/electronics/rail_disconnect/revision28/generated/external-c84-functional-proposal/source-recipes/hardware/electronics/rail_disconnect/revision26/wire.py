"""Connect pre-reserved E26 ports while preserving wide current/return planes."""

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from ...common.sexpr import children, first, read_sexpr, sexpr
from . import router as aid
from .layout import POWER_NETS
from .planes import add as add_planes

ROOT = Path(__file__).resolve().parent


class PlaneRouter(aid.Router):
    def __init__(self, board):
        super().__init__(board)
        self.load_existing_copper()
        self.plane_masks = defaultdict(dict)
        x = self.xx
        y = self.yy
        for z in children(board, "zone"):
            if not children(z, "net_name") or not str(first(z, "net_name")[1]):
                continue
            net = str(first(z, "net_name")[1]).lstrip("/")
            layer = aid.LAYERS.index(str(first(z, "layer")[1]))
            if layer in (1, 4):
                continue
            points = [tuple(float(v) - 100 for v in p[1:3]) for p in first(first(z, "polygon"), "pts")[1:]]
            mask = np.zeros((self.nx, self.ny), dtype=bool)
            for a, b in zip(points, points[1:] + points[:1]):
                if abs(b[1] - a[1]) < 1e-10:
                    continue
                hit = ((a[1] > y) != (b[1] > y)) & (x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0])
                mask ^= hit
            if net in self.plane_masks[layer]:
                self.plane_masks[layer][net] |= mask
            else:
                self.plane_masks[layer][net] = mask
        for x, y in ((4, 20), (152, 3.8), (10, 36), (100, 36)):
            self.geometry.append(
                dict(kind="via", xy=(x, y), radius=3.2, net="HEAD_KEEPOUT", layers=tuple(range(6)))
            )

        sizes = {"C4": 16.5, "C8": 16.5, "C12": 8.5, "C16": 8.5, "C20": 10.5, "C24": 16.5}
        for ref, diameter in sizes.items():
            pads = self.by_ref[ref]
            center = tuple(sum(p["xy"][i] for p in pads) / len(pads) for i in (0, 1))
            self.geometry.append(
                dict(kind="via", xy=center, radius=diameter / 2, net="BULK_BODY_NOVIA", layers=())
            )

    def masks(self, net, width):
        blocked, via = super().masks(net, width)
        blocked[1] = True
        blocked[4] = True
        via |= (self.xx < 0.81) | (self.xx > 155.19) | (self.yy < 0.81) | (self.yy > 44.44)
        for layer, shapes in self.plane_masks.items():
            for other, mask in shapes.items():
                if other != net:
                    blocked[layer] |= mask
        return blocked, via


def main():
    out = ROOT / "generated"
    (out / "verification.json").unlink(missing_ok=True)
    aid.STEP = 0.125
    tree = read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text())
    assert not children(tree, "zone"), "Start from generate output, not already routed planes"
    plans = add_planes(tree)
    r = PlaneRouter(tree)
    r.max_search_nodes = 250000
    r.search_bias = 1.3
    packet = json.loads((out / "placement-inputs.json").read_text())
    groups = defaultdict(list)
    for p in packet["ports"]:
        if p["net"] == "AGND":
            continue
        p = dict(p)
        p["layers"] = (0, 2, 3, 5)
        p["xy"] = tuple(p["xy"])
        if (
            p["net"] in POWER_NETS
            and p["ref"].startswith("Q")
            and any(q["ref"].startswith("Q") for q in groups[p["net"]])
        ):
            continue
        if not any(math.dist(p["xy"], q["xy"]) < 1e-6 for q in groups[p["net"]]):
            groups[p["net"]].append(p)
    failures = []
    for net in sorted(
        groups, key=lambda n: (n not in ("V2V5_AUX", "PROTECT_REF", "ALL_RAILS_ALLOW"), len(groups[n]), n)
    ):
        ps = groups[net]
        if len(ps) < 2:
            continue
        connected = [ps[0]]
        remaining = ps[1:]
        failed = []
        width = 0.35 if net == "V2V5_AUX" else 0.25
        while remaining:
            _, i, j = min(
                (math.dist(a["xy"], b["xy"]), i, j)
                for i, a in enumerate(connected)
                for j, b in enumerate(remaining)
            )
            target = remaining.pop(j)
            sources = sorted(connected, key=lambda p: math.dist(p["xy"], target["xy"]))
            for source in sources:
                if r.connect(source, target, width):
                    connected.append(target)
                    break
            else:
                failed.append(target)
        for target in failed:
            failures.append(dict(net=net, target=target))
        print("E26route", net, len(ps), "ports;", len(failed), "unresolved", flush=True)
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    report = dict(
        revision="E26",
        planes=plans,
        ports_routed=sum(len(p) for p in groups.values()),
        segments=len(children(tree, "segment")),
        vias=len(children(tree, "via")),
        zones=len(children(tree, "zone")),
        failures=failures,
        routes=r.routes,
        pcb_routed=False,
        copper_loss_or_current_balance_qualified=False,
        build_ready=False,
    )
    (out / "routing-inputs.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "E26candidate:",
        report["segments"],
        "segments",
        report["vias"],
        "vias",
        len(failures),
        "unresolved tasks; native fill/DRC required",
    )


if __name__ == "__main__":
    main()
