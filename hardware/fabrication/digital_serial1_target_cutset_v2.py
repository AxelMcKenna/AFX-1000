"""Reduce the wider SERIAL_1 blockage while retaining named supply/ground copper."""
import copy,itertools,json,time
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES,SERIAL
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';rp=ROOT/'staging/digital-serial1-obstruction-extent-01/diagnosis.json';bp=ROOT/'staging/digital-serial1-joint-repair-01/diagnosis.json'
    cap,recipe,base_recipe=[json.loads(p.read_text()) for p in (cp,rp,bp)]
    for r in (cap,recipe,base_recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    base=set(base_recipe['removed_uuids']);objects={o['uuid']:o for o in cap['objects']}
    region=recipe['results'][1];assert region['bounds_mm']==[65,10,83,29] and region['region_report']['connected']
    protected={'AGND','5V_DIG','3V3_DIG','V3V3_IO'}
    candidates={}
    for uid in set(region['removed_uuids'])-base:
        o=objects[uid]
        if o['net'] not in protected:candidates.setdefault(o['net'],[]).append(uid)
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    trials=[];cache={};deadline=time.monotonic()+540
    def check(ids):
        key=tuple(sorted(ids))
        if key in cache:return cache[key]
        work=copy.deepcopy(cap);removed=base.union(ids);work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed]
        screen=CloseMarginViaScreen(work,signal_layers=FACES)
        r=reachability(screen,SERIAL,[('F.Cu',(75.25,20.075))],[('F.Cu',(42.75,14.075))],FACES)
        trials.append(dict(extra_nets=sorted({objects[u]['net'] for u in ids}),extra_omitted_uuids=list(key),region_report=r));cache[key]=r['connected']
        print('Trial',len(trials),'extra objects',len(ids),'nets',len(trials[-1]['extra_nets']),'connected',r['connected'],flush=True)
        return r['connected']
    def reduce_groups(groups):
        selected=list(groups);granularity=2
        while len(selected)>1 and time.monotonic()<deadline:
            chunks=[selected[i::granularity] for i in range(granularity)];reduced=False
            for chunk in chunks:
                other=[g for g in selected if g not in chunk]
                if check({u for g in other for u in groups[g]}):
                    selected=other;granularity=max(2,granularity-1);reduced=True;break
                if time.monotonic()>=deadline:break
            if not reduced:
                if granularity>=len(selected):break
                granularity=min(len(selected),granularity*2)
        return selected
    selected={u for ids in candidates.values() for u in ids};possible=check(selected)
    minimal=False
    if possible:
        names=reduce_groups(candidates);selected={u for n in names for u in candidates[n]}
        print('Reduced net groups:',sorted(names),flush=True)
        if time.monotonic()<deadline:
            ids=reduce_groups({u:[u] for u in sorted(selected)});selected=set(ids)
        minimal=True
        for uid in sorted(selected):
            if time.monotonic()>=deadline:minimal=False;break
            if check(selected-{uid}):selected.remove(uid)
    paths=[cp,rp,bp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_region_reachability.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-target-cutset-02';out.mkdir(exist_ok=False)
    report=dict(source_sha256={str(p):sha(p) for p in paths},protected_net_names=sorted(protected),base_removed_uuids=sorted(base),trials=trials,potential_access=possible,selected_extra_nets=sorted({objects[u]['net'] for u in selected}) if possible else None,selected_extra_uuids=sorted(selected) if possible else None,inclusion_minimal_within_tested_objects=minimal,restoration_not_proven=True,candidate_emitted=False,fabrication_released=False)
    (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Final extra objects:',len(selected),'nets:',report['selected_extra_nets'],'minimal:',minimal,flush=True)
if __name__=='__main__':run()
