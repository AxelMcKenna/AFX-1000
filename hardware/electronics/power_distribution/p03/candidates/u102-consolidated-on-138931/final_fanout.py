"""Exact local barrel escapes for the final native routing obligations.

Only foreign transit segments in a selected barrel's actual clearance disk may
be displaced. Fixed component pads, supports, plated holes and all EP arrays are
preserved. Every displaced segment remains a native routing obligation.
"""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import PowerRouter, coded, named
from .spec import ROOT

TARGETS = [
    ("C300", "1", "P03_MON_TIMER", (151.5, 14.95)),
    ("U25", "12", "P03_ALL_SOURCES_READY", (147.1, 9.7)),
    ("U25", "15", "P03_MON_TIMER", (147.2, 11.15)),
    ("R302", "1", "V5_REG_SRC", (144.75, 10.9)),
    ("R40", "1", "N12_RMID", (132.55, 13.9125)),
    ("R39", "2", "N12_RMID", (132.55, 9.5875)),
    ("C110", "1", "AUX_START_DELAY", (31.75, 14.45)),
    ("U102", "7", "AUX_START_DELAY", (29.25, 19.675)),
]


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-final-fanout-{before[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    records = []
    for ref, pin, net, xy in TARGETS:
        router = PowerRouter(tree)
        pad = next(p for p in router.by_ref[ref] if p["pin"] == pin)
        assert pad["net"] == net
        full = router.geometry
        router.geometry = [g for g in full if g["kind"] != "line"]
        fixed_clear = router.safe_via(net, xy, clearance=0.16)
        router.geometry = full
        if not fixed_clear:
            records.append(
                dict(ref=ref, pin=pin, net=net, via_mm=xy, authored=False, hold="fixed geometry conflict")
            )
            continue
        displaced = []
        for obj in list(children(tree, "segment")):
            if names[str(first(obj, "net")[1])] == net:
                continue
            a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = (
                max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            if math.dist(xy, (a[0] + t * dx, a[1] + t * dy)) < 0.3 + 0.16 + float(first(obj, "width")[1]) / 2:
                tree.remove(obj)
                displaced.append(obj)
        router = PowerRouter(tree)
        assert router.safe_via(net, xy, clearance=0.16)
        router.max_search_nodes = 100000
        if not router.connect(pad, dict(net=net, xy=xy, layers=pad["layers"]), 0.16):
            tree.extend(displaced)
            records.append(dict(ref=ref, pin=pin, net=net, via_mm=xy, authored=False))
            continue
        router.via(net, xy)
        router.max_search_nodes = 600000
        if ref in {"C300", "R40", "C110"}:
            remote = None
        elif net == "N12_RMID":
            remote = dict(net=net, xy=(133.625, 13.375), layers=tuple(range(6)))
        elif net == "AUX_START_DELAY":
            remote = dict(net=net, xy=(31.75, 14.45), layers=tuple(range(6)))
        elif net == "P03_MON_BUCK_OK":
            remote = dict(net=net, xy=(154.15, 9.05), layers=tuple(range(6)))
        elif net == "P03_ALL_SOURCES_READY":
            remote = dict(net=net, xy=(151.65, 16.7), layers=tuple(range(6)))
        elif net == "P03_MON_TIMER":
            remote = dict(net=net, xy=(151.5, 14.95), layers=tuple(range(6)))
        elif net == "V5_REG_SRC":
            remote = dict(net=net, xy=(67.5, 32.875), layers=tuple(range(6)))
        else:
            remote = None
        joined = remote is None or router.connect(dict(net=net, xy=xy, layers=tuple(range(6))), remote, 0.16)
        print("Remote closure", net, joined, flush=True)
        records.append(
            dict(
                ref=ref,
                pin=pin,
                net=net,
                via_mm=xy,
                authored=True,
                remote_joined=joined,
                displaced_transit_nets=[names[str(first(o, "net")[1])] for o in displaced],
            )
        )
        print("Final local escape", ref, pin, xy, flush=True)
    router = PowerRouter(tree)
    ana = next(p for p in router.by_ref["R302"] if p["pin"] == "2")
    ana_join = router.connect(ana, dict(net="P03_MON_ANA", xy=(147.25, 10.9), layers=tuple(range(6))), 0.16)
    records.append(dict(net="P03_MON_ANA", moved_sense_bottom_joined=ana_join))
    print("Moved analog monitor sense", ana_join, flush=True)
    dig = next(p for p in router.by_ref["R301"] if p["pin"] == "1")
    dig_join = router.connect(dig, dict(net="P03_MON_DIG", xy=(145.7, 12.2225), layers=tuple(range(6))), 0.16)
    records.append(dict(net="P03_MON_DIG", monitor_joined=dig_join))
    print("Digital monitor", dig_join, flush=True)
    cap = next(p for p in router.by_ref["C300"] if p["pin"] == "2")
    cap_ground = router.connect(cap, dict(net="AGND", xy=(154, 14.25), layers=tuple(range(6))), 0.16)
    records.append(dict(net="AGND", new_timer_cap_return_joined=cap_ground))
    print("New timer cap ground", cap_ground, flush=True)
    ready = router.connect(
        dict(net="P03_ALL_SOURCES_READY", xy=(150.25, 11), layers=tuple(range(6))),
        dict(net="P03_ALL_SOURCES_READY", xy=(145.7, 16.7), layers=tuple(range(6))),
        0.16,
    )
    records.append(dict(net="P03_ALL_SOURCES_READY", existing_barrel_joined=ready))
    print("READY existing-barrel closure", ready, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/final-fanout.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=before,
                records=records,
                native_refill_and_connectivity_required=True,
                clearance_relaxed=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
