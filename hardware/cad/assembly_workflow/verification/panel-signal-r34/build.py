"""Screen the fourth panel input against every selected modeled role."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent
REG='hardware/cad/two_board_installation_06/workflow_adapter/panel-input-r34-registry.json'
def run():
    previous=H/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    d,parts,_,_=w.load_manifest(previous)
    reg=json.loads((w.ROOT/REG).read_text())
    assert set(reg['requires_roles'])<=parts.keys()
    assert len(reg['components'])==1
    role=reg['components'][0]['id'];assert role not in parts
    candidate=json.loads(previous.read_text());candidate['registries'].append(REG)
    roles=sorted(parts);assert len(roles)==77
    new=[dict(id=f'r34_signal_external_{i//8+1}',left=[role],right=roles[i:i+8],expect='empty') for i in range(0,len(roles),8)]
    candidate['checks'].extend(new)
    old=json.loads((w.HERE/'verification/panel-signals-r21-r13/inventory-progress.json').read_text())
    completed=old['completed_receiving_edges']+[dict(source='D_J2002:6',target='button_scene_4:1')]
    inventory=w.ROOT/'hardware/cad/two_board_installation_06/r19_panel_inventory/inventory.json'
    wires=json.loads(inventory.read_text())['wires'];assert len(wires)==230 and len(completed)==4
    for edge in completed:assert sum(x['source']==edge['source'] and x['target']==edge['target'] for x in wires)==1
    assert len({x['source'] for x in completed})==4
    candidate['unresolved']=[x for x in candidate['unresolved'] if '227' not in x]
    candidate['unresolved']+=['S01–S04 are receiving routes only;226 remaining panel signal/power segments, terminations, supports and opening flex remain unqualified.', 'D_H4 main-mount conductive bearing area overlaps two LINK_SDA tracks and an LED_39 via on selected r98; source-bound repair is pending. Mechanical empty intersections do not qualify hardware/copper contact.']
    (H/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (H/'inventory-progress.json').write_text(json.dumps(dict(baseline_segments=230,completed_receiving_edges=completed,remaining_segments=226,fabrication_released=False,source_sha256={w.relative(inventory):w.sha(inventory),REG:w.sha(w.ROOT/REG),w.relative(Path(__file__)):w.sha(Path(__file__))}),indent=2)+'\n')
    (H/'scope.json').write_text(json.dumps(dict(external_roles=roles,new_checks=[x['id'] for x in new],all_external_roles_once=True,original_checks_preserved=True),indent=2)+'\n')
    _,p,c,_=w.load_manifest(H/'candidate.json');assert len(p)==78 and len(c)==104
    print('Prepared78roles/104checks, including10newchecksagainst77externalroles')
if __name__=='__main__':run()
