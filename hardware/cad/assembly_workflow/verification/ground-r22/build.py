"""Select only the corrected ground candidate for full assembly screening."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,components,checks,_=w.load_manifest(previous)
    old='panel_ground_r15_scene_links';new='panel_ground_r22_scene_links'
    assert old in components and new not in components
    del components[old]
    bindings=dict(data['_loaded_sources']);bindings[w.relative(Path(__file__))]=w.sha(Path(__file__))
    contacts=sum((c['intentional_contacts'] for c in data['contracts']),[])
    assert not any(old in c.get('components',[]) for c in contacts)
    reg={'schema_version':1,'components':list(components.values()),'source_sha256':bindings,'intentional_contacts':contacts}
    (HERE/'base-registry.json').write_text(json.dumps(reg,indent=2)+'\n')
    m=json.loads(previous.read_text());m['registries']=[w.relative(HERE/'base-registry.json'),'hardware/cad/two_board_installation_06/workflow_adapter/ground-signal-clearance-registry.json']
    for c in m['checks']:
        for side in ['left','right']:c[side]=[new if x==old else x for x in c[side]]
    m['checks'].append({'id':'r22_ground_base_supports','left':[new],'right':[x for x in components if x.startswith('base_')]+['panel_mates','panel_ground_r16_support','panel_ground_r17_selectors','panel_ground_r18_guide','panel_ground_r15_splice','panel_signal_r20_scene2'],'expect':'empty'})
    m['unresolved'][0]='Configured strict cross-fit checks cover selected integration, not every component pair. Frozen local seating and terminal evidence remains required.'
    m['unresolved'][5]='Selected ground geometry contains32 wires and1 splice; r22 replaces four scene links with radius18mm bows to free signal terminals. Physical joint preparation, supports, service slack and other panel wiring remain incomplete.'
    (HERE/'candidate.json').write_text(json.dumps(m,indent=2)+'\n')
    d,c,k,_=w.load_manifest(HERE/'candidate.json');assert old not in c and new in c and len(c)==67 and len(k)==27
    assert not any(x.startswith('panel_signal_r21_') for x in c)
    print('67 roles,27 checks; S02/S03 remain excluded')
if __name__=='__main__':run()
