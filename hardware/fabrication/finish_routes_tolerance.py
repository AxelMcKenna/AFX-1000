"""Near-boundary search hypotheses; unchanged native rules decide acceptance."""

import argparse
import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.geometry import LineString

from hardware.electronics.common.sexpr import a, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_layers import simplify
from hardware.fabrication.search_screen import CandidateScreen

ROOT = Path(__file__).resolve().parent


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture",required=True)
    parser.add_argument("--label",required=True)
    parser.add_argument("--nets",nargs="+",required=True)
    args = parser.parse_args()
    for label in (args.capture,args.label):
        assert label and all(c.isalnum() or c in "-_" for c in label)
    capture_path = ROOT/"staging"/args.capture/"capture.json"
    output = ROOT/"staging"/args.label
    assert not output.exists()
    capture = json.loads(capture_path.read_text())
    assert all(sha(Path(p)) == digest for p,digest in capture["source_sha256"].items())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    board = read_sexpr(source.read_text())
    original, length = sexpr(board),len(board)
    objects = {p["uuid"]:p for p in capture["objects"]}
    nets,endpoints = {},{}
    for key,ids in capture["groups"].items():
        net = objects[ids[0]]["net"]
        if net not in args.nets:
            continue
        nets.setdefault(net,[]).append(key)
        points = set()
        for uid in ids:
            item = objects[uid]
            for layer in ("F.Cu","B.Cu"):
                if layer in item["layers"]:
                    for xy in [item["position_mm"]]+([item["end_mm"]] if "end_mm" in item else []):
                        points.add((layer,tuple(xy)))
        endpoints[key] = points
    tasks = []
    for net,keys in nets.items():
        for left,right in itertools.combinations(keys,2):
            choices = sorted((math.dist(p,q)+(.25 if layer != other else 0),layer,p,other,q)
                for layer,p in endpoints[left] for other,q in endpoints[right])
            tasks.append((choices[0][0],net,left,right,choices[:4]))
    screen = CandidateScreen(capture,signal_layers=("F.Cu","B.Cu"))
    parent = {k:k for k in endpoints}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    results = []
    deadline = time.monotonic()+120
    for _,net,left,right,choices in sorted(tasks):
        if root(left) == root(right) or time.monotonic() >= deadline:
            continue
        path = None
        for _,layer,start,other,end in choices:
            path = screen.route(net,layer,start,other,end,min(deadline,time.monotonic()+4),budget=45000)
            if path:
                break
        if not path:
            results.append(dict(net=net,groups=[left,right],connected=False))
            print(net,"bounded route not found",flush=True)
            continue
        runs,vias = simplify(screen,net,path)
        new_vias = [p for p in vias if not any(n == net and math.dist(p,q) < 1e-7 for n,q in screen.vias+screen.new_vias)]
        assert all(screen.via_legal(net,p) for p in new_vias)
        for layer,points in runs:
            assert layer in ("F.Cu","B.Cu")
            for start,end in zip(points,points[1:]):
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:finish-tolerance:final:{sha(capture_path)}:{net}:{layer}:{start}:{end}"))
                board.append([a("segment"),[a("start"),*start],[a("end"),*end],[a("width"),.2],
                    [a("layer"),layer],[a("net"),net],[a("uuid"),ident]])
            screen.added.append((net,layer,LineString(points)))
        for point in new_vias:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:finish-tolerance:finalvia:{sha(capture_path)}:{net}:{point}"))
            board.append([a("via"),[a("at"),*point],[a("size"),.65],[a("drill"),.3],
                [a("layers"),"F.Cu","B.Cu"],[a("tenting"),[a("front"),a("yes")],[a("back"),a("yes")]],
                [a("net"),net],[a("uuid"),ident]])
            screen.new_vias.append((net,point))
        parent[root(right)] = root(left)
        results.append(dict(net=net,groups=[left,right],connected=True,runs=runs,new_vias_mm=new_vias))
        print(net,"planned",len(runs),"layer runs",len(new_vias),"new vias",flush=True)
    assert sexpr(board[:length]) == original
    unique = {}
    deduplicated = []
    for node in board:
        if isinstance(node,list) and node and node[0] in ("segment","via"):
            uid = str(first(node,"uuid")[1])
            if uid in unique:
                assert sexpr(node) == unique[uid]
                continue
            unique[uid] = sexpr(node)
        deduplicated.append(node)
    board = deduplicated
    assert sexpr(board[:length]) == original
    output.mkdir()
    pcb = output/source.name
    pcb.write_text(sexpr(board)+"\n")
    inputs = (source,capture_path,Path(__file__),ROOT/"route_nf_layers.py",ROOT/"route_nf_surface.py",ROOT/"search_screen.py")
    (output/"construction.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        candidate_PCB_sha256=sha(pcb),results=results,all_original_authored_objects_exact=True,
        only_F_B_signal_layers=True,search_polygon_uncertainty_mm=.002,unchanged_native_clearance_mm=.2,native_checks_pending=True,power_noise_qualified=False,
        fabrication_released=False),indent=2)+"\n")


if __name__ == "__main__":
    run()
