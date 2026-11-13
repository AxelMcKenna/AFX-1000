"""Stage additive panel-wire candidates with full prior-role and mutual coverage.

This prepares reviewable manifests only. It never selects a design or runs CAD.
Holder replacements require a separate explicit integration review.
"""
import argparse
import itertools
import json
import re
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w


def validate(registry, parts, completed, inventory):
    assert set(registry['requires_roles']) <= parts.keys(), 'Missing required assembly roles'
    new = registry['components']
    ids = [p['id'] for p in new]
    assert ids and len(ids) == len(set(ids)) and not set(ids) & parts.keys(), 'Duplicate component'
    assert all(not p.get('replaces_component') and p['role'] == 'receiving' for p in new), 'Only additive receiving wires are supported'
    edges = registry['candidate_inventory_edges']
    assert len(edges) == len(new), 'Each new role must have one inventory edge'
    all_edges = completed + edges
    pairs = [(e['source'], e['target']) for e in all_edges]
    assert len(pairs) == len(set(pairs)), 'Edge already selected or duplicated'
    for edge in all_edges:
        found = [r for r in inventory if r['source'] == edge['source'] and r['target'] == edge['target']]
        assert len(found) == 1, 'Unknown inventory edge'
        assert 'net' not in edge or edge['net'] == found[0]['net'], 'Wrong electrical net'
    assert all('net' in e for e in edges), 'New edges require explicit net identity'
    return ids, all_edges


def stage(registry, progress, output, prefix):
    registry, progress, output = (p.resolve() for p in [registry, progress, output])
    assert all(p.is_relative_to(w.ROOT) for p in [registry, progress, output])
    assert re.fullmatch(r'[a-z][a-z0-9_]*', prefix)
    assert not (output / 'candidate.json').exists(), 'Preserve existing candidates; use a new output directory'
    assert not (output / 'previous-manifest.json').exists(), 'Preserve partial staging evidence'
    previous = w.HERE / 'current.json'
    previous_raw = previous.read_bytes()
    _, parts, checks, _ = w.load_manifest(previous)
    assert previous.read_bytes() == previous_raw, 'Selection changed during staging'
    reg = json.loads(registry.read_text())
    w.assert_current({'sources': reg['source_sha256']})
    old_progress = json.loads(progress.read_text())
    w.assert_current({'sources': old_progress['source_sha256']})
    assert old_progress['selected'] and not old_progress['physical_harness_complete']
    inventory_path = w.ROOT / 'hardware/cad/two_board_installation_06/r19_panel_inventory/inventory.json'
    inventory = json.loads(inventory_path.read_text())['wires']
    ids, edges = validate(reg, parts, old_progress['completed_receiving_edges'], inventory)
    external = sorted(parts)
    new_checks = [dict(id=f'{prefix}_external_{i // 8 + 1}', left=ids, right=external[i:i + 8], expect='empty')
                  for i in range(0, len(external), 8)]
    new_checks += [dict(id=f'{prefix}_mutual_{i + 1}', left=[a], right=[b], expect='empty')
                   for i, (a, b) in enumerate(itertools.combinations(ids, 2))]
    candidate = json.loads(previous_raw)
    candidate['registries'].append(w.relative(registry))
    candidate['checks'].extend(new_checks)
    remaining = len(inventory) - len(edges)
    candidate['unresolved'] = [re.sub(r'S01–S\d+ are receiving routes only;\d+ remaining',
        f'S01–S{len(edges):02} are receiving routes only;{remaining} remaining', s) for s in candidate['unresolved']]
    output.mkdir(parents=True, exist_ok=True)
    assert previous.read_bytes() == previous_raw, 'Selection changed during staging'
    (output / 'previous-manifest.json').write_bytes(previous_raw)
    builder = output / 'staging-source.py'
    builder.write_bytes(Path(__file__).read_bytes())
    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2) + '\n')
    save('candidate.json', candidate)
    save('candidate-inventory.json', dict(baseline_segments=len(inventory), receiving_edges_after_acceptance=edges,
        remaining_segments_after_acceptance=remaining, selected=False, physical_harness_complete=False,
        source_sha256={w.relative(p): w.sha(p) for p in [registry, progress, inventory_path, builder]}))
    save('scope.json', dict(original_checks_preserved=True, prior_roles=len(parts), prior_checks=len(checks),
        new_roles=ids, external_roles=external, new_checks=[c['id'] for c in new_checks],
        union_against_every_prior_role=True, every_new_pair_checked=True, no_replacements_or_contact_waivers=True))
    _, final_parts, final_checks, _ = w.load_manifest(output / 'candidate.json')
    assert len(final_parts) == len(parts) + len(ids) and len(final_checks) == len(checks) + len(new_checks)
    assert candidate['checks'][:len(checks)] == list(checks.values())
    print(f'Prepared {len(final_parts)} roles / {len(final_checks)} checks; {remaining} segments after acceptance')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--progress', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prefix', required=True)
    args = parser.parse_args()
    stage(args.registry, args.progress, args.output, args.prefix)
