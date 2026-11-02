"""Repair the four documented cross-branch routes on the combined eight-layer trial."""
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication import nf_minimum_logic as router,route_nf_surface as surface
from hardware.fabrication.nf_softstart_wide_screen import WideScreen
from hardware.fabrication.audit_candidate import sha


def run():
    root=Path(__file__).resolve().parent;cp=root/'staging/nf-eight-conflict-inputs-166/capture.json'
    c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text());original=sexpr(board);count=len(board)
    layers=('F.Cu','In2.Cu','In3.Cu','In4.Cu','In5.Cu','B.Cu')
    surface.SIGNAL_LAYERS=layers;surface.MARGIN=.001;surface.WIDTH=router.WIDTH=.2
    screen=WideScreen(c,signal_layers=layers);results=[];failed=[]
    def append(name,net,runs,vias):
        fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias+screen.new_vias)]
        assert all(screen.via_legal(net,p) for p in fresh)
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for start,end in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:8-combined:{sha(cp)}:{net}:{layer}:{start}:{end}'))
                board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for p in fresh:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:8-combined-via:{sha(cp)}:{net}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,p))
        results.append(dict(name=name,net=net,runs=runs,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in runs)))
        print('Routed',name,'vias',len(fresh),'length',round(results[-1]['planar_length_mm'],3),flush=True)
    # Preserve the checked front escape; use an inner detour instead of the old long perimeter route.
    net='/NF_NO_FAULT';escape=[[31.7,29.5],[32.,29.5],[32.,25.],[31.3,25.]]
    assert screen.legal(net,'F.Cu',escape) and screen.via_legal(net,escape[-1])
    append('fault front escape',net,[('F.Cu',escape)],[escape[-1]])
    tasks=[('fault inner link',net,'In5.Cu',[20.9,29.7],'In5.Cu',[31.3,25.]),
           ('C53 local reference','/N12_P03_SRC','In4.Cu',[22.3,26.4],'B.Cu',[31.25,32.75]),
           ('C54 local reference','/N12_P03_SRC','In5.Cu',[22.3,26.4],'B.Cu',[13.75,34.75]),
           ('bias sense','/N12_BIAS_SENSE','In2.Cu',[16.9406,22.6269],'In2.Cu',[26.3209,32.0072])]
    for name,net,layer,start,other,end in tasks:
        route=screen.route(net,layer,start,other,end,time.monotonic()+45,budget=220000)
        if route:
            runs,vias=router.simplify(screen,net,route);append(name,net,runs,vias)
        else:failed.append(name);print('No route',name,flush=True)
    assert sexpr(board[:count])==original
    out=root/'staging/nf-eight-conflict-routes-01';out.mkdir(exist_ok=False)
    pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,Path(__file__),root/'nf_minimum_logic.py',root/'route_nf_surface.py',root/'nf_softstart_cell_routes.py',root/'nf_softstart_joint_screen.py',root/'nf_softstart_wide_screen.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=results,failed=failed,
        all_source_objects_exact=True,new_width_mm=.2,new_via_mm=[.6,.3],native_checks_pending=True,material_stack_accepted=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
