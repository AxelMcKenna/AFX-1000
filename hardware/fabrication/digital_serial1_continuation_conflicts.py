"""Find remaining obstructions with complete successful continuations reserved.

Test SERIAL_1 after CLOCK/LED48, and LED48 after CLOCK/SERIAL_1. Copper omissions
remain diagnostic and never replace the verified native checkpoint.
"""
import copy,json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL,LED
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-packed-repair-06/diagnosis.json';op=ROOT/'staging/digital-serial1-target-obstruction-survey-01/diagnosis.json'
    cap,recipe,omissions=[json.loads(p.read_text()) for p in (cp,rp,op)]
    for r in (cap,recipe,omissions):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    base=set(recipe['removed_uuids']);surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    results=[]
    for mode,index,net in [('serial after restored led48',0,SERIAL),('led48 after serial',1,LED)]:
        attempt=recipe['attempts'][index]
        assert not attempt['repairs'][-1]['found'] and all(r['found'] for r in attempt['repairs'][:-1])
        assert attempt['repairs'][-1]['task']==('serial' if net==SERIAL else 'led48')
        for omission in omissions['results']:
            other=omission['extra_omitted_net']
            if other==net:continue
            ids=set(omission['extra_omitted_uuids'])-base
            work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in base|ids]
            screen=CloseMarginViaScreen(work,signal_layers=FACES)
            for r in attempt['routes']:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
            local=[r for r in attempt['routes'][:5] if r['net']==net]
            via=local[0]['new_vias_mm'][0]
            ends={(f,tuple(local[1]['new_vias_mm'][0])) for f in FACES} if net==SERIAL else contacts(work,LED,'J3005','1')
            crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
            crossings += [(p,list(FACES)) for n,p in screen.new_vias if n==net]
            r=reachability(PlannedRegionScreen(screen,net),net,[('F.Cu',via)],sorted(ends),FACES,existing_crossings=crossings)
            results.append(dict(mode=mode,attempt_index=index,net=net,extra_omitted_net=other,extra_omitted_uuids=sorted(ids),region_report=r))
            print(mode,other,len(ids),'potential access',r['connected'],flush=True)
    paths=[cp,rp,op,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-continuation-conflicts-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},base_removed_uuids=sorted(base),results=results,successful_continuations_replayed=True,diagnostic_only=True,restoration_not_proven=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':run()
