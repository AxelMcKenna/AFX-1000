"""Integrate the service handle without dropping its operating envelope."""
import json,copy
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent
SERVICE=w.ROOT/'hardware/cad/two_board_service_10/handle_fastener_r2'

def run():
    prior=H/'previous-manifest.json'
    if not prior.exists():prior.write_bytes((w.HERE/'current.json').read_bytes())
    data,parts,_,_=w.load_manifest(prior)
    local,service,checks,_=w.load_manifest(SERVICE/'candidate.json')
    assert all(service[k]==v for k,v in parts.items()),'Selected geometry changed since service screen'
    proof=json.loads((SERVICE/'results.json').read_text())
    assert len(proof['results'])==37 and all(r['passed'] for r in proof['results'])
    w.assert_current({'sources':proof['snapshot_sha256']})
    contacts=json.loads((SERVICE/'contact-review.json').read_text())
    assert len(contacts['results'])==4 and all(r['classification_matches'] for r in contacts['results'])
    w.assert_current({'sources':contacts['source_sha256']})
    adapter=H/'motion.scad'
    adapter.write_text('use <../../../two_board_service_10/handle_fastener_r2/parts.scad>\nuse <../../../two_board_sensor_05/workflow_adapter/sensor.scad>\nmodule service_combined_lever_motion_r2(){sensor_lever_motion();cap_handle_motion_r2();}\n')
    parts=copy.deepcopy(parts)
    parts['sensor_lever_nominal']=dict(service['cap_handle_body_r2'],id='sensor_lever_nominal')
    parts['sensor_lever_motion']=dict(parts['sensor_lever_motion'],source=w.relative(adapter),module='service_combined_lever_motion_r2',description='Original lever envelope plus enlarged removable handle sweep')
    for name,part in service.items():
        if name not in parts and name!='cap_handle_body_r2':parts[name]=part
    assert len(parts)==77
    bindings=dict(data['_loaded_sources'])
    for path,expected in local['_loaded_sources'].items():
        assert path not in bindings or bindings[path]==expected,('Conflicting source snapshot',path)
        bindings[path]=expected
    for p in [Path(__file__),adapter,SERVICE/'results.json',SERVICE/'contact-review.json',SERVICE/'review.json']:
        bindings[w.relative(p)]=w.sha(p)
    intentional=sum((r['intentional_contacts'] for r in data['contracts']),[])
    intentional += [dict(components=['sensor_lever_nominal','cap_handle_r2'],reason='Nominal socket roof seats atZ55.6; raw contact retained; no blanket waiver'),
                    dict(components=['cap_handle_screw_r2','cap_handle_r2'],reason='Flat screw head seats atZ56.5; raw contact retained'),
                    dict(components=['cap_handle_screw_r2','sensor_lever_nominal'],reason='Solid screw/tap-pilot overlap is future tapped threadZ50.5..55.6; not clearance or strength proof')]
    registry=dict(schema_version=1,components=list(parts.values()),source_sha256=bindings,intentional_contacts=intentional)
    (H/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    candidate=json.loads(prior.read_text());candidate['registries']=[w.relative(H/'registry.json')]
    for q in checks.values():
        q=copy.deepcopy(q);q['right']=['sensor_lever_nominal' if x=='cap_handle_body_r2' else x for x in q['right']]
        candidate['checks'].append(q)
    candidate['unresolved'].append('Removable-handle integration candidate: exact screw shape and receiving budget do not qualify printed threads, torque/retention, hand/tool use or full wired-lid removal. Original operating envelope retained and enlarged; full57+37checks required before selection.')
    (H/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    _,c,k,_=w.load_manifest(H/'candidate.json');assert len(c)==77 and len(k)==94
    print('77roles/94checks; existing motion retained and enlarged; nominal body replaced')
if __name__=='__main__':run()
