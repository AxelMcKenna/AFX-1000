"""Complete SERIAL_1 and four restored nets from mutually screened local escapes."""
import copy,itertools,json,time,math
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_latch_supply_repack import source_component
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,PERMIT,CLOCK,LED
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def contacts(cap,net,ref,pin):
    result=set()
    for obj in source_component(cap,net,ref,pin):
        points=[obj['position_mm']]
        if obj['kind']=='PCB_TRACK':
            a,b=obj['position_mm'],obj['end_mm'];count=max(1,math.ceil(math.dist(a,b)/.2))
            points += [tuple(round(x+(y-x)*i/count,6) for x,y in zip(a,b)) for i in range(1,count+1)]
        result.update((f,tuple(p)) for p in points for f in FACES if obj['layers'].get(f))
    return result

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';sp=ROOT/'staging/digital-serial1-joint-escape-survey-01/diagnosis.json';tp=ROOT/'staging/digital-serial1-dense-escape-survey-01/diagnosis.json'
    dp=ROOT/'staging/digital-serial1-permit-obstruction-survey-01/diagnosis.json'
    lp=ROOT/'staging/digital-serial1-led48-single-obstruction-01/diagnosis.json'
    cap,source,target,diagnosis,led_diagnosis=[json.loads(p.read_text()) for p in (cp,sp,tp,dp,lp)]
    for r in (cap,source,target,diagnosis,led_diagnosis):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    assert source['removed_uuids']==target['removed_uuids']
    extra=next(r for r in diagnosis['results'] if r['extra_omitted_net']=='/LED/LED_37')
    assert extra['region_report']['connected'] and extra['extra_omitted_uuids']==['4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1']
    led_extra=next(r for r in led_diagnosis['results'] if r['region_report']['connected'])
    assert led_extra['extra_omitted_net']=='/LED/LED_50' and led_extra['extra_omitted_uuids']==['f1ea2e26-acf3-46e4-a518-bdb380e99c7e']
    removed=source['removed_uuids']+extra['extra_omitted_uuids']+led_extra['extra_omitted_uuids']
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    sources=source['packs'][0];attempts=[];selected=None;deadline=time.monotonic()+420
    destinations={
        'permit branch':contacts(work,PERMIT,'J1003','3')|contacts(work,PERMIT,'U1001','36'),
        'permit trunk':contacts(work,PERMIT,'U1001','36'),
        'led48':contacts(work,LED,'J3005','1'),
        'led37':contacts(work,'/LED/LED_37','J3002','23'),
        'led50':contacts(work,'/LED/LED_50','J3005','3'),
        'clock':contacts(work,CLOCK,'R3016','2'),
        'control30':contacts(work,'/CONTROLS/CONTROL_30','U2003','3'),
    }
    combinations=sorted(itertools.product(enumerate(sources['screen_replayed_choices']),enumerate(target['screen_replayed_choices'])),key=lambda row:row[0][1]['cost']+row[1][1]['cost'])
    for (si,sc),(ti,tc) in combinations:
        for order in [(1,3,2,0,4,6,7,5),(1,3,0,2,4,6,7,5),(1,0,3,2,4,6,7,5),(1,2,0,3,4,6,7,5)]:
            if time.monotonic()>=deadline:break
            screen=CloseMarginViaScreen(work,signal_layers=FACES);routes=[];via={}
            for names,domains,choice in [(sources['names'],source['domains'],sc),(target['names'],target['domains'],tc)]:
                for name,index in zip(names,choice['indices']):
                    option=domains[name]['options'][index];routes.append(add(screen,domains[name]['net'],option));via[name]=option['point']
            tasks=[
                ('serial',SERIAL,'F.Cu',via['serial source'],{(f,tuple(via['serial target'])) for f in FACES}),
                ('permit branch',PERMIT,'B.Cu',via['permit'],{('In5.Cu',(45.,13.8)),('In5.Cu',(38.3,19.7))}),
                ('led48',LED,'F.Cu',via['led48'],{('In3.Cu',(73.3976,17.2734))}),
                ('clock',CLOCK,'F.Cu',via['clock'],{('B.Cu',(71.6,19.8))}),
                ('permit trunk',PERMIT,'In5.Cu',(45.,13.8),{('In5.Cu',(38.3,19.7))}),
                ('control30','/CONTROLS/CONTROL_30','F.Cu',(81.9,11.1),{('F.Cu',(82.,14.6))}),
                ('led37','/LED/LED_37','F.Cu',(44.,21.225),{('In3.Cu',(44.,21.225))}),
                ('led50','/LED/LED_50','In3.Cu',(73.5,21.598),{('In3.Cu',(77.3771,17.7209))}),
            ]
            attempt=dict(source_pack=si,target_pack=ti,order=[tasks[i][0] for i in order],repairs=[]);attempts.append(attempt)
            for i in order:
                name,net,face,start,ends=tasks[i]
                ends=destinations.get(name,ends)
                crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
                crossings += [(p,list(FACES)) for n,p in screen.new_vias if n==net]
                result=route(screen,net,face,start,ends,min(deadline,time.monotonic()+40),existing_crossings=crossings)
                entry=dict(task=name,found=bool(result));attempt['repairs'].append(entry)
                if result:
                    added=add(screen,net,result);routes.append(added);entry.update(planar_length_mm=added['planar_length_mm'],new_vias=len(added['new_vias_mm']))
                print(si,ti,entry,flush=True)
                if not result:break
            attempt['routes']=routes
            if len(attempt['repairs'])==8 and all(r['found'] for r in attempt['repairs']):selected=routes;break
        if selected or time.monotonic()>=deadline:break
    paths=[cp,sp,tp,dp,lp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_latch_supply_repack.py','digital_serial1_joint_repair.py','digital_continuous_net_route_v2.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_planned_region_screen.py','digital_region_reachability.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-packed-repair-06';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=removed,attempts=attempts,complete_route_proposal=selected,target_contacts={n:sorted(v) for n,v in destinations.items()},target_contacts_from_retained_copper_components=True,native_checks_pending=bool(selected),candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Complete packed proposal:',bool(selected),'attempts',len(attempts),flush=True)
if __name__=='__main__':run()
