"""Isolated AUX-LDO spreading/landing trial; never promotes canonical copper.

The candidate moves three actual underside parts, adds a real six-layer AGND
spreader and nine filled/capped direct-EP vias. Native routing and the external
thermal/contact model must independently validate it before adoption.
"""
import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ...power_supply.place import overlap
from . import construction
from .route import PowerRouter, coded, named
from .spec import MOUNTS, ROOT
from .thermal import rect_zone

POSES = {"R110": (25, 15.2, 0, "B"), "R130": (25, 24.65, 0, "B"), "C109": (29, 25.45, 90, "B")}
TIM = [22.25, 16.5, 29.75, 23.5]
METAL = [23.25, 17.5, 28.75, 22.5]


def implement(destination, cli):
    assert destination.resolve() != ROOT.resolve()
    source_hash = hashlib.sha256((ROOT / "power_p03.kicad_pcb").read_bytes()).hexdigest()
    if destination.exists():
        raise FileExistsError("Preserve prior trial; select a new candidate path")
    destination.mkdir(parents=True)
    (destination / "generated/history").mkdir(parents=True)
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in {".py", ".json", ".csv", ".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"} or p.name in {"fp-lib-table", "sym-lib-table"}:
            shutil.copy2(p, destination / p.name)
    shutil.copytree(ROOT / "RMX_P03.pretty", destination / "RMX_P03.pretty")
    shutil.copy2(ROOT / "generated/netlist.xml", destination / "generated/netlist.xml")
    pcb = destination / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    router = PowerRouter(tree)
    parts = {p["ref"]: p for p in json.loads((ROOT / "components.json").read_text())}
    library = footprint_root(str(cli))
    oldpads = [p for ref in POSES for p in router.by_ref[ref] if p["layers"]]
    used = [(f"mount{i}", [x-3.7,y-3.7,x+3.7,y+3.7]) for i,(x,y) in enumerate(MOUNTS)] + [("U102_TIM", TIM)]
    for fp in list(children(tree, "footprint")):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in POSES:
            tree.remove(fp)
        elif first(fp, "layer")[1] == "B.Cu":
            used.append((ref, [x-100 for x in courtyard(fp, "B.CrtYd")]))
    for ref, pose in POSES.items():
        c = parts[ref]
        lib, name = c["footprint"].split(":")
        c = dict(c, value=c["part"], mpn=c["part"], nets={p["number"]:p["net"] for p in c["pins"]})
        fp = placed_footprint(c, pose, library/(lib+".pretty")/(name+".kicad_mod"), router.nets)
        box = [x-100 for x in courtyard(fp, "B.CrtYd")]
        assert not any(overlap(box,b,.15) for _,b in used), (ref, used)
        used.append((ref,box))
        tree.append(fp)
    after = PowerRouter(tree)
    relocated_pads = oldpads + [p for ref in POSES for p in after.by_ref[ref] if p["layers"]]
    displaced = []
    names = {str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    def remove_segment(obj, reason):
        tree.remove(obj)
        displaced.append(dict(net=names[str(first(obj,"net")[1])], layer=first(obj,"layer")[1], reason=reason))
    def distance(obj,xy):
        p,q = [tuple(float(v)-100 for v in first(obj,k)[1:3]) for k in ("start","end")]
        dx,dy=q[0]-p[0],q[1]-p[1]
        t=max(0,min(1,((xy[0]-p[0])*dx+(xy[1]-p[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
        return math.dist(xy,(p[0]+t*dx,p[1]+t*dy))
    for obj in list(children(tree,"segment")):
        if first(obj,"layer")[1] != "B.Cu":
            continue
        if any(distance(obj,p["xy"]) < max(p["size"])/2+.16+float(first(obj,"width")[1])/2 for p in relocated_pads):
            remove_segment(obj,"Removed old/new actual relocated-terminal attachments")
    # Replace only the U102 direct AGND array; retain the limiting U13 array.
    for via in list(children(tree,"via")):
        xy=tuple(float(v)-100 for v in first(via,"at")[1:3])
        if names[str(first(via,"net")[1])] == "AGND" and abs(xy[0]-26.25)<.9 and abs(xy[1]-20)<1:
            tree.remove(via)
    ep_sites=[(26.25+dx,20+dy) for dx in (-.5,0,.5) for dy in (-.5,0,.5)]
    for xy in ep_sites:
        r=PowerRouter(tree);full=r.geometry;r.geometry=[g for g in full if g["kind"]!="line"]
        assert r.safe_via("AGND",xy,diameter=.7,clearance=.16),(xy,"fixed EP conflict")
        for obj in list(children(tree,"segment")):
            if names[str(first(obj,"net")[1])] != "AGND" and distance(obj,xy)<.35+.16+float(first(obj,"width")[1])/2:
                remove_segment(obj,"Actual direct-EP barrel clearance")
        r=PowerRouter(tree)
        assert r.safe_via("AGND",xy,diameter=.7,clearance=.16)
        r.via("AGND",xy,diameter=.7)
    r=PowerRouter(tree)
    remote=[]
    for x in (22.9,24.15,25.4,26.65,27.9,29.15):
        for y in (17.15,18.4,19.65,20.9,22.15,22.9):
            if abs(x-26.25)<1.6 and abs(y-20)<1.6:
                continue  # Preserve a real fine-pin escape corridor.
            if r.safe_via("AGND",(x,y),clearance=.16):
                r.via("AGND",(x,y));remote.append((x,y))
    for layer in ("F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","B.Cu"):
        zone=rect_zone("AGND",r.nets["AGND"],layer,TIM)
        zone.extend([[a("name"),"P03_U102_TRIAL"],[a("priority"),a(4)]])
        tree.append(zone)
    pcb.write_text(sexpr(named(tree))+"\n")
    report=dict(base_canonical_pcb_sha256=source_hash,candidate_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
                native_local_poses_mm=POSES,tim_cutout_native_mm=[v+100 for v in TIM],metal_contact_native_mm=[v+100 for v in METAL],
                direct_ep_vias_mm=ep_sites,direct_land_mm=.7,finished_bore_mm=.25,via_wall_minimum_required_um=50,
                direct_land_extends_beyond_nominal_EP_by_mm=.01,remote_vias_mm=remote,
                displacement_obligations=displaced,clearance_relaxed=False,
                native_refill_erc_parity_routing_required=True,thermal_network_rerun_required=True,
                fabricator_dfm_approved=False,physical_qualified=False,build_ready=False)
    (destination/"generated/u102-candidate.json").write_text(json.dumps(report,indent=2)+"\n")
    previous=construction.ROOT
    try:
        construction.ROOT=destination
        construction.write_contract()
    finally:
        construction.ROOT=previous
    assert hashlib.sha256((ROOT/"power_p03.kicad_pcb").read_bytes()).hexdigest()==source_hash
    print("Separate U102 actual spreader candidate authored",destination,"remote vias",len(remote),"native checks required",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destination",type=Path,required=True)
    p.add_argument("--kicad-cli",type=Path,required=True)
    args=p.parse_args();implement(args.destination,args.kicad_cli)
