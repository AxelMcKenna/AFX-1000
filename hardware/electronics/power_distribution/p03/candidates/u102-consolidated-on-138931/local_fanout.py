"""Remove the actual analog-enable barrel fence across the BP5 return path."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-bp5-fence-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    new = (134.3, 30.7)
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"via", "segment"}:
            continue
        if names[str(first(obj, "net")[1])] == "P03_A_ENABLE":
            if obj[0] == "via":
                xy = tuple(float(v) - 100 for v in first(obj, "at")[1:3])
                take = math.dist(xy, (134.05, 30.25)) < 0.3
            else:
                pp = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
                take = (
                    first(obj, "layer")[1] == "F.Cu"
                    and min(p[0] for p in pp) < 135.5
                    and max(p[0] for p in pp) > 133.5
                    and min(p[1] for p in pp) < 31.5
                    and max(p[1] for p in pp) > 28.9
                )
            if take:
                tree.remove(obj)
                removed.append(obj[0])
    router = PowerRouter(tree)
    fixed = router.geometry
    router.geometry = [g for g in fixed if g["kind"] != "line"]
    assert router.safe_via("P03_A_ENABLE", new, clearance=0.16), (
        "Fixed land prevents the proposed enable barrel"
    )
    router.geometry = fixed
    for obj in list(children(tree, "segment")):
        if names[str(first(obj, "net")[1])] == "P03_A_ENABLE":
            continue
        a, b = [tuple(float(v) - 100 for v in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = (
            max(0, min(1, ((new[0] - a[0]) * dx + (new[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            if dx or dy
            else 0
        )
        if math.dist(new, (a[0] + t * dx, a[1] + t * dy)) < 0.3 + 0.16 + float(first(obj, "width")[1]) / 2:
            tree.remove(obj)
            removed.append("foreign_transit")
    router = PowerRouter(tree)
    assert router.safe_via("P03_A_ENABLE", new, clearance=0.16)

    def pad(ref, pin):
        return next(p for p in router.by_ref[ref] if p["pin"] == pin and p["layers"])

    enable = pad("U23", "7")
    router.path("P03_A_ENABLE", 0, [enable["xy"], new], 0.16)
    router.via("P03_A_ENABLE", new)
    bp5, cap = pad("U23", "6"), pad("C220", "1")
    assert bp5["net"] == cap["net"] == "P03_A_BP5"
    router.path("P03_A_BP5", 0, [bp5["xy"], cap["xy"]], 0.25)
    for p in [p for p in router.pads if p["net"] == "P03_A_ENABLE"]:
        router.connect(dict(net=p["net"], xy=new, layers=tuple(range(6))), p, 0.16)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/local-bp5-fence.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                enable_barrel_mm=new,
                bp5_direct_front_points_mm=[bp5["xy"], cap["xy"]],
                bp5_width_mm=0.25,
                removed_copper=removed,
                clearance_relaxed=False,
                native_refill_and_loop_verification_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Analog enable barrel moved clear of actual BP5 local path; native check required", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
