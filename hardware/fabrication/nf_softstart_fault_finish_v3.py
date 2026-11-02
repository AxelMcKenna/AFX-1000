"""Repair one displaced fault-status path without moving any saved objects."""
import json
import time
import math
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication import nf_minimum_logic as router,route_nf_surface as surface
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen as JointScreen
from hardware.fabrication.audit_candidate import sha


def run():
    root=Path(__file__).resolve().parent
    path=root/'staging/nf-softstart-cell-inputs-164/capture.json';c=json.loads(path.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text());old=sexpr(board);count=len(board)
    router.WIDTH=surface.WIDTH=.2;surface.MARGIN=.001
    screen=JointScreen(c);net='/NF_NO_FAULT';start=[20.9,29.7];end=[31.7,29.5]
    escape=[[31.7,29.5],[32.0,29.5],[32.0,25.0],[31.3,25.0]]
    assert screen.legal(net,'F.Cu',escape) and screen.via_legal(net,escape[-1])
    screen.new_vias.append((net,escape[-1]))
    route=screen.route(net,'In2.Cu',start,'In2.Cu',escape[-1],time.monotonic()+50,budget=200000)
    if not route:print('No complete fault detour');return
    runs,vias=router.simplify(screen,net,route)
    runs.append(('F.Cu',escape));vias=sorted(set(tuple(p) for p in vias+[escape[-1]]))
    fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias)]
    for layer,points in runs:
        for p,q in zip(points,points[1:]):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:SS-fault:{sha(path)}:{layer}:{p}:{q}'))
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
    for p in fresh:
        assert screen.via_legal(net,p)
        uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:SS-fault-via:{sha(path)}:{p}'))
        board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
    assert sexpr(board[:count])==old
    folder=root/'staging/nf-softstart-fault-finish-03';folder.mkdir(exist_ok=False)
    pcb=folder/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,path,Path(__file__),root/'nf_softstart_cell_routes.py',root/'nf_softstart_joint_screen.py',root/'nf_minimum_logic.py',root/'route_nf_surface.py']
    (folder/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),net=net,runs=runs,new_vias_mm=fresh,all_original_objects_exact=True,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Routed fault detour',runs,'new vias',fresh)


if __name__=='__main__':run()
