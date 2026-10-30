#!/usr/bin/env python3
"""Audit public User drum settings against the actual Engine without fitting."""
import argparse
import concurrent.futures
import json
import os
import subprocess
from pathlib import Path

import numpy as np

from tools import rmx_drum_user_settings as loader
from tools.rmx_drums import DRUMS, FRAMES, checked, plan_for, require
from tools.rmx_drums_fx import source_hashes as core_hashes
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav


def bindings():
    return core_hashes() | {n: sha256(Path(n)) for n in ['tools/rmx_drum_user_settings.py', 'tools/rmx_drum_user_match.py', 'tools/drum_user_probe.cpp']}


def original_plan(c, inventory, session):
    plan = plan_for(c, inventory)
    plan['parameters'] = [s | dict(value=0 if s['name'] == 'DefaultSwitch' else 1 if s['name'] == 'UserSwitch' else s['value']) for s in plan['parameters']]
    plan['initial_state'] = dict(path=c['name'] + '.bin', sha256=sha256(session / (c['name'] + '.bin')))
    return plan


def original(a, c):
    requested = a.session / (c['name'] + '.bin'); rsd = a.session / (c['name'] + '.RSD')
    require(sha256(requested) == c['requested_state_sha256'] and c['customization_retained'], 'Requested User state changed')
    require(rsd.read_text() == loader.xml(c['settings']), 'RSD settings changed')
    saved = a.session / c['name'] / 'state-before.bin'
    require(loader.chunks(saved.read_bytes())[b'cstm'] == loader.chunks(requested.read_bytes())[b'cstm'], 'Original customization retention changed')
    x, provenance = checked(a.session, c, plan_builder=lambda c, inv: original_plan(c, inv, a.session))
    r = json.loads((a.session / c['name'] / 'receipt.json').read_text())
    require(r['host_sha256'] == sha256(a.host), 'Original host changed')
    for member in r['plugin']['binary_files']:
        require(sha256(Path(r['plugin']['bundle']) / member['path']) == member['sha256'], 'Original binary changed')
    return x, provenance | dict(requested_state_sha256=sha256(requested), rsd_sha256=sha256(rsd))


def schedule(c):
    pad = list(DRUMS).index(c['drum']); node = ['Kick', 'Snare', 'Clap', 'Hihat'][pad]; values = c['settings'].get(node, {})
    return 'RMX_DRUM_USER 1\n' + ' '.join(str(v) for v in [pad, c['level'], c['pitch'], c['block'],
        values.get('GainCb', 3), values.get('DecayCb', 1), values.get('EnvelopeCb', 0)]) + '\n' + ''.join(str(f) + '\n' for f in c['hits'])


def predict(a):
    require(a.stage in ['fresh', 'fresh2'], 'Use a fresh settings recipe')
    bound = bindings(); binary = sha256(a.renderer); root = new_directory(a.session); (root / 'predictions').mkdir()
    write_wav(root / 'silence.wav', 48000, np.zeros(FRAMES * 2)); outputs = {}
    for c in loader.recipe(a.stage):
        plan = root / 'predictions' / (c['name'] + '.tsv'); plan.write_text(schedule(c))
        out = plan.with_suffix('.wav'); dry = plan.with_name(plan.stem + '-dry.wav')
        run([a.renderer, root / 'silence.wav', out, plan, dry]); outputs[c['name']] = sha256(out)
    require(bound == bindings() and binary == sha256(a.renderer), 'Prediction source/binary changed')
    save_json(root / 'prediction.json', dict(kind='rmx220-user-drum-sealed-audio-prediction', stage=a.stage, cases=loader.recipe(a.stage),
        source_sha256=bound, renderer=str(a.renderer.resolve()), renderer_sha256=binary, output_sha256=outputs,
        input_sha256=sha256(root / 'silence.wav'), acceptance=ACCEPTANCE,
        expected='All whole/second/attack/body/decay1%perchannel gates plus complete prediction/native/sanitizer WAV identity.'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['session', 'renderer']: p.add_argument('--' + name, type=Path, required=True)
    for name in ['host', 'output', 'prediction']: p.add_argument('--' + name, type=Path)
    p.add_argument('--predict', action='store_true'); p.add_argument('--stage', default='fresh'); p.add_argument('--regression', action='store_true')
    p.add_argument('--sanitizer', type=Path); p.add_argument('--workers', type=int, default=2)
    a = p.parse_args(); require(1 <= a.workers <= 4, 'Invalid worker count'); bound = bindings(); binary = sha256(a.renderer)
    if a.predict: return predict(a)
    require(a.host is not None and a.output is not None, 'Comparison needs host and output')
    symbols = subprocess.check_output(['nm', '-C', str(a.renderer)], text=True); require('rmx::Engine::process(' in symbols, 'Fixture must use the actual Engine')
    matrix_path = a.session / 'matrix.json'; matrix_hash = sha256(matrix_path); matrix = json.loads(matrix_path.read_text())
    expected = loader.recipe(matrix.get('stage', 'loader'))
    require(len(matrix['cases']) == len(expected) and all(all(row[k] == v for k, v in c.items()) for c, row in zip(expected, matrix['cases'], strict=True)), 'Original recipes changed')
    cases = [{k: v for k, v in row.items() if k != 'receipt_sha256'} for row in matrix['cases']]
    prediction = None
    if a.prediction:
        prediction = json.loads(a.prediction.read_text())
        require(prediction['cases'] == expected and prediction['acceptance'] == ACCEPTANCE, 'Prediction programs/gates changed')
        require(matrix['prediction_sha256'] == sha256(a.prediction) == sha256(a.session / 'prediction.json'), 'Captured prediction binding changed')
        require(sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Prediction binary changed')
        if not a.regression: require(prediction['source_sha256'] == bound and prediction['renderer_sha256'] == binary, 'Prospective candidate changed')
    root = new_directory(a.output); sanitizer_hash = sha256(a.sanitizer) if a.sanitizer else None
    def one(c):
        x, provenance = original(a, c); plan = root / (c['name'] + '.tsv'); plan.write_text(schedule(c))
        out = plan.with_suffix('.wav'); dry = root / (c['name'] + '-dry.wav')
        run([a.renderer, a.session / 'silence.wav', out, plan, dry])
        rate, y = float_wav(out); drate, d = float_wav(dry)
        require(rate == drate == 48000 and x.shape == y.shape == d.shape == (FRAMES, 2) and not np.any(d), 'User candidate extent/rate/dry changed')
        if prediction:
            require(sha256(a.prediction.parent / 'predictions' / (c['name'] + '.wav')) == prediction['output_sha256'][c['name']], 'Prediction WAV changed')
            if not a.regression: require(sha256(out) == prediction['output_sha256'][c['name']], 'Output differs from sealed prediction')
        sanitized = None
        if a.sanitizer:
            san = root / (c['name'] + '-asan.wav'); sd = root / (c['name'] + '-asan-dry.wav')
            r = subprocess.run([str(a.sanitizer), str(a.session / 'silence.wav'), str(san), str(plan), str(sd)],
                capture_output=True, text=True, timeout=120,
                env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            require(r.returncode == 0 and not r.stderr, 'Sanitizer failure: ' + r.stderr)
            sanitized = sha256(san) == sha256(out) and sha256(sd) == sha256(dry)
            require(sanitized, 'Sanitizer User WAV bytes differ')
        complete_bits = bool(np.array_equal(x.view('u4'), y.view('u4')))
        x, y = x[32:].astype(float), y[32:].astype(float)
        windows = [(0, len(x), 'complete')] + [(s, min(s + 48000, len(x)), 'second') for s in range(0, len(x), 48000)]
        for frame in c['hits']:
            windows += [(frame, min(frame + 256, len(x)), 'attack'), (frame, min(frame + 48000, len(x)), 'body'),
                        (frame + 4800, min(frame + 120000, len(x)), 'decay')]
        scores = [dict(start=s, stop=t, kind=k, score=screen(x[s:t], y[s:t])) for s, t, k in windows if t > s]
        row = provenance | dict(passed=all(w['score']['passed'] for w in scores), windows=scores, settings=c['settings'],
            candidate_sha256=sha256(out), dry_sha256=sha256(dry), schedule_sha256=sha256(plan),
            sanitizer_byte_identical=sanitized, complete_sample_bit_identity=complete_bits)
        print('PASS' if row['passed'] else 'FAIL', c['name'], flush=True); return row
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool: rows = list(pool.map(one, cases))
    require(bound == bindings() and binary == sha256(a.renderer) and matrix_hash == sha256(matrix_path), 'Source, binary or Original matrix changed')
    if a.sanitizer: require(sanitizer_hash == sha256(a.sanitizer), 'Sanitizer changed')
    save_json(root / 'comparison.json', dict(kind='rmx220-drum-user-settings-comparison', live_engine=True, passed=all(r['passed'] for r in rows),
        cases=rows, programs=len(rows), source_sha256=bound, renderer_sha256=binary, sanitizer_sha256=sanitizer_hash,
        acceptance=ACCEPTANCE, original_matrix_sha256=matrix_hash,
        prediction_sha256=sha256(a.prediction) if prediction else None, prospective=prediction is not None and not a.regression,
        scope='Actual Engine User48k, default pitch ranges, dry factory drums. Public RSD/native-state loading and User switches verified. '
        'Fixed32/32, unchanged1%perchannel whole/second/attack/body/decay screens. Discovery regressions, not prospective qualification.'))


if __name__ == '__main__':
    main()
