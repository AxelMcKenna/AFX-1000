"""Require the joint source and receiving-end proposal to restore every cut net."""
import copy,json,time,math,uuid
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
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,CLOCK,LED
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';sp=ROOT/'staging/digital-serial1-joint-source-restoration-01/diagnosis.json';tp=ROOT/'staging/digital-serial1-data-placement-first-01/diagnosis.json'
    cap,source,target=[json.loads(p.read_text()) for p in (cp,sp,tp)]
    for r in (cap,source,target):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    selected_target=target['placement_and_local_escapes'];assert selected_target and source['selected_source_proposals']
    # This receipt selected the original pose. Preserve the exact footprint.
    pose=selected_target['pose'];assert pose['position_mm']==[75.,21.] and pose['angle']==0 and pose['side']=='B'
    removed=set(source['removed_uuids'])|set(target['removed_uuids']);work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    def crossings(s,n):
        return [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==n and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]+[(p,list(FACES)) for other,p in s.new_vias if other==n]
    ends={CLOCK:contacts(work,CLOCK,'R3016','2'),LED:contacts(work,LED,'J3005','1'),'/LED/LED_50':contacts(work,'/LED/LED_50','J3005','3'),'/CONTROLS/CONTROL_30':contacts(work,'/CONTROLS/CONTROL_30','U2003','3')}
    attempts=[];selected=None;deadline=time.monotonic()+360
    for si,source_proposal in enumerate(source['selected_source_proposals']):
        for ti,choice in enumerate(selected_target['packing']['choices']):
            if time.monotonic()>deadline:break
            def prepared():
                s=CloseMarginViaScreen(work,signal_layers=FACES);rs=[];via={}
                for r in source_proposal['routes']+selected_target['routes']:rs.append(add(s,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm'])))
                for name,index in zip(selected_target['packing']['names'],choice['indices']):
                    d=selected_target['domains'][name];o=d['options'][index];rs.append(add(s,d['net'],o));via[d['net']]=o['point']
                return s,rs,via
            screen,routes,vias=prepared()
            tasks=[(SERIAL,'F.Cu',source_proposal['serial_via'],{(f,tuple(vias[SERIAL])) for f in FACES}),
                   (CLOCK,'F.Cu',vias[CLOCK],ends[CLOCK]),(LED,'F.Cu',vias[LED],ends[LED]),
                   ('/LED/LED_50','In3.Cu',(73.5,21.598),ends['/LED/LED_50']),
                   ('/CONTROLS/CONTROL_30','F.Cu',(81.9,11.1),ends['/CONTROLS/CONTROL_30'])]
            attempt=dict(source_proposal=si,target_pack=ti,preflight=[],orders=[]);attempts.append(attempt)
            for net,face,start,targets in tasks:
                r=reachability(PlannedRegionScreen(screen,net),net,[(face,start)],sorted(targets),FACES,existing_crossings=crossings(screen,net))
                attempt['preflight'].append(dict(net=net,region_report=r))
                if not r['connected']:break
            print('Combined',si,ti,'access',[(r['net'],r['region_report']['connected']) for r in attempt['preflight']],flush=True)
            if len(attempt['preflight'])!=5 or not all(r['region_report']['connected'] for r in attempt['preflight']):continue
            for order in [(0,1,2,3,4),(1,2,0,3,4),(2,1,3,0,4),(3,4,1,2,0)]:
                screen,routes,vias=prepared();record=dict(order=order,repairs=[]);attempt['orders'].append(record)
                for i in order:
                    net,face,start,targets=tasks[i]
                    result=route(screen,net,face,start,targets,min(deadline,time.monotonic()+35),existing_crossings=crossings(screen,net))
                    record['repairs'].append(dict(net=net,found=bool(result)))
                    if not result:break
                    routes.append(add(screen,net,result))
                record['routes']=routes
                if len(record['repairs'])==5 and all(r['found'] for r in record['repairs']):selected=routes;break
            if selected:break
        if selected or time.monotonic()>deadline:break
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    paths=[cp,sp,tp,pcb,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_native_route_cleanup.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-combined-restoration-01';out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),attempts=attempts,candidate_emitted=bool(selected),native_rules_relaxed=False,fabrication_released=False)
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
                    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:SERIAL1-JOINT:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
            for p in r['new_vias_mm']:
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:SERIAL1-JOINT-via:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
        dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
        report.update(candidate_PCB_sha256=sha(dest),routes=selected,pruned_unused_vias=pruned,removed_objects=retired,geometry_delta=geometry_delta(original,board),native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Complete candidate emitted:',bool(selected),flush=True)

if __name__=='__main__':run()
