"""Bind an additive extension to the cumulative r148 routing acceptance scope."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def combine(previous_path, extension_path, output):
    previous_path, extension_path, output = previous_path.resolve(), extension_path.resolve(), output.resolve()
    assert not output.exists(), 'Use a fresh candidate directory'
    previous, extension = (json.loads(p.read_text()) for p in (previous_path, extension_path))
    assert previous['baseline_opens'] == 162
    assert previous['expected_opens'] == extension['baseline_opens']
    assert not previous['new_vias'] and not extension['new_vias'], 'This gate is surface-only'
    before_ids = {uid for row in previous['routes'] for uid in row['segment_uuids']}
    new_ids = {uid for row in extension['routes'] for uid in row['segment_uuids']}
    assert not before_ids.intersection(new_ids), 'Extension UUIDs collide with retained copper'
    sources = {}
    for report in (previous, extension):
        for name, expected in report['source_sha256'].items():
            assert sha(ROOT / name) == expected, ('stale routing source', name)
            assert name not in sources or sources[name] == expected
            sources[name] = expected
    for path in (Path(__file__), previous_path, extension_path):
        sources[str(path.relative_to(ROOT))] = sha(path)
    pcb = extension_path.parent / 'signal_main.kicad_pcb'
    assert sha(pcb) == extension['candidate_sha256']
    routes = previous['routes'] + extension['routes']
    assert 162-len(routes) == extension['expected_opens']
    output.mkdir()
    shutil.copy2(pcb, output / pcb.name)
    report = {'baseline_opens': 162, 'expected_opens': extension['expected_opens'],
              'routes': routes, 'new_vias': [], 'native_acceptance_pending': True,
              'fabrication_released': False, 'source_sha256': sources,
              'candidate_sha256': sha(output / pcb.name),
              'extension_baseline_opens': extension['baseline_opens'],
              'extension_joins': len(extension['routes'])}
    (output / 'routing.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Cumulative candidate:', len(routes), 'joins;', report['expected_opens'], 'expected opens')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('previous', type=Path)
    parser.add_argument('extension', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    combine(args.previous, args.extension, args.output)
