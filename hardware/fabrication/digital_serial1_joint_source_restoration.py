"""Restore MCU branches and LED37 from a jointly packed source-side escape set."""
import copy,json,time
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';sp=ROOT/'staging/digital-serial1-three-source-escape-01/diagnosis.json';pp=ROOT/'staging/digital-serial1-joint-three-source-pack-01/diagnosis.json'
    cap,source,packed=[json.loads(p.read_text()) for p in (cp,sp,pp)]
    for r in (cap,source,packed):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    assert source['removed_uuids']==packed['removed_uuids']
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in source['removed_uuids']]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    destinations={PERMIT:contacts(work,PERMIT,'J1003','3')|contacts(work,PERMIT,'U1001','36'),'/LED/LED_37':contacts(work,'/LED/LED_37','J3002','23')}
    trunk_ends=contacts(work,PERMIT,'U1001','36');serial_ends=contacts(work,SERIAL,'U3003','4')
    def crossings(s,n):
        return [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==n and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]+[(p,list(FACES)) for other,p in s.new_vias if other==n]
    attempts=[];selected=[];deadline=time.monotonic()+360
    for choice_index,choice in enumerate(packed['packing']['choices']):
        if time.monotonic()>deadline:break
        def prepared():
            s=CloseMarginViaScreen(work,signal_layers=FACES);rs=[];vias={}
            for name,index in zip(packed['packing']['names'],choice['indices']):
                d=source['domains'][name];option=d['options'][index];rs.append(add(s,d['net'],option));vias[d['net']]=option['point']
            return s,rs,vias
        screen,routes,vias=prepared();preflight=[]
        for net in [PERMIT,'/LED/LED_37']:
            r=reachability(PlannedRegionScreen(screen,net),net,[('F.Cu',vias[net])],sorted(destinations[net]),FACES,existing_crossings=crossings(screen,net))
            preflight.append(dict(net=net,region_report=r))
            if not r['connected']:break
        attempt=dict(choice_index=choice_index,preflight=preflight,orders=[]);attempts.append(attempt)
        print('Source pack',choice_index,'restoration access',[(r['net'],r['region_report']['connected']) for r in preflight],flush=True)
        if not all(r['region_report']['connected'] for r in preflight) or len(preflight)!=2:continue
        for order in [(PERMIT,'/LED/LED_37'),('/LED/LED_37',PERMIT)]:
            screen,routes,vias=prepared();record=dict(order=order,repairs=[]);attempt['orders'].append(record)
            tasks=[(net,'F.Cu',vias[net],destinations[net]) for net in order]+[(PERMIT,'In5.Cu',(45.,13.8),trunk_ends)]
            for net,face,start,ends in tasks:
                result=route(screen,net,face,start,ends,min(deadline,time.monotonic()+30),existing_crossings=crossings(screen,net))
                record['repairs'].append(dict(net=net,found=bool(result)))
                if not result:break
                routes.append(add(screen,net,result))
            record['routes']=routes
            if len(routes)!=6:continue
            r=reachability(PlannedRegionScreen(screen,SERIAL),SERIAL,[('F.Cu',vias[SERIAL])],sorted(serial_ends),FACES,existing_crossings=crossings(screen,SERIAL))
            record['serial_region_report']=r
            if r['connected']:
                selected.append(dict(choice_index=choice_index,routes=routes,serial_via=vias[SERIAL]));print('Both MCU branches and LED37 restored; serial access retained',flush=True);break
        if len(selected)>=3:break
    paths=[cp,sp,pp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-joint-source-restoration-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=source['removed_uuids'],attempts=attempts,selected_source_proposals=selected,target_restorations_pending=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Joint source proposals',len(selected),flush=True)

if __name__=='__main__':run()
