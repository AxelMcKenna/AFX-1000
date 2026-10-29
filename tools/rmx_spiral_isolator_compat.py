#!/usr/bin/env python3
"""Preserve all qualified Isolator programs after integrating live Spiral."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from tools import rmx_isolate_modes as modes
from tools import rmx_trans_match as trans
from tools import rmx_cut_match as cut
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import new_directory
from tools.rmx_drums import require


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['host', 'renderer', 'sanitizer', 'parent-root', 'original-root', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    bound = modes.source_hashes() | trans.bindings() | cut.bindings()
    own = sha256(Path(__file__))
    binaries = {k: sha256(getattr(a, k)) for k in ['renderer', 'sanitizer']}
    for binary in [a.renderer, a.sanitizer]:
        require('rmx::Engine::process(' in subprocess.check_output(['nm', '-C', str(binary)], text=True),
                'Fixture must execute the live Engine')
    root = new_directory(a.output)
    rows, parents = [], {}
    for family in ['gate', 'trans', 'cut']:
        for stage in ['discovery', 'fresh', 'lifecycle', 'fresh2', 'lifecycle2']:
            if family == 'gate':
                suffix = 'former-fresh' if stage == 'fresh' else stage
                report = a.parent_root / f'gate-drive-live-first-{suffix}/comparison.json'
                published = Path(f'research/audio/measurements/2026-10-29-gate-drive-live-{suffix}.json')
                variant = 'discovery' if stage == 'discovery' else 'gate-' + stage
                cases = [c for c in modes.recipe(variant) if c['mode'] == 'gatedrive']
                original = 'rmx-isolate-modes-discovery-20261029' if stage == 'discovery' else {
                    'fresh': 'rmx-gate-drive-fresh-v2-20261029',
                    'fresh2': 'rmx-gate-drive-fresh2-20261029',
                    'lifecycle': 'rmx-gate-drive-lifecycle-20261029',
                    'lifecycle2': 'rmx-gate-drive-lifecycle2-20261029'}[stage]
                sources = modes.source(variant)
            else:
                module = trans if family == 'trans' else cut
                report = a.parent_root / (f'trans-live-final-{stage}' if family == 'trans' else f'cut-live-first-{stage}') / 'comparison.json'
                published = Path(f'research/audio/measurements/2026-10-29-{family}-' + ('roll' if family == 'trans' else 'add') + f'-live-{stage}.json')
                cases, sources = module.recipe(stage), module.source(stage)
                original = 'rmx-isolate-modes-discovery-20261029' if stage == 'discovery' else f'rmx-{family}-{stage}-v1-20261029'
            require(sha256(report) == sha256(published), 'Qualified parent report changed')
            parents[f'{family}/{stage}'] = sha256(report)
            old = {r['case']: r for r in json.loads(report.read_text())['cases']}
            args = SimpleNamespace(stage=stage, session=a.original_root / original, host=a.host)
            for c in cases:
                kwargs = {} if sources is None else dict(expected_source=sources[c['source']])
                _, provenance = modes.original(args, c, **kwargs)
                parent = old[c['name']]
                require(parent['passed'] and all(parent[k] == v for k, v in provenance.items()), 'Parent provenance changed')
                require(sha256(report.parent / (c['name'] + '.wav')) == parent['candidate_sha256'], 'Parent WAV changed')
                folder = root / family
                folder.mkdir(exist_ok=True)
                plan = folder / (c['name'] + '.tsv')
                plan.write_text(modes.schedule(c))
                require(sha256(plan) == parent['schedule_sha256'], 'Parent schedule changed')
                for name, binary in [('native', a.renderer), ('asan', a.sanitizer)]:
                    out = folder / (c['name'] + '-' + name + '.wav')
                    result = subprocess.run([str(x) for x in [binary, args.session / (c['source'] + '.wav'), out, plan]],
                        capture_output=True, text=True, timeout=120,
                        env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
                    require(result.returncode == 0 and not result.stderr, 'Native/sanitizer replay failed: ' + result.stderr)
                    require(sha256(out) == parent['candidate_sha256'], family + ' ' + name + ' audio changed: ' + c['name'])
                rows.append(provenance | dict(family=family, stage=stage, passed=True,
                    candidate_sha256=parent['candidate_sha256'], whole_wav_parent_byte_identity=True,
                    sanitized_whole_wav_byte_identity=True))
                print('UNCHANGED', family, stage, c['name'], flush=True)
    require(len(rows) == 438 and all(sum(r['family'] == f for r in rows) == 146 for f in ['gate', 'trans', 'cut']), 'Coverage changed')
    require(bound == modes.source_hashes() | trans.bindings() | cut.bindings()
            and own == sha256(Path(__file__))
            and binaries == {k: sha256(getattr(a, k)) for k in binaries}, 'Source/binary changed')
    save_json(root / 'verification.json', dict(kind='rmx220-spiral-prior-isolator-byte-compatibility', passed=True,
        programs=438, cases=rows, source_sha256=bound, verifier_sha256=own, binaries_sha256=binaries,
        parent_reports_sha256=parents, sanitizer_stderr_empty=True, scope='All 146 programs per Gate/Drive, Trans/Roll and Cut/Add. '
        'Current native and ASAN complete WAV bytes equal the qualified live parent. '
        'Original provenance rechecked. Existing reference gates transfer; no new wrapper or capture claim.'))


if __name__ == '__main__':
    main()
