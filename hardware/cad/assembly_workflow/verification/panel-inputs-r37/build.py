"""Integrate paired panel inputs and exact holder replacements for screening."""
import copy
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w

H = Path(__file__).resolve().parent
REG = 'hardware/cad/two_board_installation_06/workflow_adapter/panel-input-r37-registry.json'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def run():
    previous = H / 'previous-manifest.json'
    if not previous.exists():
        previous.write_bytes((w.HERE / 'current.json').read_bytes())
    data, parts, old_checks, _ = w.load_manifest(previous)
    reg = json.loads((w.ROOT / REG).read_text())
    w.assert_current({'sources': reg['source_sha256']})
    assert set(reg['requires_roles']) <= parts.keys()
    assert len(parts) == 78 and len(old_checks) == 104
    replacements = {p['replaces_component']: p['id'] for p in reg['components'] if 'replaces_component' in p}
    assert replacements == {'base_button_holders': 'panel_holders_r37', 'controls_button_mechanisms': 'panel_mechanisms_r37'}
    original = copy.deepcopy(parts)
    for item in reg['components']:
        item = copy.deepcopy(item)
        old_id = item.get('replaces_component')
        if old_id:
            old = parts.pop(old_id)
            # Selected physical geometry retains the old display role. This does
            # not qualify the printed part; the explicit uncertainty is retained.
            item['role'] = old['role']
            item['scene'] = old.get('scene', True)
        assert item['id'] not in parts
        parts[item['id']] = item
    assert parts['panel_holders_r37']['scene'] is False
    assert parts['panel_mechanisms_r37']['scene'] is True
    assert parts['panel_mechanisms_r37']['role'] == 'installed'
    assert all(parts[k] == v for k, v in original.items() if k not in replacements)
    bindings = dict(data['_loaded_sources'])
    w.merge_sources(bindings, reg['source_sha256'])
    for path in [w.ROOT / REG, Path(__file__), previous]:
        w.merge_sources(bindings, {w.relative(path): w.sha(path)})
    registry = dict(schema_version=1, components=list(parts.values()), source_sha256=bindings,
                    intentional_contacts=sum((r['intentional_contacts'] for r in data['contracts']), []),
                    unmodeled_installed_items=sum((r.get('unmodeled_installed_items', []) for r in data['contracts']), []))
    save(H / 'registry.json', registry)
    candidate = json.loads(previous.read_text())
    candidate['registries'] = [w.relative(H / 'registry.json')]
    for check in candidate['checks']:
        for side in ['left', 'right']:
            check[side] = [replacements.get(x, x) for x in check[side]]
    external = sorted(replacements.get(x, x) for x in original)
    wires = ['panel_signal_r37_tap', 'panel_signal_r37_auto']
    new_checks = [dict(id=f'r37_{wire}_external_{i // 8 + 1}', left=[wire], right=external[i:i + 8], expect='empty')
                  for wire in wires for i in range(0, len(external), 8)]
    new_checks.append(dict(id='r37_tap_auto_mutual', left=[wires[0]], right=[wires[1]], expect='empty'))
    candidate['checks'].extend(new_checks)
    candidate['unresolved'] = [x for x in candidate['unresolved'] if '226 remaining' not in x]
    candidate['unresolved'].append('S01–S06 are receiving routes only;224 remaining panel signal/power segments, terminations, supports and opening flex remain unqualified. Scene-zero holder relief preserves the upper0.5mm bearing layer; printed strength, retention and tolerance remain unqualified.')
    save(H / 'candidate.json', candidate)
    inventory = w.ROOT / 'hardware/cad/two_board_installation_06/r19_panel_inventory/inventory.json'
    rows = json.loads(inventory.read_text())['wires']
    progress = json.loads((w.HERE / 'verification/panel-signal-r34/inventory-progress.json').read_text())
    edges = progress['completed_receiving_edges'] + reg['candidate_inventory_edges']
    assert len(rows) == 230 and len(edges) == 6
    assert len({(e['source'], e['target']) for e in edges}) == 6
    for edge in edges:
        matches = [r for r in rows if r['source'] == edge['source'] and r['target'] == edge['target']]
        assert len(matches) == 1
        if 'net' in edge:
            assert matches[0]['net'] == edge['net']
    save(H / 'candidate-inventory.json', dict(baseline_segments=230, receiving_edges_after_acceptance=edges,
         remaining_segments_after_acceptance=224, selected=False, physical_harness_complete=False,
         source_sha256={w.relative(inventory): w.sha(inventory), REG: w.sha(w.ROOT / REG)}))
    save(H / 'scope.json', dict(replacements=replacements, original_checks_preserved_with_role_replacements=True,
         prior_checks=104, external_roles=external, new_checks=[c['id'] for c in new_checks],
         every_wire_against_all_prior_roles=True, no_contact_exclusions=True))
    _, final_parts, final_checks, _ = w.load_manifest(H / 'candidate.json')
    assert len(final_parts) == 80 and len(final_checks) == 125
    print('Prepared80roles/125checks;104priorchecks retained with exact holder substitutions;21new checks')


if __name__ == '__main__':
    run()
