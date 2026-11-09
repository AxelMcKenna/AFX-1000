"""Restore every remaining branch after the source-bound SERIAL_1/DATA cut.

Emit a board only after all five remaining restorations pass the routing screen.
Native DRC and independent pad-group replay are still required for adoption.
"""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-data-cutset-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    assert recipe['serial_continuation']
    removed=set(recipe['base_removed_uuids']+recipe['selected_extra_uuids']);work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    fixed=recipe['fixed_routes']+[recipe['serial_continuation']]
    tasks=[
        ('data','/LED/DATA_5V_SRC','B.Cu',(74.175,21.),contacts(work,'/LED/DATA_5V_SRC','U3005','21')),
        ('permit trunk',PERMIT,'In5.Cu',(45.,13.8),contacts(work,PERMIT,'U1001','36')),
        ('led37','/LED/LED_37','F.Cu',(44.,21.225),contacts(work,'/LED/LED_37','J3002','23')),
        ('led50','/LED/LED_50','In3.Cu',(73.5,21.598),contacts(work,'/LED/LED_50','J3005','3')),
        ('control30','/CONTROLS/CONTROL_30','F.Cu',(81.9,11.1),contacts(work,'/CONTROLS/CONTROL_30','U2003','3')),
    ]
    def prepared():
        screen=CloseMarginViaScreen(work,signal_layers=FACES);routes=[]
        for r in fixed:routes.append(add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm'])))
        return screen,routes
    def crossings(screen,net):
        return [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]+[(p,list(FACES)) for n,p in screen.new_vias if n==net]
    screen,_=prepared();preflight=[]
    for name,net,face,start,ends in tasks:
        result=reachability(PlannedRegionScreen(screen,net),net,[(face,start)],sorted(ends),FACES,existing_crossings=crossings(screen,net))
        preflight.append(dict(task=name,region_report=result));print(name,'fixed-prefix access',result['connected'],flush=True)
    attempts=[];selected=None;deadline=time.monotonic()+240
    if all(r['region_report']['connected'] for r in preflight):
        for order in [(0,1,2,3,4),(0,3,2,1,4),(2,3,0,4,1),(4,0,1,2,3),(3,4,2,0,1),(1,2,3,4,0)]:
            if time.monotonic()>deadline:break
            screen,routes=prepared();attempt=dict(order=[tasks[i][0] for i in order],repairs=[]);attempts.append(attempt)
            for i in order:
                name,net,face,start,ends=tasks[i]
                result=route(screen,net,face,start,ends,min(deadline,time.monotonic()+40),existing_crossings=crossings(screen,net))
                entry=dict(task=name,found=bool(result));attempt['repairs'].append(entry)
                if result:
                    added=add(screen,net,result);routes.append(added);entry.update(planar_length_mm=added['planar_length_mm'],new_vias=len(added['new_vias_mm']))
                print(entry,flush=True)
                if not result:break
            attempt['routes']=routes
            if len(attempt['repairs'])==5 and all(r['found'] for r in attempt['repairs']):selected=routes;break
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    paths=[cp,rp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_serial1_joint_repair.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_native_route_cleanup.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-data-restoration-01';out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),preflight=preflight,attempts=attempts,candidate_emitted=bool(selected),native_rules_relaxed=False,fabrication_released=False)
    if selected:
        original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
        retired=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in removed]
        assert len(retired)==len(removed)
        for n in retired:board.remove(n)
        selected,pruned=prune_single_face_vias(work,selected)
        for r in selected:
            for face,path in r['runs']:
                for p,q in zip(path,path[1:]):
                    if math.dist(p,q)<1e-7:continue
                    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:SERIAL1-DATA:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
            for p in r['new_vias_mm']:
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:SERIAL1-DATA-via:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
        dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
        report.update(candidate_PCB_sha256=sha(dest),routes=selected,pruned_unused_vias=pruned,removed_objects=retired,geometry_delta=geometry_delta(original,board),native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Candidate emitted:',bool(selected),flush=True)
if __name__=='__main__':run()
