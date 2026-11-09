"""Route DATA before global SERIAL_1, trying alternative local layer escapes."""
import copy,json,math,time
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-data-cutset-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    removed=set(recipe['base_removed_uuids']+recipe['selected_extra_uuids']);work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    fixed=recipe['fixed_routes'];net='/LED/DATA_5V_SRC';start=[74.175,21.]
    ends=contacts(work,net,'U3005','21')
    def prepared():
        s=CloseMarginViaScreen(work,signal_layers=FACES)
        for r in fixed:add(s,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        return s
    def crossings(s,n):
        return [(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==n and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]+[(p,list(FACES)) for other,p in s.new_vias if other==n]
    screen=prepared();options=[]
    for x in range(61):
        for y in range(61):
            point=[72+x*.1,18+y*.1]
            if not screen.via_legal(net,point):continue
            paths=[p for p in surface.candidate_paths(start,point) if screen.legal(net,'B.Cu',p)]
            if paths:
                path=min(paths,key=lambda p:LineString(p).length)
                options.append(dict(point_mm=point,path=path,length_mm=LineString(path).length))
    options.sort(key=lambda r:r['length_mm'])
    # Spread the bounded attempts spatially instead of keeping only adjacent points.
    choices=[];seen=set()
    for o in options:
        key=tuple(round(v*2) for v in o['point_mm'])
        if key not in seen:choices.append(o);seen.add(key)
        if len(choices)>=20:break
    print('DATA escape options',len(options),'spatial samples',len(choices),flush=True)
    attempts=[];selected=None;deadline=time.monotonic()+240
    trials=[None]+[(o,face) for o in choices for face in ('In3.Cu','In5.Cu','F.Cu')]
    for trial in trials:
        if time.monotonic()>deadline:break
        s=prepared();routes=[];face='B.Cu';point=start
        if trial is not None:
            option,face=trial;point=option['point_mm']
            routes.append(add(s,net,dict(runs=[('B.Cu',option['path'])],vias=[point])))
        result=route(s,net,face,point,ends,min(deadline,time.monotonic()+20),existing_crossings=crossings(s,net))
        attempt=dict(escape=trial,data_route_found=bool(result));attempts.append(attempt)
        if result:
            routes.append(add(s,net,result))
            serial_start=fixed[0]['new_vias_mm'][0];serial_end=fixed[2]['new_vias_mm'][0]
            report=reachability(PlannedRegionScreen(s,SERIAL),SERIAL,[('In3.Cu',serial_start)],[(f,serial_end) for f in FACES],FACES,existing_crossings=crossings(s,SERIAL))
            attempt.update(data_routes=routes,serial_access_report=report)
            if report['connected']:
                serial=route(s,SERIAL,'In3.Cu',serial_start,{(f,tuple(serial_end)) for f in FACES},min(deadline,time.monotonic()+40),existing_crossings=crossings(s,SERIAL))
                if serial:
                    selected=dict(data_routes=routes,serial_route=add(s,SERIAL,serial));break
        print('trial',len(attempts),'DATA',bool(result),'SERIAL region',attempt.get('serial_access_report',{}).get('connected'),flush=True)
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-data-first-repair-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),fixed_routes=fixed,escape_options=options,attempts=attempts,selected=selected,remaining_restorations_pending=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('DATA and SERIAL jointly restored:',bool(selected),flush=True)

if __name__=='__main__':run()
