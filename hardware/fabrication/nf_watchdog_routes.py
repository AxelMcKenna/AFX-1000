"""Route only the relocated watchdog timing capacitors and their ground escapes."""
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
from hardware.fabrication.nf_minimum_logic import LayerScreen,simplify,sha,WIDTH,DIAMETER,DRILL
from hardware.fabrication.route_nf_surface import shape,candidate_paths

ROOT=Path(__file__).resolve().parent


def run():
    capture_path=ROOT/'staging/nf-watchdog-placement-inputs-172/capture.json'
    capture=json.loads(capture_path.read_text())
    assert all(sha(Path(p))==digest for p,digest in capture['source_sha256'].items())
    source=next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board=read_sexpr(source.read_text());original=sexpr(board);count=len(board)
    output=ROOT/'staging/nf-watchdog-routes-01';assert not output.exists()
    screen=LayerScreen(capture,signal_layers=('F.Cu','B.Cu'))
    pads={(o['ref'],o['pin']):o for o in capture['objects'] if o['kind']=='PAD'}
    results=[]
    def append(net,runs,vias):
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for start,end in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:local-watchdog:{sha(capture_path)}:{net}:{layer}:{start}:{end}'))
                board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),WIDTH],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for point in vias:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:local-watchdog-via:{sha(capture_path)}:{net}:{point}'))
            board.append([a('via'),[a('at'),*point],[a('size'),DIAMETER],[a('drill'),DRILL],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            screen.new_vias.append((net,point))
        results.append(dict(net=net,runs=runs,new_vias_mm=vias,planar_length_mm=sum(LineString(p).length for l,p in runs)))
    for ref,owner in [('C1','U3'),('C2','U9')]:
        cap,target=pads[(ref,'1')],pads[(owner,'2')];net=cap['net'];assert net==target['net']
        path=screen.route(net,'F.Cu',target['position_mm'],'B.Cu',cap['position_mm'],time.monotonic()+30,budget=90000)
        if path:
            runs,vias=simplify(screen,net,path)
            fresh=[v for v in vias if not any(n==net and math.dist(v,p)<1e-7 for n,p in screen.vias+screen.new_vias)]
            assert all(screen.via_legal(net,v) for v in fresh)
            append(net,runs,fresh)
        print(ref,'timing routed',bool(path),flush=True)
    ground=shape([p for z in capture['zones'] if z['layer']=='In1.Cu' and z['net']=='/AGND' and not z['keepout'] for p in z['polygons']])
    ground = ground.buffer(-.35)
    for ref in ['C1','C2']:
        cap=pads[(ref,'2')];start=cap['position_mm'];net=cap['net'];assert net=='/AGND'
        choices=[]
        for ix in range(-25,26):
            for iy in range(-25,26):
                pt=tuple(round(v+d/10,6) for v,d in zip(start,(ix,iy)))
                if math.dist(start,pt)<.8 or not ground.covers(Point(pt)) or not screen.via_legal(net,pt):continue
                for path in candidate_paths(start,pt):
                    if screen.legal(net,'B.Cu',path):
                        choices.append((LineString(path).length,pt,path));break
        if choices:
            _,pt,path=min(choices)
            append(net,[('B.Cu',path)],[pt])
        print(ref,'ground routed',bool(choices),flush=True)
    assert sexpr(board[:count])==original
    output.mkdir();pcb=output/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,capture_path,Path(__file__),ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=results,
        all_input_objects_exact=True,new_width_mm=WIDTH,new_via_mm=[DIAMETER,DRILL],native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
