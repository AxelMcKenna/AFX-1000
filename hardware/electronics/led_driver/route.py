#!/usr/bin/env python3
"""Route the placed E20 driver PCB; independent native verification is required."""

import argparse
import json
import math

from ..common.sexpr import children, sexpr
from ..common.sexpr import read_sexpr as read
from ..control_inputs.board import Routing as FourLayerRouting
from .place import DATUM, MOUNTS, OUT, POSES, ROOT, SIZE

COPPER_LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
DEBUG = ROOT.parents[2] / "build/artifacts/research/e20-routing"


class Routing(FourLayerRouting):
    """Include all six copper layers in THT/via collision geometry."""

    def __init__(self, board, nets):
        super().__init__(board, nets)
        pads = [p for fp in children(board, "footprint") for p in children(fp, "pad")]
        assert len(pads) == len(self.geometry)
        for shape, pad in zip(self.geometry, pads):
            shape["is_pad"] = True
            if pad[3] in ("circle", "oval") and abs(shape["w"] - shape["h"]) < 1e-6:
                shape["kind"] = "circle"
                shape["r"] = shape["w"] / 2
            if len(shape["layers"]) > 1:
                shape["layers"] = list(COPPER_LAYERS)

    def via(self, net, xy, size=0.6):
        count = self.counts["vias"]
        super().via(net, xy, size)
        if self.counts["vias"] > count:
            self.geometry[-1]["layers"] = list(COPPER_LAYERS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fanout-only",
        action="store_true",
        help="Save native fanout intermediate for DRC before maze routing",
    )
    args = parser.parse_args()
    pcb = ROOT / "led_driver.kicad_pcb"
    board = read(pcb.read_text())
    assert not children(board, "segment"), (
        "Regenerate placement before routing; do not stack duplicate copper"
    )
    (OUT / "verification.json").unlink(missing_ok=True)
    nets = {str(n[2]).lstrip("/"): int(n[1]) for n in children(board, "net") if str(n[1]) != "0"}
    router = Routing(board, nets)
    for index, (x, y) in enumerate(MOUNTS):
        radius = 3.8
        router.geometry.append(
            dict(
                kind="circle",
                net=f"MOUNT_KEEP_OUT_{index}",
                layers=list(COPPER_LAYERS),
                x=x,
                y=y,
                r=radius,
            )
        )
        radius = 3.75 / math.cos(math.pi / 32)
        points = " ".join(
            f"(xy {100 + x + radius * math.cos(i * math.pi / 16):.6f} {100 + y + radius * math.sin(i * math.pi / 16):.6f})"
            for i in range(32)
        )
        board.append(
            read(f"""(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "In3.Cu" "In4.Cu" "B.Cu")
            (hatch edge .5) (connect_pads (clearance 0)) (min_thickness .15)
            (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
            (polygon (pts {points})))""")
        )
    tasks = {}
    router.endpoint_layers = {}
    for (ref, pin), (x, y, net) in router.pads.items():
        if net.startswith("unconnected-"):
            continue
        if ref.startswith("J"):
            tasks.setdefault(net, []).append((x, y))
            if ref == "J1" and pin not in ("1", "2", "8"):
                # Reserve exits from the fine-pitch THT input connector too;
                # surrounding supply branches can otherwise fence a pin in.
                router.endpoint_layers[(net, (x, y))] = ("In2.Cu", "In3.Cu", "B.Cu", "F.Cu")
            continue
        if ref in ("U1", "U2", "U3", "U4"):
            n = int(pin)
            if n == 33:
                continue
            # Two staggered via tiers keep 0.65mm-pitch pads clear with .6/.3
            # standard vias. Outward F.Cu escapes avoid the ground heat paddle.
            outward = 1 if y > POSES[ref][1] else -1
            at = (x, round(y + outward * (1.4 if n % 2 else 2.6), 6))
        elif ref == "U5":
            if pin in ("2", "23"):
                other = router.p("U5", 1 if pin == "2" else 24)
                router.path(net, "B", (x, y), other, width=0.25)
                continue
            # No exposed paddle: use inward B.Cu fanout beneath the body,
            # avoiding the output-header leads outside the package.
            inward = -1 if y > POSES[ref][1] else 1
            at = (x, round(y + inward * (1.1 if int(pin) % 2 else 2.4), 6))
        else:
            # Route directly from bottom SMD terminals. A fixed through-via
            # beside each terminal would collide with the top driver lands or
            # ground paddle. The grid may add vias only where all layers clear.
            tasks.setdefault(net, []).append((x, y))
            router.endpoint_layers[(net, (x, y))] = (POSES[ref][3] + ".Cu",)
            continue
        side = POSES[ref][3]
        router.path(net, side, (x, y), at, width=0.25 if net == "AGND" else 0.15)
        router.via(net, at)
        if net != "AGND":
            tasks.setdefault(net, []).append(at)
    for ref in ("U1", "U2", "U3", "U4"):
        cx, cy, _, _ = POSES[ref]
        for dx in (-3, 3):
            for dy in (-1.8, 1.8):
                router.via("AGND", (cx + dx, cy + dy))
    # These ground roots are already connected by the single In1 plane.
    # Native refill/connectivity subsequently verifies that assumption.
    router.initially_connected = {
        "AGND": [at for net, at in router.vias if net == "AGND"] + [router.p("J1", 1), router.p("J1", 8)]
    }
    # Wide supply distribution connects the input, bulk capacitor and all four
    # common-anode headers. Lower-current IC/capacitor branches follow at .25mm.
    high_current = [router.p("J1", 2), router.p("C13", 1)]
    high_current += [router.p(ref, pin) for ref in ("J2", "J3", "J4", "J5") for pin in (25, 26)]
    tasks["5V_DIG"] = [p for p in tasks["5V_DIG"] if p not in high_current]
    ordered = {}
    for net in ("LED_XLAT", "LED_SCK", "LED_MOSI", "LED_BLANK"):
        ordered[net] = tasks.pop(net)
    for net in ("OE_N", "ENABLE_MID", "PG_3V3", "PG_5V"):
        ordered[net] = tasks.pop(net)
    ordered["V3V3_IO"] = tasks.pop("V3V3_IO")
    ordered["5V_DIG"] = tasks.pop("5V_DIG")
    for net in ("IREF_0", "IREF_1", "IREF_2", "IREF_3"):
        ordered[net] = tasks.pop(net)
    for net in ("SERIAL_0", "SERIAL_1", "SERIAL_2"):
        ordered[net] = tasks.pop(net)
    for net in ("LATCH_5V_SRC", "CLOCK_5V_SRC", "DATA_5V_SRC", "BLANK_5V_SRC"):
        ordered[net] = tasks.pop(net)
    # Reference and control terminals are less accessible than the wide-pitch
    # output headers. Route them before the repeated LED fanouts close lanes.
    for net in sorted(list(tasks)):
        if not (net.startswith("LED_") and net[4:].isdigit()):
            ordered[net] = tasks.pop(net)
    # Reach the far header row before the nearer row; each chip occupies six
    # connector columns, so the two output banks need no inter-chip crossing.
    for bank in (range(22, 11, -2), range(23, 12, -2), range(0, 12, 2), range(11, 0, -2)):
        for chip in range(4):
            for output in bank:
                net = f"LED_{chip * 24 + output:02d}"
                ordered[net] = tasks.pop(net)
    ordered.update(tasks)
    from .route_grid import connect

    if not args.fanout_only:
        try:
            router.route_width = {"5V_DIG": 0.8}
            connect(router, {"5V_DIG": high_current}, SIZE)
            router.route_width = {}
            # Escape each remaining SMD land before global branches can fence
            # it in. All resulting endpoints are accessible on signal layers.
            escapes = {}
            for net, at in router.endpoint_layers:
                escapes.setdefault(net, []).append(at)
            connect(router, escapes, SIZE, escape=True)
            for net, targets in ordered.items():
                ordered[net] = [getattr(router, "escape_points", {}).get((net, at), at) for at in targets]
            # Every ground land now reaches a through via (or is a THT pad).
            # The In1/In4 planes join them without redundant signal-layer trees.
            # Native saved refill/connectivity must prove those connections.
            ordered.pop("AGND")
            connect(router, ordered, SIZE)
        except AssertionError:
            DEBUG.mkdir(parents=True, exist_ok=True)
            (DEBUG / "route-debug.kicad_pcb").write_text(
                "(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n"
            )
            raise
    for plane in ("In1.Cu", "In4.Cu"):
        board.append(
            read(f"""(zone (net {nets["AGND"]}) (net_name "/AGND") (layer "{plane}") (hatch edge .5)
      (connect_pads (clearance .15)) (min_thickness .15) (fill yes (thermal_gap .2) (thermal_bridge_width .25))
      (polygon (pts (xy 100.6 100.6) (xy 190.4 100.6) (xy 190.4 126.4) (xy 100.6 126.4))))""")
        )
    if args.fanout_only:
        DEBUG.mkdir(parents=True, exist_ok=True)
    destination = DEBUG / "fanout.kicad_pcb" if args.fanout_only else pcb
    destination.write_text("(kicad_pcb\n" + "\n".join(sexpr(v) for v in board[1:]) + "\n)\n")
    (OUT / "routing-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E20",
                board_size_mm=[*SIZE, 1.6],
                layout_origin_proposal_mm=DATUM,
                counts=router.counts,
                paths=router.paths,
                native_verified=False,
                fanout_only=args.fanout_only,
            ),
            indent=2,
        )
        + "\n"
    )
    print("E20 copper generated; run native all-severity DRC/parity/refill before accepting it.", flush=True)


if __name__ == "__main__":
    main()
