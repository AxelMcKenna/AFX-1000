"""Integrate corrected S02/S03 against selected r62 PCB and r22 ground."""
import copy,json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent
REG='hardware/cad/two_board_installation_06/workflow_adapter/adjacent-signals-registry.json'

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    d,c,k,_=w.load_manifest(previous);assert 'panel_ground_r22_scene_links' in c and 'panel_ground_r15_scene_links' not in c
    reg=json.loads((w.ROOT/REG).read_text());assert set(reg['requires_roles'])<=c.keys()
    signals=[x['id'] for x in reg['components']];assert len(signals)==2 and not set(signals)&c.keys()
    candidate=json.loads(previous.read_text());candidate['registries'].append(REG)
    for existing in list(candidate['checks']):
        if existing['id'].startswith('r20_signal_'):
            q=copy.deepcopy(existing);q['id']=q['id'].replace('r20_signal_','r21_signals_');q['left']=signals
            if q['id'].endswith('base_ground_supports'):q['right'].append('panel_signal_r20_scene2')
            candidate['checks'].append(q)
    candidate['checks'].append({'id':'r21_signals_mutual','left':signals[:1],'right':signals[1:],'expect':'empty'})
    baseline=w.ROOT/'hardware/cad/two_board_installation_06/r19_panel_inventory/inventory.json';inv=json.loads(baseline.read_text());assert len(inv['wires'])==230
    completed=[{'source':'D_J2002:2','target':'button_scene_2:1'}]+reg['completed_inventory_edges'];assert len({x['source'] for x in completed})==3
    for edge in completed:assert sum(x['source']==edge['source'] and x['target']==edge['target'] for x in inv['wires'])==1,edge
    candidate['unresolved'][-1]='S01/S02/S03 are receiving routes only;227 remaining panel signal/power segments, terminations, supports and opening flex remain unqualified.'
    (HERE/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (HERE/'inventory-progress.json').write_text(json.dumps({'baseline_segments':230,'completed_receiving_edges':completed,'remaining_segments':227,'fabrication_released':False,'source_sha256':{w.relative(baseline):w.sha(baseline),REG:w.sha(w.ROOT/REG),w.relative(Path(__file__)):w.sha(Path(__file__))}},indent=2)+'\n')
    _,parts,checks,_=w.load_manifest(HERE/'candidate.json');assert len(parts)==69 and len(checks)==34;print('69roles/34checks;3inventory edges;227remaining')
if __name__=='__main__':run()
