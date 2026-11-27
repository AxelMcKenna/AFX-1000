"""Separate own fan-connector reservations from foreign cooling interference."""
import json,shutil
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.assembly_workflow.pcb_updates.r44.build import boxes
HERE=Path(__file__).resolve().parent

def run():
    d,c,k,_=w.load_manifest(HERE/'candidate.json');capture=json.loads((w.ROOT/d['mechanical_capture']).read_text());excluded=set(json.loads((w.HERE/'base.json').read_text())['replaced_allocations']);own={'F_J202','F_J203'}
    rows=[r for r in capture['component_envelopes']+capture['tail_envelopes'] if r[0] not in excluded]
    s=HERE/'cooling-diagnostic.scad';s.write_text(boxes('coverage_other_allocations',[r for r in rows if r[0] not in own])+boxes('coverage_fan_connector_allocations',[r for r in rows if r[0] in own]))
    for name in ['coverage_other_allocations','coverage_fan_connector_allocations']:
        c[name]={'id':name,'source':w.relative(s),'module':name,'role':'receiving'};result,_=w.execute('component',c[name],c);assert result['passed']
    _,f=w.job('check',k['coverage_main_population_cooling'],c);out=HERE/'cooling-diagnosis';out.mkdir(exist_ok=False)
    for name in ['result.json','geometry.scad','geometry.stl','native.log']:shutil.copyfile(f/name,out/name)
    checks=[('installed','base_component_allocations','cooling_installed'),('shell','base_component_allocations','cooling_shell'),('foreign_harness','coverage_other_allocations','cooling_internal_harness'),('own_connectors','coverage_fan_connector_allocations','cooling_internal_harness')];results=[]
    for label,a,b in checks:
        q={'id':'coverage_cooling_'+label,'left':[a],'right':[b],'expect':'empty'};r,_=w.execute('check',q,c);assert not r['runtime_failure'];results.append({'check':label,'passed':r['passed'],'mesh':r['mesh'],'cache':w.relative(w.job('check',q,c)[1])});print(label,r['passed'],flush=True)
    (out/'diagnosis.json').write_text(json.dumps({'results':results,'source_sha256':{w.relative(p):w.sha(p) for p in [Path(__file__),s,w.ROOT/d['mechanical_capture']]},'fabrication_released':False},indent=2)+'\n')
if __name__=='__main__':run()
