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
    ("U26", "2", "AGND", (150.3, 10.0)),
    ("U25", "5", "P03_MON_BUCK_OK", (141.75, 9.4)),
    ("R302", "1", "V5_REG_SRC", (141.6, 11.25)),
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
        fixed_clear = router.safe_via(net, xy, clearance=.16)
        router.geometry = full
        if not fixed_clear:
            records.append(dict(ref=ref, pin=pin, net=net, via_mm=xy, authored=False, hold="fixed geometry conflict"))
            continue
        displaced = []
        for obj in list(children(tree, "segment")):
            if names[str(first(obj, "net")[1])] == net:
                continue
            a, b = [tuple(float(v)-100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
            dx, dy = b[0]-a[0], b[1]-a[1]
            t = max(0, min(1, ((xy[0]-a[0])*dx+(xy[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
            if math.dist(xy, (a[0]+t*dx, a[1]+t*dy)) < .3+.16+float(first(obj, "width")[1])/2:
                tree.remove(obj)
                displaced.append(obj)
        router = PowerRouter(tree)
        assert router.safe_via(net, xy, clearance=.16)
        router.max_search_nodes = 100000
        if not router.connect(pad, dict(net=net, xy=xy, layers=pad["layers"]), .16):
            tree.extend(displaced)
            records.append(dict(ref=ref, pin=pin, net=net, via_mm=xy, authored=False))
            continue
        router.via(net, xy)
        records.append(dict(ref=ref, pin=pin, net=net, via_mm=xy, authored=True,
                            displaced_transit_nets=[names[str(first(o, "net")[1])] for o in displaced]))
        print("Final local escape", ref, pin, xy, flush=True)
    pcb.write_text(sexpr(named(tree))+"\n")
    (root/"generated/final-fanout.json").write_text(json.dumps(dict(
        before_pcb_sha256=before, records=records, native_refill_and_connectivity_required=True,
        clearance_relaxed=False, physical_qualified=False), indent=2)+"\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
