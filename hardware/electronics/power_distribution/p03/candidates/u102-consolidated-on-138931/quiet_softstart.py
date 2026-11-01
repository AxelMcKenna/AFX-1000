"""Actual capped soft-start barrel/In2 corridor; switch/support exclusions stay intact."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-quiet-softstart-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    router = PowerRouter(tree)
    source = next(p for p in router.by_ref["U13"] if p["pin"] == "9" and p["layers"])
    via = (111.25, 7.6)
    assert source["net"] == "LO_P_SS"
    assert router.safe_via(source["net"], via, clearance=0.16), (
        "Actual fixed copper does not permit the SS barrel"
    )
    router.path(source["net"], 0, [source["xy"], via], 0.16)
    router.via(source["net"], via)
    holds = []
    for ref, pin in [("R49", "2"), ("C74", "1")]:
        target = next(p for p in router.by_ref[ref] if p["pin"] == pin and p["layers"])
        if not router.connect(dict(net=source["net"], xy=via, layers=tuple(range(6))), target, 0.16):
            holds.append(ref + "." + pin)
    pcb.write_text(sexpr(named(tree)) + "\n")
    (root / "generated/quiet-softstart.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                source_terminal="U13.9",
                net="LO_P_SS",
                barrel_mm=via,
                land_mm=0.6,
                finished_bore_mm=0.25,
                required_via_wall_minimum_um=50,
                required_filled_and_copper_capped_planar=True,
                allowed_inner_corridor="In2.Cu",
                native_all_face_support_exclusion_preserved=True,
                switching_nets_not_added_to_corridor=True,
                remote_search_holds=holds,
                actual_thermal_void_network_must_be_recomputed=True,
                noise_and_startup_qualified=False,
                native_refill_and_connectivity_required=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Quiet SS capped barrel/corridor authored; no support/SW clearance relaxation", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    implement(p.parse_args().root)
