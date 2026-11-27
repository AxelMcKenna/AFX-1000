"""Prepare a frozen, unselected integration candidate for S02/S03 and ground bows."""
import copy,json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists(): previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,components,checks,_=w.load_manifest(previous)
    old='panel_ground_r15_scene_links';new='panel_ground_r22_scene_links'
    assert old in components and new not in components
    del components[old]
    bindings=dict(data['_loaded_sources'])
    bindings[w.relative(Path(__file__))]=w.sha(Path(__file__))
    registry={'schema_version':1,'components':list(components.values()),'source_sha256':bindings,
              'intentional_contacts':sum((c['intentional_contacts'] for c in data['contracts']),[])}
    assert not any(old in c.get('components',[]) for c in registry['intentional_contacts'])
    (HERE/'base-registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    candidate=json.loads(previous.read_text())
    candidate['registries']=[w.relative(HERE/'base-registry.json')]+[
      'hardware/cad/two_board_installation_06/workflow_adapter/'+n for n in
      ['ground-signal-clearance-registry.json','adjacent-signals-registry.json']]
    for check in candidate['checks']:
        for side in ['left','right']:check[side]=[new if c==old else c for c in check[side]]
    signals=['panel_signal_r21_scene1','panel_signal_r21_scene3']
    for existing in list(candidate['checks']):
        if existing['id'].startswith('r20_signal_'):
            check=copy.deepcopy(existing);check['id']=check['id'].replace('r20_signal_','r21_signals_');check['left']=signals
            if check['id'].endswith('base_ground_supports'):check['right'].append('panel_signal_r20_scene2')
            candidate['checks'].append(check)
    candidate['checks'].append({'id':'r21_signals_mutual','left':signals[:1],'right':signals[1:],'expect':'empty'})
    candidate['boards']['signal']='hardware/cad/two_board_sensor_05/signal_dac/native-r50/signal_main.kicad_pcb'
    candidate['unresolved'][0]='Configured cross-fit checks cover selected integration; frozen local seating and terminal checks remain required. They do not prove every component pair.'
    candidate['unresolved'][-1]='S01/S02/S03 are receiving routes only; 227 further panel signal/power segments, terminations, supports and opening flex remain unqualified.'
    (HERE/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    d,c,k,_=w.load_manifest(HERE/'candidate.json')
    assert old not in c and all(n in c for n in signals+[new])
    for name in candidate['registries'][-2:]:
        r=json.loads((w.ROOT/name).read_text())
        assert set(r.get('requires_roles',[]))<=c.keys()
        assert not set(r.get('supersedes_roles',[]))&c.keys()
    fresh=w.board_state(d);assert fresh['geometry_fresh'],fresh
    (HERE/'freshness.json').write_text(json.dumps(fresh,indent=2)+'\n')
    print(len(c),'roles;',len(k),'checks; mechanical capture fresh')
if __name__=='__main__':run()
