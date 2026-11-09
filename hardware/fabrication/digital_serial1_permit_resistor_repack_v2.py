"""Move the MCU pull-down to retain LED37's original via while opening SERIAL_1."""
import copy,itertools,json,math,time
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_resistor_native_pose_screen import candidates
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_region_point_access import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-data-cutset-01/diagnosis.json';tp=ROOT/'staging/digital-serial1-resistor-templates-01/templates.json'
    cap,recipe,native=[json.loads(p.read_text()) for p in (cp,rp,tp)]
    for r in (cap,recipe,native):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(pcb.read_text())
    led_via='4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1';ground_stub='f8c2863b-957e-5044-9e8a-19dbed83a0d6'
    removed=set(recipe['base_removed_uuids']+recipe['selected_extra_uuids']);removed.remove(led_via);removed.add(ground_stub)
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    fixed=[r for r in recipe['fixed_routes']+[recipe['serial_continuation']] if r['net']!=PERMIT]
    no_resistor=copy.deepcopy(work);no_resistor['objects']=[o for o in work['objects'] if o.get('ref')!='R1003']
    check=CloseMarginViaScreen(no_resistor,signal_layers=FACES)
    for r in fixed:add(check,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    trunk_ends=contacts(no_resistor,PERMIT,'U1001','36')
    crossing=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in no_resistor['objects'] if o['net']==PERMIT and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
    trunk=route(check,PERMIT,'In5.Cu',(45.,13.8),trunk_ends,time.monotonic()+40,existing_crossings=crossing)
    assert trunk,'Retained MCU trunk requires further repair before moving its pull-down'
    fixed.append(add(check,PERMIT,trunk));print('MCU trunk restored with original LED37 via retained',fixed[-1]['planar_length_mm'],flush=True)
    templates=[]
    for t in native['templates']:
        if t['ref']!='R1003':continue
        assert sha(tp.parent/t['file'])==t['sha256'];t=copy.deepcopy(t);t['footprint']=read_sexpr((tp.parent/t['file']).read_text());templates.append(t)
    source_ends=contacts(no_resistor,PERMIT,'J1003','3')|trunk_ends
    for face,path in fixed[-1]['runs']:
        for a,b in zip(path,path[1:]):
            count=max(1,math.ceil(math.dist(a,b)/.2));source_ends.update((face,tuple(x+(y-x)*i/count for x,y in zip(a,b))) for i in range(count+1))
    source_ends.update((f,tuple(p)) for p in fixed[-1]['new_vias_mm'] for f in FACES)
    def score(pose):
        p=next(p for p in pose['pads'] if p['net']==PERMIT)['position_mm']
        return min(math.dist(p,q) for f,q in source_ends)
    previous=ROOT/'staging/digital-serial1-permit-resistor-repack-01/diagnosis.json'
    saved=json.loads(previous.read_text());assert all(sha(Path(p))==h for p,h in saved['source_sha256'].items())
    assert saved['removed_uuids']==sorted(removed) and saved['fixed_routes']==json.loads(json.dumps(fixed))
    poses,counts,base=saved['legal_poses'],saved['placement_counts'],no_resistor
    print('R1003 placement screen',counts,'legal poses',len(poses),flush=True)
    ground_ends={(f,tuple(p)) for o in base['objects'] if o['net']=='AGND' for f in ['B.Cu'] if o['layers'].get(f) for p in [o['position_mm']]+([o['end_mm']] if o['kind']=='PCB_TRACK' else [])}
    probes=[('B.Cu',next(p for p in pose['pads'] if p['net']==PERMIT)['position_mm']) for pose in poses]
    access=reachability(PlannedRegionScreen(check,PERMIT),PERMIT,sorted(source_ends),sorted(source_ends),FACES,existing_crossings=crossing+[(p,list(FACES)) for n,p in check.new_vias if n==PERMIT],probes=probes)
    eligible=[i for i,p in enumerate(access['probe_results']) if p['connected_to_sources']]
    print('MCU-connected placement regions:',len(eligible),'of',len(poses),flush=True)
    attempts=[];selected=None;deadline=time.monotonic()+300
    for pose in [poses[i] for i in eligible][:64]:
        if time.monotonic()>deadline:break
        placed=copy.deepcopy(base);placed['objects']+=pose['pads'];screen=CloseMarginViaScreen(placed,signal_layers=FACES)
        for r in fixed:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        attempt=dict(position_mm=pose['position_mm'],angle=pose['angle'],repairs=[]);attempts.append(attempt);routes=[]
        for net in [PERMIT,'AGND']:
            pad=next(p for p in pose['pads'] if p['net']==net);start=pad['position_mm'];ends=source_ends if net==PERMIT else ground_ends
            direct=[p for f,end in sorted(ends,key=lambda row:math.dist(start,row[1]))[:64] if f=='B.Cu' and (net!= 'AGND' or math.dist(start,end)<=5.) for p in surface.candidate_paths(start,end) if screen.legal(net,'B.Cu',p)]
            result=dict(runs=[('B.Cu',min(direct,key=lambda p:LineString(p).length))],vias=[]) if direct else None
            if result is None and net==PERMIT:
                crossings=crossing+[(p,list(FACES)) for n,p in screen.new_vias if n==net]
                result=route(screen,net,'B.Cu',start,ends,min(deadline,time.monotonic()+25),existing_crossings=crossings)
            if result is None and net=='AGND':
                for radius in (1.1,1.3,1.5):
                    for angle in range(0,360,15):
                        p=[start[0]+radius*math.cos(math.radians(angle)),start[1]+radius*math.sin(math.radians(angle))]
                        if screen.via_legal(net,p) and screen.legal(net,'B.Cu',[start,p]):result=dict(runs=[('B.Cu',[start,p])],vias=[p]);break
                    if result:break
            entry=dict(net=net,found=bool(result));attempt['repairs'].append(entry)
            if result:
                added=add(screen,net,result);routes.append(added);entry.update(planar_length_mm=added['planar_length_mm'],new_vias=len(added['new_vias_mm']))
            print(pose['position_mm'],pose['angle'],entry,flush=True)
            if not result:break
        attempt['routes']=routes
        if len(routes)==2:selected=dict(pose=pose,routes=routes);break
    paths=[cp,rp,tp,pcb,previous,Path(__file__),ROOT/'digital_resistor_native_pose_screen.py']+[tp.parent/t['file'] for t in templates]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_core_layout.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_region_point_access.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/output_stage/check_placement.py']
    out=ROOT/'staging/digital-serial1-permit-resistor-repack-02';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),retained_original_led37_via=led_via,fixed_routes=fixed,placement_counts=counts,legal_poses=poses,access_report=access,eligible_pose_indices=eligible,attempts=attempts,placement_and_routes=selected,other_restorations_pending=True,ground_plane_connection_requires_native_refill=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Complete R1003 reconnection:',bool(selected),flush=True)
if __name__=='__main__':run()
