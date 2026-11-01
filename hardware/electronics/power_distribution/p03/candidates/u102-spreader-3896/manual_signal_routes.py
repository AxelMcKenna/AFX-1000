"""Explicit local routing through actual terminal corridors, native checks mandatory."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr
from .route import PowerRouter, coded, named
from .spec import ROOT


def implement(root):
    path=root/"power_p03.kicad_pcb";raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    archive=root/"generated/history"/f"before-explicit-signals-{digest[:16]}.kicad_pcb.gz"
    if not archive.exists():archive.write_bytes(gzip.compress(raw,mtime=0))
    tree=coded(read_sexpr(raw.decode()));router=PowerRouter(tree)
    def pad(ref,pin):return next(p for p in router.by_ref[ref] if p["pin"]==pin and p["layers"])
    # The initial bend must leave the SS terminal horizontally before moving
    # up. A diagonal departure approaches adjacent SW copper too closely.
    ss=pad("U13","9");assert ss["net"]=="LO_P_SS"
    # Stop before the bare-metal support exclusion at(117,4). Continuing
    # horizontally to117 would violate its actual all-faceR3.7 keepout.
    ss_path=[ss["xy"],(111.2,7.7),(111.2,7.5),(113,7.5)]
    router.path(ss["net"],0,ss_path,.16)
    holds=[]
    for target in [pad("R49","2"),pad("C74","1")]:
        if not router.connect(dict(net=ss["net"],xy=ss_path[-1],layers=(0,)),target,.16):holds.append(target["ref"]+"."+target["pin"])
    # Both the configuration input and the true ground terminal need actual
    # copper. The chosen ground barrel is outside the opposite-face pad cage.
    p1,p2,cap=pad("U26","1"),pad("U26","2"),pad("C301","2")
    assert p1["net"]==p2["net"]==cap["net"]=="AGND"
    ground_path=[p2["xy"],p1["xy"],(p1["xy"][0],cap["xy"][1]),cap["xy"],(cap["xy"][0],14.25),(154,14.25)]
    router.path("AGND",5,ground_path,.25)
    assert router.safe_via("AGND",ground_path[-1],clearance=.16)
    router.via("AGND",ground_path[-1])
    path.write_text(sexpr(named(tree))+"\n")
    (root/"generated/explicit-local-signals.json").write_text(json.dumps(dict(before_pcb_sha256=digest,softstart_front_points_mm=ss_path,softstart_width_mm=.16,ground_back_points_mm=ground_path,ground_width_mm=.25,remote_search_holds=holds,native_clearance_refill_and_connectivity_required=True,clearance_relaxed=False,physical_qualified=False),indent=2)+"\n")
    print("Explicit SS escape and local Schmitt ground authored; native verification required",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=ROOT);implement(p.parse_args().root)
