"""Test dense serial escapes before choosing the MCU branch's layer crossing."""
import copy,json,time,math
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
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';sp=ROOT/'staging/digital-serial1-dense-source-escape-01/diagnosis.json'
    cap,source=[json.loads(p.read_text()) for p in (cp,sp)]
    for r in (cap,source):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in source['removed_uuids']]
    assert any(o['uuid']=='4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1' for o in work['objects'])
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    options=sorted(enumerate(source['domains']['serial source']['options']),key=lambda r:r[1]['cost'])
    choices=[];seen=set()
    for i,o in options:
        key=tuple(round(v*10) for v in o['point'])
        if key not in seen:choices.append((i,o));seen.add(key)
    ends=contacts(work,PERMIT,'U1001','36')|contacts(work,PERMIT,'J1003','3')
    trunk_ends=contacts(work,PERMIT,'U1001','36')
    serial_ends=contacts(work,SERIAL,'U3003','4')
    def crossings(s,n):
        return [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==n and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]+[(p,list(FACES)) for other,p in s.new_vias if other==n]
    attempts=[];selected=[];deadline=time.monotonic()+300
    for index,option in choices:
        if time.monotonic()>deadline:break
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        routes=[add(screen,SERIAL,option)]
        report=reachability(PlannedRegionScreen(screen,PERMIT),PERMIT,[('B.Cu',(41.5,16.9125))],sorted(ends),FACES,existing_crossings=crossings(screen,PERMIT))
        attempt=dict(serial_option_index=index,serial_via=option['point'],permit_region_report=report);attempts.append(attempt)
        print('Serial via',option['point'],'MCU full-component access',report['connected'],flush=True)
        if not report['connected']:continue
        for face,start,targets in [('B.Cu',(41.5,16.9125),ends),('In5.Cu',(45.,13.8),trunk_ends)]:
            result=route(screen,PERMIT,face,start,targets,min(deadline,time.monotonic()+35),existing_crossings=crossings(screen,PERMIT))
            if not result:break
            routes.append(add(screen,PERMIT,result))
        attempt['routes']=routes
        if len(routes)!=3:continue
        r=reachability(PlannedRegionScreen(screen,SERIAL),SERIAL,[('F.Cu',option['point'])],sorted(serial_ends),FACES,existing_crossings=crossings(screen,SERIAL))
        attempt['serial_region_after_mcu_restore']=r
        if r['connected']:
            selected.append(dict(serial_option_index=index,routes=routes));print('Source restoration retained serial access',flush=True)
            if len(selected)>=3:break
    paths=[cp,sp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-source-access-repair-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=source['removed_uuids'],serial_option_count=len(options),spatially_distinct_choices=len(choices),attempts=attempts,selected_source_proposals=selected,original_led37_via_retained=True,target_restorations_pending=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Source proposals:',len(selected),flush=True)

if __name__=='__main__':run()
