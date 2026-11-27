"""Add NUDGE UP with complete prior-role coverage, without selecting it."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

H = Path(__file__).resolve().parent
REG = 'hardware/cad/two_board_installation_06/workflow_adapter/panel-input-r38-registry.json'


def run():
    previous = H / 'previous-manifest.json'
    if not previous.exists():
        previous.write_bytes((w.HERE / 'current.json').read_bytes())
    _, parts, checks, _ = w.load_manifest(previous)
    reg = json.loads((w.ROOT / REG).read_text())
    w.assert_current({'sources': reg['source_sha256']})
    assert set(reg['requires_roles']) <= parts.keys()
    assert len(parts) == 80 and len(checks) == 125
    assert len(reg['components']) == 1
    role = reg['components'][0]['id']
    assert role not in parts
    external = sorted(parts)
    new = [dict(id=f'r38_signal_external_{i // 8 + 1}', left=[role], right=external[i:i + 8], expect='empty')
           for i in range(0, len(external), 8)]
    candidate = json.loads(previous.read_text())
    candidate['registries'].append(REG)
    candidate['checks'].extend(new)
    candidate['unresolved'] = [x.replace('S01–S06', 'S01–S07').replace('224 remaining', '223 remaining') for x in candidate['unresolved']]
    (H / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    progress = json.loads((w.HERE / 'verification/panel-inputs-r37/inventory-progress.json').read_text())
    completed = progress['completed_receiving_edges'] + reg['candidate_inventory_edges']
    inventory = w.ROOT / 'hardware/cad/two_board_installation_06/r19_panel_inventory/inventory.json'
    rows = json.loads(inventory.read_text())['wires']
    assert len(completed) == 7 and len({(e['source'], e['target']) for e in completed}) == 7 and len(rows) == 230
    for edge in completed:
        matches = [r for r in rows if r['source'] == edge['source'] and r['target'] == edge['target']]
        assert len(matches) == 1 and ('net' not in edge or matches[0]['net'] == edge['net'])
    (H / 'candidate-inventory.json').write_text(json.dumps(dict(baseline_segments=230, receiving_edges_after_acceptance=completed,
        remaining_segments_after_acceptance=223, selected=False, physical_harness_complete=False,
        source_sha256={REG: w.sha(w.ROOT / REG), w.relative(inventory): w.sha(inventory)}), indent=2) + '\n')
    (H / 'scope.json').write_text(json.dumps(dict(prior_checks=125, original_checks_preserved=True,
        all_prior_roles_once=True, external_roles=external, new_checks=[c['id'] for c in new]), indent=2) + '\n')
    _, final_parts, final_checks, _ = w.load_manifest(H / 'candidate.json')
    assert len(final_parts) == 81 and len(final_checks) == 135
    print('Prepared81roles/135checks including10new checks against all80priorroles')


if __name__ == '__main__':
    run()
