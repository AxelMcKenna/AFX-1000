"""Coordinated CT/reset escapes followed by width-preserving sense/supply repair."""
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,read_sexpr,sexpr
import hardware.fabrication.nf_minimum_logic as router
import hardware.fabrication.route_nf_surface as surface
from hardware.fabrication.audit_candidate import sha
ROOT=Path(__file__).resolve().parent
LAYERS=('F.Cu','In2.Cu','In3.Cu','B.Cu')


def run():
    cp=ROOT/'staging/nf-ct-cell-inputs-172/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text())
    output=ROOT/'staging/nf-ct-cell-routes-02';assert not output.exists()
    pads={(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'}
    screen=router.LayerScreen(c);reserved=[('/N12_BIAS_CT',(20.3,23.8)),('/N12_VIN_VALID_CT',(20.3,26.5))]
    for net,xy in reserved:
        print('CT via site',net,xy,screen.via_legal(net,xy),flush=True)
        assert screen.via_legal(net,xy)
        screen.new_vias.append((net,xy))
    results=[];failed=[];emitted=set()
    def commit(name,net,path,width):
        runs,vias=router.simplify(screen,net,path)
        fresh=[p for p in vias if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias) and (net,tuple(p)) not in emitted]
        for layer,points in runs:
            screen.added.append((net,layer,LineString(points)))
            for start,end in zip(points,points[1:]):
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:cell-v2:{sha(cp)}:{net}:{layer}:{start}:{end}'))
                board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),width],[a('layer'),layer],[a('net'),net],[a('uuid'),uid]])
        for pt in fresh:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:NF:cell-via-v2:{sha(cp)}:{net}:{pt}'))
            board.append([a('via'),[a('at'),*pt],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('tenting'),[a('front'),a('yes')],[a('back'),a('yes')]],[a('net'),net],[a('uuid'),uid]])
            if (net,pt) not in screen.new_vias:screen.new_vias.append((net,pt))
            emitted.add((net,tuple(pt)))
        results.append(dict(name=name,net=net,width_mm=width,runs=runs,new_vias_mm=fresh,planar_length_mm=sum(LineString(p).length for l,p in runs)))
        print('Routed',name,'length',round(results[-1]['planar_length_mm'],3),'vias',len(fresh),flush=True)
    def via_route(name,net,start,end,end_layer,via_choices):
        for via in via_choices:
            if not screen.via_legal(net,via):continue
            screen.signal_layers=('F.Cu',)
            head=screen.route(net,'F.Cu',start,'F.Cu',via,time.monotonic()+2,budget=35000)
            screen.signal_layers=LAYERS
            if not head:continue
            if (net,via) not in screen.new_vias:screen.new_vias.append((net,via))
            for layer in (('In2.Cu','In3.Cu','B.Cu') if 'reset' in name else ('B.Cu','In3.Cu','In2.Cu')):
                tail=screen.route(net,layer,via,end_layer,end,time.monotonic()+4,budget=60000)
                if tail:
                    commit(name,net,head+tail,.16);return True
            if (net,via) not in reserved:screen.new_vias.remove((net,via))
        failed.append(name);print('No complete route',name,flush=True);return False
    # Keep reset exits away from the reserved CT vias.
    for owner,end,centre in [('U25',(21.3312,23.5276),(18.8,22.8)),('U26',(20.2618,27.9753),(19.4,25.3))]:
        p=pads[owner,'6'];choices=sorted({(round(centre[0]+dx/10,6),round(centre[1]+dy/10,6)) for dx in range(-5,6) for dy in range(-5,6)},key=lambda pt:math.dist(pt,centre))
        direct=screen.route(p['net'],'F.Cu',p['position_mm'],'F.Cu',end,time.monotonic()+10,budget=100000) if owner=='U25' else None
        if direct:commit(owner+' reset',p['net'],direct,.16)
        else:via_route(owner+' reset',p['net'],p['position_mm'],end,'B.Cu',choices)
    for (net,via),ref,owner in reversed(list(zip(reserved,['C37','C35'],['U25','U26']))):
        via_route(ref+' CT',net,pads[owner,'5']['position_mm'],pads[ref,'1']['position_mm'],'B.Cu',[via])
    # Restore the original 0.20 mm widths on these logic/sense/supply segments.
    router.WIDTH=surface.WIDTH=.2
    old=screen;screen=router.LayerScreen(c);screen.added=old.added;screen.new_vias=old.new_vias
    tasks=[
        ('permit','/N12_PERMIT_D','In2.Cu',(18.9214,22.7002),'In2.Cu',(20.7,24.4788)),
        ('bias sense','/N12_BIAS_SENSE','In2.Cu',(16.9406,22.6269),'In2.Cu',(26.3209,32.0072)),
        ('INTVCC branch','/N12_INTVCC','In2.Cu',(19.725,27.15),'In2.Cu',(24.8825,31.65)),
        ('INTVCC local link','/N12_INTVCC','In3.Cu',(19.775,24.5),'In3.Cu',(19.725,27.15))]
    tasks[0],tasks[1]=tasks[1],tasks[0]
    for name,net,layer,start,other,end in tasks:
        path=screen.route(net,layer,start,other,end,time.monotonic()+30,budget=180000)
        if path:commit(name,net,path,.2)
        else:failed.append(name);print('No route',name,flush=True)
    output.mkdir();pcb=output/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,Path(__file__),ROOT/'nf_minimum_logic.py',ROOT/'route_nf_surface.py']
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),routes=results,failed=failed,new_via_mm=[.6,.3],
        native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Completed',len(results),'tasks; failed',failed)


if __name__=='__main__':run()
