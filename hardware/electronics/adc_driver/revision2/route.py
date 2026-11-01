"""Exploratory R2 copper: explicit local FDA/pump paths, then obstacle-aware routing."""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from ...common.sexpr import sexpr
from ..pcb.router import AdcRouter
from .generate import OUT, ROOT, board


class R2Router(AdcRouter):
    def masks(self, net, width):
        blocks, vias = super().masks(net, width)
        for center in [30, 80]:
            for lo, hi in [(center - 6.5, center - 1), (center + 1, center + 6.5)]:
                hit = (
                    (self.xx > lo - width / 2 - 0.15)
                    & (self.xx < hi + width / 2 + 0.15)
                    & (self.yy > 38.7 - width / 2 - 0.15)
                    & (self.yy < 45 + width / 2 + 0.15)
                )
                for layer in [2, 3, 5]:
                    blocks[layer] |= hit
                vias |= hit
        return blocks, vias

    def p(self, ref, pin):
        return next(p for p in self.by_ref[ref] if p["pin"] == str(pin))

    def local(self):
        self.escapes = {}
        self.max_search_nodes = 400000
        for ci, ch in enumerate(("L", "R")):
            dx = 50 * ci
            u = "U" + str(ci + 1)

            def r(n):
                return "R" + str(n + 16 * ci)

            def c(n):
                return "C" + str(n + 14 * ci)

            def direct(net, a, b, layer=0, width=0.2):
                self.path(net, layer, [self.p(*a)["xy"], self.p(*b)["xy"]], width)

            # Compact backside bypass: one power via under the body; ground return below relief.
            for up, cap, x, net in [(3, c(13), 29.4 + dx, "V5_REG"), (6, c(14), 30.6 + dx, "NBIAS_" + ch)]:
                via = (x, 43.325)
                self.path(net, 0, [self.p(u, up)["xy"], via], 0.2)
                self.via(net, via)
                self.path(net, 5, [via, self.p(cap, 1)["xy"]], 0.2)
                self.escapes[(u, str(up))] = via
                self.escapes[(cap, "1")] = via
                ground = (x - 2 if up == 3 else x + 2, 46.5)
                self.path("AGND", 5, [self.p(cap, 2)["xy"], (x, 46.5), ground], 0.25)
                self.via("AGND", ground)
            for up, x, net in [(2, 29.6 + dx, "VOCM_" + ch), (7, 30.4 + dx, "PD_" + ch)]:
                via = (x, 40.9)
                self.path(net, 0, [self.p(u, up)["xy"], (x, 42.675), via], 0.15)
                self.via(net, via)
                self.escapes[(u, str(up))] = via
            # HF capacitors and Rg/Rf summing branches stay entirely on F.Cu.
            for side, ip, op, cap, rg, rf in [("P", 8, 5, c(1), r(1), r(3)), ("N", 1, 4, c(2), r(2), r(4))]:
                net = "FB_" + side + "_" + ch
                direct(net, (u, ip), (cap, 2))
                direct(net, (cap, 2), (rf, 2))
                outer = (36 if side == "P" else 24) + dx
                self.path(
                    net,
                    0,
                    [
                        self.p(rf, 2)["xy"],
                        (outer, self.p(rf, 2)["xy"][1]),
                        (outer, self.p(rg, 2)["xy"][1]),
                        self.p(rg, 2)["xy"],
                    ],
                    0.2,
                )
                sensevia = (35 + dx if side == "P" else 25 + dx, 37.5)
                sense = self.p(rf, 1)["net"]
                inner = (34 if side == "P" else 26) + dx
                self.path(
                    sense,
                    0,
                    [self.p(rf, 1)["xy"], (inner, self.p(rf, 1)["xy"][1]), (inner, 37.5), sensevia],
                    0.2,
                )
                self.via(sense, sensevia)
                self.escapes[(rf, "1")] = sensevia
                drv = "DRV_" + ch + ("N" if side == "P" else "P")
                direct(drv, (u, op), (cap, 1))
                direct(drv, (cap, 1), (r(6) if side == "P" else r(5), 1))
            for up, x, y in [
                (4, 10 if ci == 0 else 90, 12.5),
                (6, 17.5 if ci == 0 else 97.5, 11.325),
                (7, 18.5 if ci == 0 else 98.5, 10.675),
            ]:
                pump = "U" + str(5 + ci)
                p = self.p(pump, up)
                via = (x, y)
                self.path(p["net"], 0, [p["xy"], (x, p["xy"][1]), via], 0.2)
                self.via(p["net"], via)
                self.escapes[(pump, str(up))] = via
            # Flying cap is directly behind the two pump terminals; one via each.
            pump = "U" + str(5 + ci)
            for up, cp in [(1, 1), (8, 2)]:
                net = self.p(pump, up)["net"]
                xy = (12.5 + (80 * ci) if cp == 1 else 15.5 + (80 * ci), 8.2)
                self.path(net, 0, [self.p(pump, up)["xy"], xy], 0.25)
                self.via(net, xy)
                self.path(net, 5, [xy, self.p(c(8), cp)["xy"]], 0.25)
                self.escapes[(pump, str(up))] = xy
                self.escapes[(c(8), str(cp))] = xy
        # Reserve crowded IC escapes before global traces can fence them in.
        for ref, pin, xy in [
            ("U3", 8, (60, 40.5)),
            ("U3", 4, (50, 45.5)),
            ("U4", 4, (50, 18)),
            ("U4", 11, (60, 18)),
        ]:
            pad = self.p(ref, pin)
            self.path(pad["net"], 0, [pad["xy"], (xy[0], pad["xy"][1]), xy], 0.2)
            self.via(pad["net"], xy)
            self.escapes[(ref, str(pin))] = xy
        for pad in self.by_ref["U7"]:
            if pad["net"] == "AGND":
                continue
            x = 50.8 if pad["xy"][0] < 55 else 59.2
            via = (x, round(pad["xy"][1] * 4) / 4)
            self.path(pad["net"], 0, [pad["xy"], (x, pad["xy"][1]), via], 0.2)
            self.via(pad["net"], via)
            self.escapes[("U7", pad["pin"])] = via
        for pin in (5, 6):
            pad = self.p("U8", pin)
            via = (59, round(pad["xy"][1] * 4) / 4)
            self.path(pad["net"], 0, [pad["xy"], (59, pad["xy"][1]), via], 0.2)
            self.via(pad["net"], via)
            self.escapes[("U8", str(pin))] = via
        for ref, xy in [
            ("R8", (41, 26)),
            ("R10", (41.5, 33)),
            ("R11", (46, 33)),
            ("R26", (59.5, 33)),
            ("R27", (64.25, 34.5)),
            ("R40", (60.5, 61)),
            ("R41", (56, 64)),
        ]:
            pin = "2" if ref == "R40" else "1"
            pad = self.p(ref, pin)
            self.path(pad["net"], 0, [pad["xy"], (xy[0], pad["xy"][1]), xy], 0.2)
            self.via(pad["net"], xy)
            self.escapes[(ref, pin)] = xy
        # Ground escape to the dedicated planes, using safe obstacles outside the FDA reliefs.
        for pad in self.pads:
            if pad["net"] == "AGND" and not pad["through"] and pad["ref"] not in ("C13", "C14", "C27", "C28"):
                target = dict(net="AGND", xy=pad["xy"], layers=(1, 4))
                if not self.connect(pad, target, 0.25):
                    self.failed.append(dict(net="AGND", source=[pad["ref"], pad["pin"]], target="plane"))

    def route_all(self):
        self.local()
        groups = defaultdict(list)
        for pad in self.pads:
            if not pad["net"].startswith(("unconnected-", "FB_")) and pad["net"] != "AGND":
                if (pad["ref"], pad["pin"]) in self.escapes:
                    pad = dict(pad, xy=self.escapes[(pad["ref"], pad["pin"])], layers=(2, 3, 5))
                groups[pad["net"]].append(pad)
        for net in sorted(groups, key=lambda n: (n in ("V5_REG", "P12", "N12"), n)):
            connected, remaining = groups[net][:1], groups[net][1:]
            while remaining:
                _, i, j = min(
                    (math.dist(a["xy"], b["xy"]), i, j)
                    for i, a in enumerate(connected)
                    for j, b in enumerate(remaining)
                )
                source, target = connected[i], remaining.pop(j)
                width = 0.35 if net in ("V5_REG", "P12", "N12") else 0.2
                if not self.connect(source, target, width):
                    self.failed.append(
                        dict(
                            net=net,
                            source=[source["ref"], source["pin"]],
                            target=[target["ref"], target["pin"]],
                        )
                    )
                connected.append(target)
            print(net, len(groups[net]), "lands", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True)
    args = parser.parse_args()
    candidate = board(args.kicad_cli)
    router = R2Router(candidate)
    router.route_all()
    router.prune_unused_vias()
    (ROOT / "adc_driver.kicad_pcb").write_text(sexpr(candidate) + "\n")
    (OUT / "routing.json").write_text(
        json.dumps(
            dict(routes=router.routes, failed=router.failed, native_drc_required=True, build_ready=False),
            indent=2,
        )
        + "\n"
    )
    print("Exploratory route complete;", len(router.failed), "search failures; native DRC required")


if __name__ == "__main__":
    main()
