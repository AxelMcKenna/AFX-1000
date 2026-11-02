"""Complete the remaining 0.20 mm sense path with a 0.001 mm planning margin.

The project remains at 0.20 mm clearance. Native polygon capture is an outside
approximation; independent native DRC remains the acceptance check.
"""
import json
import time
import math
import uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
import hardware.fabrication.nf_minimum_logic as router
import hardware.fabrication.route_nf_surface as surface
from hardware.fabrication.audit_candidate import sha
ROOT=Path(__file__).resolve().parent
LAYERS=('F.Cu','In2.Cu','In3.Cu','In4.Cu','In5.Cu','B.Cu')


def run():
    cp=ROOT/'staging/nf-eight-cell-inputs-165/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());original=sexpr(board);count=len(board)
    router.WIDTH=surface.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=LAYERS
    screen=router.LayerScreen(c,signal_layers=LAYERS);net='/N12_BIAS_SENSE'
    path=screen.route(net,'In2.Cu',(16.9406,22.6269),'In2.Cu',(26.3209,32.0072),time.monotonic()+90,budget=350000)
    assert path,'No legal sense path found'
    runs,vias=router.simplify(screen,net,path)
    fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias)]
    for layer,points in runs:
        for start,end in zip(points,points[1:]):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:eight-sense:{sha(cp)}:{layer}:{start}:{end}'))
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),.2],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
    for pt in fresh:
        uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:eight-sense-via:{sha(cp)}:{pt}'))
        board.append([a('via'),[a('at'),*pt],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
    assert sexpr(board[:count])==original
    out=ROOT/'staging/nf-eight-sense-finish-01';out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,cp,Path(__file__),ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']},candidate_PCB_sha256=sha(pcb),net=net,runs=runs,new_vias_mm=fresh,
        width_mm=.2,project_clearance_mm=.2,numerical_planning_margin_mm=.001,planar_length_mm=sum(LineString(p).length for l,p in runs),
        all_source_objects_exact=True,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Routed sense path',len(runs),'layer runs;',len(fresh),'new vias')


if __name__=='__main__':run()
