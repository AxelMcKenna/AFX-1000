"""Minimize DATA_5V_SRC rework with all proven local/global restorations fixed."""
import copy,json,time
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_continuous_net_route_v2 import route
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-packed-repair-06/diagnosis.json';op=ROOT/'staging/digital-serial1-target-obstruction-survey-01/diagnosis.json'
    cap,recipe,omissions=[json.loads(p.read_text()) for p in (cp,rp,op)]
    for r in (cap,recipe,omissions):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    base=set(recipe['removed_uuids']);surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    attempt=recipe['attempts'][0];assert attempt['repairs'][-1]['task']=='serial' and not attempt['repairs'][-1]['found']
    assert all(r['found'] for r in attempt['repairs'][:-1]);local=[r for r in attempt['routes'][:5] if r['net']==SERIAL]
    start=local[0]['new_vias_mm'][0];ends={(f,tuple(local[1]['new_vias_mm'][0])) for f in FACES}
    selected=set(next(r for r in omissions['results'] if r['extra_omitted_net']=='/LED/DATA_5V_SRC')['extra_omitted_uuids'])-base
    results=[]
    def screen_for(ids):
        work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in base|ids]
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        for r in attempt['routes']:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        return work,screen
    def check(ids):
        work,screen=screen_for(ids);crossings=[(p,list(FACES)) for n,p in screen.new_vias if n==SERIAL]
        r=reachability(PlannedRegionScreen(screen,SERIAL),SERIAL,[('F.Cu',start)],sorted(ends),FACES,existing_crossings=crossings)
        results.append(dict(extra_omitted_uuids=sorted(ids),region_report=r));print('Omitted DATA copper',len(ids),'serial access',r['connected'],flush=True)
        return r['connected']
    assert check(selected)
    for uid in sorted(selected):
        if check(selected-{uid}):selected.remove(uid)
    work,screen=screen_for(selected);crossings=[(p,list(FACES)) for n,p in screen.new_vias if n==SERIAL]
    proposed=route(screen,SERIAL,'F.Cu',start,ends,time.monotonic()+80,existing_crossings=crossings)
    checked=add(screen,SERIAL,proposed) if proposed else None
    paths=[cp,rp,op,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_continuous_net_route_v2.py','digital_polygon_path.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-data-cutset-01';out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},base_removed_uuids=sorted(base),selected_extra_uuids=sorted(selected),results=results,inclusion_minimal_within_tested_objects=True,fixed_routes=attempt['routes'],serial_continuation=checked,restoration_not_proven=True,candidate_emitted=False,fabrication_released=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Selected extra objects',len(selected),'serial continuation',bool(checked),'length',checked['planar_length_mm'] if checked else None,flush=True)
if __name__=='__main__':run()
