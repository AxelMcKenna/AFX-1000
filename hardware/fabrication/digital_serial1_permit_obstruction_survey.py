"""Locate the remaining MCU_PERMIT restoration obstruction after serial fanout."""
import copy,json
from pathlib import Path
from shapely.geometry import box
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,PERMIT
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';sp=ROOT/'staging/digital-serial1-joint-escape-survey-01/diagnosis.json'
    cap,source=[json.loads(p.read_text()) for p in (cp,sp)]
    for r in (cap,source):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    base=set(source['removed_uuids']);region=box(38,13,47,21);candidates={};protected={'AGND','5V_DIG','V3V3_IO',SERIAL,PERMIT}
    for o in cap['objects']:
        if o['uuid'] in base or o['kind'] not in ('PCB_TRACK','PCB_VIA') or o['net'] in protected:continue
        if any(surface.shape(ps).intersects(region) for ps in o['layers'].values()):candidates.setdefault(o['net'],[]).append(o['uuid'])
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    pack=source['packs'][0];choice=pack['screen_replayed_choices'][0];results=[]
    for net,ids in [(None,[]),*sorted(candidates.items())]:
        work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in base.union(ids)]
        screen=CloseMarginViaScreen(work,signal_layers=FACES);via=None
        for name,index in zip(pack['names'],choice['indices']):
            domain=source['domains'][name];option=domain['options'][index];add(screen,domain['net'],option)
            if domain['net']==PERMIT:via=option['point']
        crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==PERMIT and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
        crossings.append((via,list(FACES)))
        r=reachability(PlannedRegionScreen(screen,PERMIT),PERMIT,[('B.Cu',via)],[('In5.Cu',(45.,13.8)),('In5.Cu',(38.3,19.7))],FACES,existing_crossings=crossings)
        results.append(dict(extra_omitted_net=net,extra_omitted_uuids=ids,region_report=r))
        print(net,'omitted',len(ids),'permit potential access',r['connected'],flush=True)
    paths=[cp,sp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-permit-obstruction-survey-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},base_removed_uuids=sorted(base),source_pack=choice,search_box_mm=list(region.bounds),results=results,diagnostic_only=True,restoration_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':run()
