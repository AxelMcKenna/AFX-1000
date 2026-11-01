"""Real VIN plane tap with an equal-width local N12 output detour.

The existing 0.25 mm negative-output trace blocks the only nearby through-via
crossing. Move that short segment outward 0.45 mm on the SAME layer, retaining
its native endpoints, width and node. No regulator SET/feedback trace is moved.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-vin-tap-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    target = []
    for obj in children(tree, "segment"):
        if names[str(first(obj, "net")[1])] != "N12_SRC" or first(obj, "layer")[1] != "In3.Cu":
            continue
        p = [tuple(round(float(v) - 100, 5) for v in first(obj, k)[1:3]) for k in ("start", "end")]
        if set(p) == {(89.15, 27.35), (86.9, 27.35)}:
            target.append(obj)
    assert len(target) == 1, "Exact retained N12 force segment not found"
    tree.remove(target[0])
    r = PowerRouter(tree)
    xy = (87.675, 26.925)
    assert r.safe_via("VIN_PROTECTED", xy, clearance=0.16)
    r.via("VIN_PROTECTED", xy)
    path = [(89.15, 27.35), (89.15, 27.8), (86.9, 27.8), (86.9, 27.35)]
    r.path("N12_SRC", 3, path, 0.25)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/vin-tap.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                tap_net="VIN_PROTECTED",
                tap_mm=xy,
                via_land_mm=0.6,
                finished_bore_mm=0.25,
                N12_output_same_layer_path_mm=path,
                original_and_retained_width_mm=0.25,
                added_trace_length_mm=0.9,
                clearance_relaxed=False,
                native_refill_and_connectivity_required=True,
                input_feed_resistance_current_noise_and_physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("VIN filled-plane tap and same-width local N12 detour authored", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
