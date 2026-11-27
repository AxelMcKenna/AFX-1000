"""Adopt detailed touch geometry and bundle ownership, not unqualified fan body caps."""
import copy,json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent
R24='hardware/cad/two_board_installation_06/workflow_adapter/fan-mates-registry.json'
R25='hardware/cad/two_board_installation_06/workflow_adapter/touch-module-registry.json'

def rename(v,mapping):
    if isinstance(v,str):return mapping.get(v,v)
    if isinstance(v,list):return [rename(x,mapping) for x in v]
    if isinstance(v,dict):return {k:rename(x,mapping) for k,x in v.items()}
    return v

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    d,c,k,_=w.load_manifest(previous);r24=json.loads((w.ROOT/R24).read_text());r25=json.loads((w.ROOT/R25).read_text())
    mapping={'cooling_internal_harness':'cooling_internal_harness_r24','controls_touch_module_receiving':'panel_touch_c3_r25'}
    for old in mapping:assert old in c;del c[old]
    h=copy.deepcopy(next(x for x in r24['components'] if x['id']=='cooling_internal_harness_r24'))
    adapter=HERE/'harness-only.scad';adapter.write_text('use <../../../two_board_installation_06/r24_fan_mates/harness.scad>\nmodule cooling_internal_harness_r24(){reconciled_fan_harness();}\n')
    h['source']=w.relative(adapter);h['uncertainty']='Only duplicated downstream bundle reservation is removed. All six physical wire paths and full original connector reservations remain. Formation, connector registration, terminations and service acceptance remain unqualified.'
    c[h['id']]=h
    assert len(r25['components'])==1
    touch=r25['components'][0];assert touch['id']=='panel_touch_c3_r25';c[touch['id']]=touch
    bindings=dict(d['_loaded_sources'])
    for name,r in [(R24,r24),(R25,r25)]:
        bindings[name]=w.sha(w.ROOT/name)
        for field in ['source_sha256','sources_sha256']:
            for path,digest in r.get(field,{}).items():
                assert w.sha(w.ROOT/path)==digest,path
                assert path not in bindings or bindings[path]==digest,path
                bindings[path]=digest
    for p in [Path(__file__),adapter,w.HERE/'verification/coverage-02/diagnosis/results.json',w.HERE/'verification/coverage-02/candidate.json']:bindings[w.relative(p)]=w.sha(p)
    contacts=rename(sum((x['intentional_contacts'] for x in d['contracts']),[]),mapping)
    # No r24 height cap, mating-body replacement, or entry mask enters this selection.
    reg={'schema_version':1,'components':list(c.values()),'source_sha256':bindings,'intentional_contacts':contacts}
    (HERE/'registry.json').write_text(json.dumps(reg,indent=2)+'\n')
    m=rename(json.loads(previous.read_text()),mapping);m['registries']=[w.relative(HERE/'registry.json')]
    diag_path=w.HERE/'verification/coverage-02/diagnosis/results.json';diag=json.loads(diag_path.read_text())
    wanted={'coverage02_controls_without_touch','coverage02_sensor_non_shell','coverage02_lid_non_shell','coverage02_touch_non_shell'}
    for row in diag['results']:
        if row['check']['id'] in wanted:
            assert row['passed'];m['checks'].append(rename(row['check'],mapping))
    cov=json.loads((w.HERE/'verification/coverage-02/candidate.json').read_text());m['checks'].append(rename(next(q for q in cov['checks'] if q['id']=='coverage_sensor_control_details'),mapping))
    m['unresolved'].insert(-1,'Detailed C3 touch model replaces the broad box; actual touch through-fastener stack, host/electrode wiring and physical tolerances remain unqualified. Raw touch/lever/lid shell-seat contacts are retained separately, not waived by non-shell checks.')
    m['unresolved']=[x.replace('Exact receiving envelope and bundle-to-individual-wire handoff reconciliation remains open','Bundle-to-individual ownership is corrected with all six paths retained; exact connector receiving envelope and terminal registration remain open') for x in m['unresolved']]
    (HERE/'candidate.json').write_text(json.dumps(m,indent=2)+'\n')
    _,parts,checks,_=w.load_manifest(HERE/'candidate.json');assert len(parts)==69 and len(checks)==39;assert 'cooling_fan_mates_r24' not in parts
    old=json.loads(previous.read_text());_,oldparts,_,_=w.load_manifest(previous)
    assert parts['base_component_allocations']==oldparts['base_component_allocations']
    print('69roles/39checks; exact six wires retained; original fan connector reservations unchanged')
if __name__=='__main__':run()
