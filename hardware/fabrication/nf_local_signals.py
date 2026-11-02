"""Bounded additive NF signal closure; no new vias, force copper or plane tracks.

Timing/sensing routes are limited to short local paths. Native DRC, circuit
parity, per-net connectivity and integrated analog/noise review remain gates.
"""
import argparse
import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.geometry import LineString

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import Screen, SIGNAL_LAYERS, candidate_paths
from hardware.fabrication.routing_nets import is_logic_net

ROOT = Path(__file__).resolve().parent
LOCAL_SUFFIXES = ('_CT','_CWD','_TMR','_SS','_RAMP','_F_TIMEOUT','_F_OUTPUT',
                  '_HOST5','_RESET_N','_UV_GOOD','_OV_GOOD','_UV_REF','_OV_REF',
                  '_UV_RMID','_UV_SENSE','_OV_SENSE','_OUT_SUM','_OV_OK')


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture',required=True)
    parser.add_argument('--label',required=True)
    args = parser.parse_args()
    assert all(n and all(c.isalnum() or c in '-_' for c in n) for n in (args.capture,args.label))
    capture_path = ROOT/'staging'/args.capture/'capture.json'
    c = json.loads(capture_path.read_text())
    assert all(sha(Path(p)) == h for p,h in c['source_sha256'].items())
    source = next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    original, count = sexpr(board),len(board)
    objects = {o['uuid']:o for o in c['objects']}
    nets, endpoints = {},{}
    for key,ids in c['groups'].items():
        net = objects[ids[0]]['net']
        if not (is_logic_net(net) or net.endswith(LOCAL_SUFFIXES)):
            continue
        nets.setdefault(net,[]).append(key)
        contacts = set()
        for uid in ids:
            obj=objects[uid]
            for layer in obj['layers']:
                if layer in SIGNAL_LAYERS:
                    for xy in [obj['position_mm']]+([obj['end_mm']] if 'end_mm' in obj else []):
                        contacts.add((layer,tuple(xy)))
        endpoints[key] = contacts
    tasks=[]
    for net,keys in nets.items():
        limit=30 if is_logic_net(net) else 8
        for left,right in itertools.combinations(keys,2):
            pairs=sorted((math.dist(p,q),layer,p,q) for layer,p in endpoints[left]
                         for other,q in endpoints[right] if layer==other and math.dist(p,q)<=limit)
            if pairs:
                tasks.append((pairs[0][0],net,left,right,pairs[:32],limit))
    screen=Screen(c)
    parent={k:k for k in endpoints}
    def root(k):
        while parent[k]!=k:
            k=parent[k]
        return k
    results=[]
    deadline=time.monotonic()+90
    for _,net,left,right,pairs,limit in sorted(tasks):
        if root(left)==root(right):
            continue
        if time.monotonic()>deadline:
            break
        chosen=None
        for _,layer,start,end in pairs:
            for path in candidate_paths(start,end):
                path=[p for i,p in enumerate(path) if not i or p!=path[i-1]]
                if sum(math.dist(p,q) for p,q in zip(path,path[1:]))<=limit and screen.legal(net,layer,path):
                    chosen=layer,path
                    break
            if chosen:
                break
        if chosen is None:
            continue
        layer,path=chosen
        for start,end in zip(path,path[1:]):
            ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:local-signal:{sha(source)}:{net}:{layer}:{start}:{end}'))
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],
                          [a('layer'),layer],[a('net'),net],[a('uuid'),ident]])
        screen.added.append((net,layer,LineString(path)))
        parent[root(right)]=root(left)
        results.append(dict(net=net,groups=[left,right],layer=layer,points_mm=path,
                            length_mm=sum(math.dist(p,q) for p,q in zip(path,path[1:])),maximum_length_mm=limit))
        print('Planned',net,layer,results[-1]['length_mm'],flush=True)
    assert sexpr(board[:count])==original
    output=ROOT/'staging'/args.label
    output.mkdir(exist_ok=False)
    pcb=output/source.name
    pcb.write_text(sexpr(board)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in (source,capture_path,Path(__file__),ROOT/'route_nf_surface.py',ROOT/'routing_nets.py')},
        candidate_PCB_sha256=sha(pcb),routes=results,all_original_authored_objects_exact=True,
        no_new_vias_or_reserved_plane_tracks=True,route_count=len(results),native_checks_pending=True,
        integrated_timing_noise_fault_review_required=True,fabrication_released=False),indent=2)+'\n')
    print('Planned',len(results),'local signal connections')


if __name__ == '__main__':
    run()
