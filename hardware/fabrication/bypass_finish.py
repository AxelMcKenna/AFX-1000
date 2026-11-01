"""Explicit F/B routing of the last E11 supply and status gaps."""

import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.geometry import LineString

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_layers import LayerScreen, simplify

ROOT = Path(__file__).resolve().parent
CAPTURE = ROOT/"staging/bypass-routing-inputs-4/capture.json"
OUTPUT = ROOT/"staging/bypass-final-routes-01"


def run():
    assert not OUTPUT.exists()
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == digest for p,digest in capture["source_sha256"].items())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    board = read_sexpr(source.read_text())
    original, length = sexpr(board),len(board)
    objects = {p["uuid"]:p for p in capture["objects"]}
    nets,endpoints = {},{}
    for key,ids in capture["groups"].items():
        net = objects[ids[0]]["net"]
        assert net in ("/3V3","/5V","/INPUT_READY")
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
            tasks.append((choices[0][0],net,left,right,choices[:8]))
    screen = LayerScreen(capture,signal_layers=("F.Cu","B.Cu"))
    parent = {k:k for k in endpoints}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    results = []
    deadline = time.monotonic()+200
    for _,net,left,right,choices in sorted(tasks):
        if root(left) == root(right) or time.monotonic() >= deadline:
            continue
        path = None
        for _,layer,start,other,end in choices:
            path = screen.route(net,layer,start,other,end,min(deadline,time.monotonic()+35),budget=120000)
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
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E11:final:{sha(CAPTURE)}:{net}:{layer}:{start}:{end}"))
                board.append([a("segment"),[a("start"),*start],[a("end"),*end],[a("width"),.2],
                    [a("layer"),layer],[a("net"),net],[a("uuid"),ident]])
            screen.added.append((net,layer,LineString(points)))
        for point in new_vias:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E11:finalvia:{sha(CAPTURE)}:{net}:{point}"))
            board.append([a("via"),[a("at"),*point],[a("size"),.65],[a("drill"),.3],
                [a("layers"),"F.Cu","B.Cu"],[a("tenting"),[a("front"),a("yes")],[a("back"),a("yes")]],
                [a("net"),net],[a("uuid"),ident]])
            screen.new_vias.append((net,point))
        parent[root(right)] = root(left)
        results.append(dict(net=net,groups=[left,right],connected=True,runs=runs,new_vias_mm=new_vias))
        print(net,"planned",len(runs),"layer runs",len(new_vias),"new vias",flush=True)
    assert sexpr(board[:length]) == original
    OUTPUT.mkdir()
    pcb = OUTPUT/source.name
    pcb.write_text(sexpr(board)+"\n")
    inputs = (source,CAPTURE,Path(__file__),ROOT/"route_nf_layers.py",ROOT/"route_nf_surface.py")
    (OUTPUT/"construction.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        candidate_PCB_sha256=sha(pcb),results=results,all_original_authored_objects_exact=True,
        only_F_B_signal_layers=True,native_checks_pending=True,power_noise_qualified=False,
        fabrication_released=False),indent=2)+"\n")


if __name__ == "__main__":
    run()
