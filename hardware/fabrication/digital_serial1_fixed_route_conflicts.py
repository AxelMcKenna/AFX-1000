"""Check whole retained source components before declaring a restoration blocked."""
import copy,json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
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
    removed=set(recipe['base_removed_uuids']+recipe['selected_extra_uuids']);work=copy.deepcopy(cap);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    fixed=recipe['fixed_routes']+[recipe['serial_continuation']]
    cases=[('all reserved routes',fixed),('before global SERIAL_1',fixed[:-1])]
    cases += [('without '+net,[r for r in fixed if r['net']!=net]) for net in sorted({r['net'] for r in fixed})]
    results=[]
    for case,routes in cases:
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        for r in routes:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        for net,sref,spin,tref,tpin in [('/LED/DATA_5V_SRC','R3015','1','U3005','21'),('/LED/LED_37','U3002','18','J3002','23')]:
            starts=contacts(work,net,sref,spin);ends=contacts(work,net,tref,tpin)
            crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
            crossings += [(p,list(FACES)) for n,p in screen.new_vias if n==net]
            r=reachability(PlannedRegionScreen(screen,net),net,sorted(starts),sorted(ends),FACES,existing_crossings=crossings)
            results.append(dict(case=case,net=net,source_contacts=sorted(starts),target_contacts=sorted(ends),region_report=r))
            print(case,net,'full source component access',r['connected'],flush=True)
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_region_reachability.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-fixed-route-conflicts-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},removed_uuids=sorted(removed),results=results,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':run()
