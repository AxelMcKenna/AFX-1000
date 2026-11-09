"""Test narrowly declared neighbouring LED escapes as LED70 restoration tasks."""
import copy
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_region_reachability import reachability
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

LED69={'0bdc553e-b3ea-53f3-94e9-5a7cfe0314e0','70463f9f-2b96-588a-8c74-70a392b5a12a','edeaaa57-ba45-5003-b595-44b8f092c3b7','a3dd07a2-f8d6-5dfb-94f9-13e440075222'}
LED71={'06f9e3d2-5a93-5ea4-a3ad-d7cbbd854198','08f0d821-8ae1-51ce-a3f5-5b9444db7436','77253491-b9d5-507c-bff8-887662e37a28','0f0065f8-ec18-5151-94f8-4d916b952751'}


def run():
    cp=ROOT/'staging/digital-costed-shortening-inputs-30/capture.json'
    cap=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
    objects={o['uuid']:o for o in cap['objects']}
    assert all(objects[u]['net']=='/LED/LED_69' for u in LED69)
    assert all(objects[u]['net']=='/LED/LED_71' for u in LED71)
    terminals=[next(o for o in cap['objects'] if o.get('ref')==ref and o.get('pin')==pin) for ref,pin in [('U3003','27'),('J3004','2')]]
    net='/LED/LED_70'
    assert all(o['net']==net for o in terminals)
    starts=[(f,terminals[0]['position_mm']) for f in FACES if terminals[0]['layers'].get(f)]
    ends=[(f,terminals[1]['position_mm']) for f in FACES if terminals[1]['layers'].get(f)]
    surface.WIDTH=layers.WIDTH=.2
    surface.MARGIN=.001
    surface.SIGNAL_LAYERS=FACES
    cases=[('LED71 inner leg',{'06f9e3d2-5a93-5ea4-a3ad-d7cbbd854198'}),
           ('LED69 inner leg',{'0bdc553e-b3ea-53f3-94e9-5a7cfe0314e0'}),
           ('both inner legs',{'06f9e3d2-5a93-5ea4-a3ad-d7cbbd854198','0bdc553e-b3ea-53f3-94e9-5a7cfe0314e0'}),
           ('LED71 source cell',LED71),('LED69 source cell',LED69),('both source cells',LED69|LED71)]
    results=[]
    for name,removed in cases:
        work=copy.deepcopy(cap)
        work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        r=reachability(screen,net,starts,ends,FACES)
        r.update(case=name,removed_uuids=sorted(removed))
        results.append(r)
        print(name,'LED70 potential access',r['connected'],'transitions',len(r['component_witness']),flush=True)
    paths=[cp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-led70-corridor-probe-01'
    out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},net=net,starts=starts,ends=ends,results=results,
        removals_are_diagnostic_only=True,all_displaced_nets_must_be_restored=True,candidate_emitted=False,native_rules_relaxed=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':
    run()
