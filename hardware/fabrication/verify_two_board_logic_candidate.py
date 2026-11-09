"""Bind an independently audited additive logic-routing working candidate."""
import argparse
import json
import re
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    parser = argparse.ArgumentParser()
    for name in ['candidate', 'parent', 'capture', 'fill', 'audit', 'manifest']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--expected-opens', required=True, type=int)
    parser.add_argument('--expected-closed', required=True, type=int)
    args = parser.parse_args()
    for name in ['candidate', 'parent', 'capture', 'fill', 'audit', 'manifest']:
        assert all(c.isalnum() or c in '-_.' for c in getattr(args, name))
    out = STAGING / args.candidate
    target = out / 'final-review.json'
    assert not target.exists()
    reports = [STAGING / args.parent / 'final-review.json',
               STAGING / args.capture / 'capture.json',
               STAGING / args.fill / 'local-plane-fill.json',
               out / args.audit, out / args.manifest, out / 'review.json',
               out / 'visual-review.json', out / 'plots/native-plots.json',
               *sorted((out / 'plots').glob('*-render.json'))]
    cached = {}
    bindings = 0
    for report in reports:
        data = json.loads(report.read_text())
        for key in ['source_sha256', 'artifact_sha256']:
            for name, digest in data.get(key, {}).items():
                path = Path(name)
                if not path.is_absolute():
                    path = (REPO if name.startswith(('hardware/', 'tests/')) else report.parent) / path
                if path not in cached:
                    cached[path] = sha(path)
                assert cached[path] == digest, (report, name)
                bindings += 1
    native = json.loads((out / 'review.json').read_text())
    audit = json.loads((out / args.audit).read_text())
    manifest = json.loads((out / args.manifest).read_text())
    capture = json.loads((STAGING / args.capture / 'capture.json').read_text())
    visual = json.loads((out / 'visual-review.json').read_text())
    assert native['opens'] == audit['new_opens'] == capture['native_uncapped_opens'] == args.expected_opens
    assert audit['closed_connections'] == manifest['expected_closed_connections'] == args.expected_closed
    assert native['geometry_findings'] == native['schematic_parity_findings'] == 0
    assert audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    assert audit['all_other_native_groups_preserved']
    assert audit['all_eleven_supply_planes_unchanged'] and audit['quiet_network_fields_preserved'] == 7
    assert len(audit['new_reference_checks']) == len(manifest['routes'])
    assert all(row['uncovered_mm2'] < 1e-6 for row in audit['new_reference_checks'])
    assert visual['inspection_complete'] and visual['views_inspected']
    old = STAGING / 'two-board-fabrication-status-50/final-verification.json'
    for name, digest in json.loads(old.read_text())['documentation_snapshot_sha256'].items():
        assert sha(REPO / name) == digest, name
    links = []
    for link in re.findall(r'\]\(([^)]+)\)', (out / 'README.md').read_text()):
        if '://' in link or link.startswith('#'):
            continue
        path = (out / link.split('#')[0]).resolve()
        assert path.exists(), link
        links.append(str(path.relative_to(REPO)))
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p)
                               for p in [Path(__file__), *reports, out / 'README.md', old]},
                  verified_bindings=bindings, local_documentation_links_checked=len(links),
                  working_candidate=args.candidate, selected_checkpoint='TBP50',
                  power_opens=args.expected_opens, signal_opens=251,
                  closed_connections=args.expected_closed,
                  retained_reference_checks=len(audit['retained_reference_checks']),
                  prior_checkpoint_documentation_unchanged=True,
                  fabrication_released=False, goal_complete=False)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__':
    run()
