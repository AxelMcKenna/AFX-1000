"""Greedily minimize a bounded local copper omission that opens SERIAL_1.

This is inclusion-minimal in the tested net groups, not a minimum-cost proof.
No geometry or board change is adopted from this diagnostic.
"""
import copy
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-target-obstruction-survey-01/diagnosis.json'
    cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
    for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    base=set(recipe['base_removed_uuids']);candidates={r['extra_omitted_net']:r['extra_omitted_uuids'] for r in recipe['results'] if r['extra_omitted_net']}
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    trials=[]
    def check(names):
        removed=base.union(*(candidates[n] for n in names));work=copy.deepcopy(cap)
        work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        r=reachability(screen,SERIAL,[('F.Cu',(75.25,20.075))],[('F.Cu',(42.75,14.075))],FACES)
        trials.append(dict(extra_nets=sorted(names),extra_omitted_uuids=sorted(removed-base),region_report=r))
        print('Extra nets',len(names),'objects',len(removed-base),'connected',r['connected'],flush=True)
        return r['connected']
    selected=set(candidates);possible=check(selected)
    if possible:
        # Prefer restoring large or recently qualified branches first.
        for name in sorted(candidates,key=lambda n:(-len(candidates[n]),n)):
            if check(selected-{name}):selected.remove(name)
    paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-target-cutset-01';out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},base_removed_uuids=sorted(base),trials=trials,potential_access=possible,selected_extra_nets=sorted(selected) if possible else None,selected_extra_uuids=sorted({u for n in selected for u in candidates[n]}) if possible else None,inclusion_minimal_within_tested_groups=possible,restoration_not_proven=True,candidate_emitted=False,fabrication_released=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Final extra nets:',report['selected_extra_nets'],flush=True)
if __name__=='__main__':run()
