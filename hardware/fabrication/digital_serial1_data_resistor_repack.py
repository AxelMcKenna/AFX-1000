"""Test moving R3015 while preserving the screened serial/clock/LED48 routes."""
import copy,json,math,time
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_resistor_translation_screen import candidates
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-data-cutset-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(pcb.read_text())
    output_stub='6a538cec-4500-5fb6-a3db-da27fe13a423';removed=set(recipe['base_removed_uuids']+recipe['selected_extra_uuids']+[output_stub])
    work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    fixed=recipe['fixed_routes']+[recipe['serial_continuation']]
    def score(pose):
        pads={p['pin']:p for p in pose['pads']}
        return math.dist(pads['1']['position_mm'],[70.220423,19.747835])+.35*math.dist(pads['2']['position_mm'],[76.769724,21.])
    poses,counts,base=candidates(work,board,'R3015',fixed,[67+i*.25 for i in range(45)],[15+i*.25 for i in range(49)],score)
    print('R3015 placement screen',counts,'legal poses',len(poses),flush=True)
    ends={ '/LED/DATA_5V_SRC':contacts(base,'/LED/DATA_5V_SRC','U3005','21'),'/LED/DATA_5V':contacts(base,'/LED/DATA_5V','U3001','4') }
    attempts=[];selected=None;deadline=time.monotonic()+240
    for pose in poses[:36]:
        if time.monotonic()>deadline:break
        placed=copy.deepcopy(base);placed['objects']+=pose['pads'];screen=CloseMarginViaScreen(placed,signal_layers=FACES)
        for r in fixed:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        attempt=dict(position_mm=pose['position_mm'],repairs=[]);attempts.append(attempt);routes=[]
        for pad in sorted(pose['pads'],key=lambda p:p['pin']):
            net=pad['net'];start=pad['position_mm']
            direct=[p for f,end in sorted(ends[net],key=lambda row:math.dist(start,row[1]))[:64] if f=='B.Cu' for p in surface.candidate_paths(start,end) if screen.legal(net,'B.Cu',p)]
            crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in placed['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
            result=dict(runs=[('B.Cu',min(direct,key=lambda p:LineString(p).length))],vias=[]) if direct else route(screen,net,'B.Cu',start,ends[net],min(deadline,time.monotonic()+25),existing_crossings=crossings)
            entry=dict(net=net,found=bool(result));attempt['repairs'].append(entry)
            if result:
                added=add(screen,net,result);routes.append(added);entry.update(planar_length_mm=added['planar_length_mm'],new_vias=len(added['new_vias_mm']))
            print(pose['position_mm'],entry,flush=True)
            if not result:break
        attempt['routes']=routes
        if len(routes)==2:selected=dict(pose=pose,routes=routes);break
    paths=[cp,rp,pcb,Path(__file__),ROOT/'digital_resistor_translation_screen.py']+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_core_layout.py','digital_continuous_net_route_v2.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]+[ROOT.parent/'electronics/output_stage/check_placement.py']
    out=ROOT/'staging/digital-serial1-data-resistor-repack-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),placement_counts=counts,legal_poses=poses,attempts=attempts,placement_and_routes=selected,other_restorations_pending=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Complete R3015 reconnection:',bool(selected),flush=True)
if __name__=='__main__':run()
