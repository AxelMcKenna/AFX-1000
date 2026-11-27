"""Prepare the verified handle revision while preserving latest selected PCBs."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    results=json.loads((H/'results.json').read_text())
    assert len(results['results'])==94 and all(r['passed'] for r in results['results'])
    w.assert_current({'sources':results['snapshot_sha256']})
    current,parts,checks,_=w.load_manifest()
    old,oldparts,oldchecks,_=w.load_manifest(H/'previous-manifest.json')
    assert parts==oldparts and checks==oldchecks,'Intervening mechanical/check change requires reintegration'
    status=w.board_state(current);assert status['geometry_fresh'] and not status['errors']
    base=H/'selection-base.json';assert not base.exists(),'Preserve prior selection evidence'
    base.write_bytes((w.HERE/'current.json').read_bytes())
    candidate=json.loads((H/'candidate.json').read_text())
    candidate['boards']=current['boards']
    candidate['mechanical_capture']=current['mechanical_capture']
    candidate['unresolved']=[x for x in candidate['unresolved'] if not x.startswith('Removable-handle integration candidate:')]
    candidate['unresolved'].append('Removable lever handle with sourced nominal cap screw and enlarged operating envelope is modeled; printed threads, tightening/retention, exact tool/hand access, wire flex and full wired-lid removal remain unqualified. The local16mm vertical lift check is not full service qualification.')
    registry=json.loads((H/'registry.json').read_text())
    for p in [Path(__file__),base,H/'results.json']:
        registry['source_sha256'][w.relative(p)]=w.sha(p)
    (H/'selected-registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    candidate['registries']=[w.relative(H/'selected-registry.json')]
    (H/'selected-candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    _,newparts,newchecks,_=w.load_manifest(H/'selected-candidate.json')
    assert len(newparts)==77 and len(newchecks)==94
    print('Preserved latest board selection:',candidate['boards'])
if __name__=='__main__':run()
