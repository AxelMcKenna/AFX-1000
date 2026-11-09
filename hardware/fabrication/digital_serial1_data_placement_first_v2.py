"""Move and reconnect R3015 before reserving adjacent receiving-end escapes."""
import copy,json,math,time
from pathlib import Path
from shapely.geometry import LineString,Point
from hardware.electronics.common.sexpr import read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_resistor_native_pose_screen_v2 import candidates
from hardware.fabrication.digital_joint_escape_packing import pack
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_region_point_access import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-serial1-source-preparation-inputs-31-02/capture.json';rp=ROOT/'staging/digital-serial1-data-cutset-01/diagnosis.json';tp=ROOT/'staging/digital-serial1-resistor-templates-01/templates.json';ep=ROOT/'staging/digital-serial1-four-target-escape-01/diagnosis.json'
    cap,recipe,native,escapes=[json.loads(p.read_text()) for p in (cp,rp,tp,ep)]
    for r in (cap,recipe,native,escapes):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(pcb.read_text())
    removed=set(recipe['base_removed_uuids']+recipe['selected_extra_uuids'])
    removed.remove('4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1');removed.add('6a538cec-4500-5fb6-a3db-da27fe13a423')
    removed &= {o['uuid'] for o in cap['objects']}
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    templates=[]
    for t in native['templates']:
        if t['ref']!='R3015':continue
        assert sha(tp.parent/t['file'])==t['sha256'];t=copy.deepcopy(t);t['footprint']=read_sexpr((tp.parent/t['file']).read_text());templates.append(t)
    poses,counts,base=candidates(work,board,'R3015',[],[69+i*.25 for i in range(37)],[12+i*.25 for i in range(69)],lambda p:math.dist(p['position_mm'],[75,21]),templates)
    print('Placement before escape reservation',counts,flush=True)
    ends={'/LED/DATA_5V_SRC':contacts(base,'/LED/DATA_5V_SRC','U3005','21'),'/LED/DATA_5V':contacts(base,'/LED/DATA_5V','U3001','4')}
    def crossings(s,n):
        return [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in base['objects'] if o['net']==n and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]+[(p,list(FACES)) for other,p in s.new_vias if other==n]
    access=[];eligible=set(range(len(poses)));screen=CloseMarginViaScreen(base,signal_layers=FACES)
    for net in ends:
        probes=[('B.Cu',next(p for p in pose['pads'] if p['net']==net)['position_mm']) for pose in poses]
        report=reachability(PlannedRegionScreen(screen,net),net,sorted(ends[net]),sorted(ends[net]),FACES,existing_crossings=crossings(screen,net),probes=probes)
        indices={i for i,p in enumerate(report['probe_results']) if p['connected_to_sources']};eligible &= indices
        access.append(dict(net=net,pose_indices=sorted(indices),region_report=report));print(net,'accessible poses',len(indices),flush=True)
    attempts=[];selected=None;deadline=time.monotonic()+360
    for index in sorted(eligible)[:32]:
        if time.monotonic()>deadline:break
        pose=poses[index]
        if pose['position_mm']==[75.,21.] and pose['angle']==0:continue
        placed=copy.deepcopy(base);placed['objects']+=pose['pads'];screen=CloseMarginViaScreen(placed,signal_layers=FACES)
        attempt=dict(pose_index=index,position_mm=pose['position_mm'],angle=pose['angle'],repairs=[]);attempts.append(attempt);routes=[]
        for pad in sorted(pose['pads'],key=lambda p:p['pin']):
            net=pad['net'];start=pad['position_mm']
            direct=[p for f,end in sorted(ends[net],key=lambda row:math.dist(start,row[1]))[:64] if f=='B.Cu' for p in surface.candidate_paths(start,end) if screen.legal(net,'B.Cu',p)]
            result=dict(runs=[('B.Cu',min(direct,key=lambda p:LineString(p).length))],vias=[]) if direct else route(screen,net,'B.Cu',start,ends[net],min(deadline,time.monotonic()+25),existing_crossings=crossings(screen,net))
            attempt['repairs'].append(dict(net=net,found=bool(result)))
            if not result:break
            routes.append(add(screen,net,result))
        attempt['routes']=routes
        print('Pose',index,pose['position_mm'],pose['angle'],'DATA terminals routed',len(routes),flush=True)
        if len(routes)!=2:continue
        domains={}
        for name in ('serial target','clock','led48'):
            d=copy.deepcopy(escapes['domains'][name]);obstacles=screen.obstacles(d['net'])
            d['options']=[o for o in d['options'] if all(screen.via_outline.covers(Point(p)) and not obstacles.intersects(Point(p)) for p in o['vias']) and all(screen.legal(d['net'],f,p) for f,p in o['runs'])]
            domains[name]=d
        packing=pack(domains,limit=8);attempt['remaining_escape_counts']={n:len(d['options']) for n,d in domains.items()};attempt['packing']=packing
        print('Receiving-end packs after DATA placement',len(packing['choices']),flush=True)
        if packing['choices']:
            for choice in packing['choices']:
                replay=CloseMarginViaScreen(placed,signal_layers=FACES)
                for r in routes:add(replay,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
                for name,j in zip(packing['names'],choice['indices']):add(replay,domains[name]['net'],domains[name]['options'][j])
            selected=dict(pose=pose,routes=routes,domains=domains,packing=packing);break
    paths=[cp,rp,tp,ep,pcb,Path(__file__)]+[tp.parent/t['file'] for t in templates]+[ROOT/n for n in ('audit_candidate.py','digital_resistor_native_pose_screen_v2.py','digital_core_layout.py','digital_joint_escape_packing.py','digital_serial1_joint_escape_survey.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_region_point_access.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/output_stage/check_placement.py']
    out=ROOT/'staging/digital-serial1-data-placement-first-02';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),placement_counts=counts,legal_poses=poses,access_reports=access,eligible_pose_indices=sorted(eligible),attempts=attempts,placement_and_local_escapes=selected,global_restorations_pending=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('DATA placement and local receiving escapes found:',bool(selected),flush=True)

if __name__=='__main__':run()
