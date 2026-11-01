"""Minimal P19 monitor repair using a real filled/capped SSOP via-in-pad.

The .55/.20 via preserves .160 mm nominal copper clearance at the actual .635
SSOP pitch and .175 mm native annulus. It introduces an explicit .20 mm finished
hole requirement. C50 preplate ring is .125 mm at minimum50µm wall, just like the
existing .60/.25 vias; no fabrication tolerance/acceptance is inferred.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
from .quiet_crossover import CORRIDORS, CrossoverRouter
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root):
    pcb = root / "power_p03.kicad_pcb"
    raw = pcb.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = root / "generated/history" / f"before-p19-vip-{digest[:16]}.pcb.gz"
    if not archive.exists():
        archive.write_bytes(gzip.compress(raw, mtime=0))
    tree = coded(read_sexpr(raw.decode()))
    r = PowerRouter(tree)
    net = "P03_MON_P19"
    vip = (143.375, 10.9525)
    bottom = (144.15, 13.7)
    # Only a sub-picometre floating-point comparison epsilon is used here;
    # the actual native DRC requirement remains exactly .160 mm.
    assert r.safe_via(net, vip, diameter=0.55, clearance=0.16 - 1e-10), "SSOP VIP has a physical obstacle"
    assert r.safe_via(net, bottom, diameter=0.6, clearance=0.16), "Bottom monitor escape is blocked"
    tree.append(
        read_sexpr(
            f'(via (at {vip[0] + 100} {vip[1] + 100}) (size .55) (drill .20) (layers "F.Cu" "B.Cu") (free yes) (net {r.nets[net]}))'
        )
    )
    r = PowerRouter(tree)
    r.via(net, bottom)
    source = next(p for p in r.by_ref["R305"] if p["pin"] == "1")
    local = r.connect(source, dict(net=net, xy=bottom, layers=(5,)), 0.16)
    joins = []
    for a, b in [(vip, bottom), (bottom, (146.125, 6.25))]:
        r = PowerRouter(tree)
        r.max_search_nodes = 600000
        ok = r.connect(
            dict(net=net, xy=a, layers=tuple(range(6))), dict(net=net, xy=b, layers=tuple(range(6))), 0.16
        )
        if not ok:
            # A declared quiet crossover may use In1 while every physical
            # obstacle and the U13 field exclusion remains active.
            CORRIDORS[net] = [(0.6, 0.6, 159.4, 44.4)]
            r = CrossoverRouter(tree)
            r.only_in1 = True
            r.max_search_nodes = 1000000
            ok = r.connect(dict(net=net, xy=a, layers=(1,)), dict(net=net, xy=b, layers=(1,)), 0.16)
        joins.append(dict(endpoints_mm=[a, b], joined=ok, routes=r.routes))
        print("P19 VIP monitor join", ok, flush=True)
    pcb.write_text(sexpr(named(tree)) + "\n")
    project = root / "power_p03.kicad_pro"
    pro = json.loads(project.read_text())
    old = pro["board"]["design_settings"]["rules"]["min_through_hole_diameter"]
    assert old in (0.20, 0.25)
    pro["board"]["design_settings"]["rules"]["min_through_hole_diameter"] = 0.20
    project.write_text(json.dumps(pro, indent=2) + "\n")
    (root / "generated/p19-vip.json").write_text(
        json.dumps(
            dict(
                before_pcb_sha256=digest,
                via_in_pad=dict(
                    ref="U25",
                    pin="3",
                    net=net,
                    centre_mm=vip,
                    land_mm=0.55,
                    finished_bore_mm=0.20,
                    native_annulus_mm=0.175,
                    preplate_ring_at_50um_wall_mm=0.125,
                    adjacent_pad_nominal_clearance_mm=0.160,
                ),
                bottom_barrel_mm=bottom,
                bottom_local_joined=local,
                interconnects=joins,
                prior_finished_hole_minimum_mm=old,
                new_finished_hole_minimum_required_mm=0.20,
                filled_resin_and_copper_cap_planarization_required=True,
                native_copper_clearance_requirement_mm=0.16,
                no_foreign_copper_removed=True,
                clearance_relaxed=False,
                new_fabricator_process_acceptance_required=True,
                fabricator_dfm_approved=False,
                native_refill_and_connectivity_required=True,
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
