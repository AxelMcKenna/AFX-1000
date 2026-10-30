#!/usr/bin/env python3
"""Original-reference drum performance campaigns, with sealed audio predictions."""
import argparse
import concurrent.futures
import json
import os
import subprocess
from pathlib import Path

import numpy as np

from tools.rmx_drums import DRUMS, FRAMES, checked, plan_for, require
from tools.rmx_drums_fx import source_hashes as core_hashes
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav


def bindings():
    return core_hashes() | {n: sha256(Path(n)) for n in ['tools/rmx_drum_performance.py', 'tools/drum_performance_probe.cpp']}


FRESH_STAGES = ('fresh', 'fresh2', 'hold-edges-fresh', 'tempo-fresh', 'overdub-fresh', 'overdub-fresh2')


def recipe(stage):
    if stage in ['hold-edges-fresh', 'tempo-fresh', 'overdub-fresh', 'overdub-fresh2']:
        base = stage.split('-fresh')[0]
        rng = np.random.default_rng({'hold-edges': 0x44504831, 'tempo': 0x44505431, 'overdub': 0x44504F31}[base] + (1 if stage.endswith('fresh2') else 0))
        rows = recipe(base)
        for index, c in enumerate(rows):
            c['name'] = c['name'].replace('performance-', 'performance-fresh2-' if stage.endswith('fresh2') else 'performance-fresh-')
            c['block'] = ([43, 131, 1021, 4096] if stage.endswith('fresh2') else [11, 79, 509, 2053])[index % 4]
            c['level'] = [17, 107, 191, 253][index % 4]
            c['pitch'] = int(rng.choice([3, 39, 117, 121, 128, 135, 139, 191, 239, 255]))
            shift = int(rng.integers(1001, 4000) if stage.endswith('fresh2') else rng.integers(7, 1000))
            for e in c['changes']:
                if e['frame'] != 1: e['frame'] += shift
            if base == 'tempo': c['bpm'] = [103, 129, 151, 179][index % 4]
            c['hits'] = [e['frame'] for e in c['changes'] if e['type'] == 'H']
        return rows
    if stage in ['tempo', 'overdub', 'hold-edges']:
        rows = []
        for pad, drum in enumerate(DRUMS):
            variants = ['auto91', 'auto137', 'auto160', 'auto187'] if stage == 'tempo' else ['free', 'quantized', 'mute', 'delete'] if stage == 'overdub' else ['initial', 'release-under-touch', 'reposition', 'empty-touch']
            for i, variant in enumerate(variants):
                position = [51, 102, 153, 204][i]
                changes = [(1, 'X', position), (48079 + pad * 6, 'H', pad), (48111 + pad * 6, 'R', pad),
                           (96113 + pad * 6, 'T', 1), (168191 + pad * 6, 'T', 0)]
                bpm, automatic, quantize, hold = 120, 0, 0, 0
                if stage == 'tempo':
                    bpm, automatic = [91, 137, 160, 187][i], 1
                    changes += [(192241, 'X', 255), (192273, 'T', 1), (384601, 'T', 0)]
                elif stage == 'overdub':
                    quantize = int(i == 1)
                    changes = [(31, 'O', 1)] + [(f + pad * 6 + off, k, pad) for f in [48079, 77113, 128193] for off, k in [(0, 'H'), (32, 'R')]]
                    if variant in ['mute', 'delete']:
                        button = 'M' if variant == 'mute' else 'D'
                        changes += [(240313, button, 1), (240337, 'H', pad), (240369, 'R', pad), (240401, button, 0)]
                        if variant == 'mute': changes += [(336491, 'M', 1), (336523, 'H', pad), (336555, 'R', pad), (336587, 'M', 0)]
                    changes += [(432701, 'O', 0)]
                elif variant == 'initial':
                    hold = 1; changes += [(312437, 'F', 0)]
                elif variant == 'release-under-touch':
                    changes = [e for e in changes if e[1] != 'T' or e[2] != 0]
                    changes += [(120157, 'F', 1), (144239, 'F', 0), (312437, 'T', 0)]
                elif variant == 'reposition':
                    changes += [(72091, 'F', 1), (80093, 'X', position), (192241, 'X', 255), (312437, 'F', 0)]
                else:
                    changes = [(1, 'X', position), (31, 'T', 1), (127, 'F', 1), (48079, 'H', pad), (48111, 'R', pad), (96113, 'X', position), (312437, 'F', 0)]
                rows.append(dict(name=f'performance-{stage}-{drum}-{variant}', drum=drum, variant=variant,
                    block=[8, 127, 512, 4093][i], level=128, pitch=128, position=position, bpm=bpm,
                    automatic=automatic, quantize=quantize, hold=hold, overdub=0,
                    hits=[f for f, k, v in changes if k == 'H'],
                    changes=[dict(frame=f, type=k, value=v) for f, k, v in sorted(changes, key=lambda e: e[0])]))
        return rows
    if stage in ['fresh', 'fresh2']:
        rng = np.random.default_rng(0x44504631 if stage == 'fresh' else 0x44504632)
        rows = recipe('discovery')
        for index, c in enumerate(rows):
            shift = int(rng.integers(7, 1000))
            c['name'] = c['name'].replace('performance-', 'performance-' + stage + '-')
            c['block'] = [8, 33, 257, 4096, 67, 509, 1024, 4093][index % 8]
            c['level'] = [17, 107, 133, 211, 253][index % 5]
            c['pitch'] = int(rng.choice([3, 39, 117, 121, 128, 135, 139, 191, 239, 255]))
            for e in c['changes']:
                if e['frame'] != 1: e['frame'] += shift
            c['hits'] = [e['frame'] for e in c['changes'] if e['type'] == 'H']
        return rows
    rows = []
    for pad, drum in enumerate(DRUMS):
        variants = ['baseline', 'hold-before', 'hold-during', 'hold-rearm', 'hold-reselect',
                    'quantize-eighth', 'quantize-half', 'quantize-toggle']
        for index, variant in enumerate(variants):
            hit = 48079 + pad * 6
            changes = [(1, 'X', [153, 102, 204, 51][pad]), (hit, 'H', pad), (hit + 32, 'R', pad)]
            quantize = int(variant.startswith('quantize'))
            position = 51 if variant == 'quantize-eighth' else 153 if variant == 'quantize-half' else [153, 102, 204, 51][pad]
            changes[0] = (1, 'X', position)
            if variant != 'baseline':
                changes += [(96113 + pad * 6, 'T', 1), (168191 + pad * 6, 'T', 0)]
            if variant == 'hold-before':
                changes += [(72091, 'F', 1), (312437, 'F', 0)]
            elif variant == 'hold-during':
                changes += [(120157, 'F', 1), (288373, 'F', 0)]
            elif variant == 'hold-rearm':
                changes += [(72091, 'F', 1), (192241, 'F', 0), (240313, 'X', position), (240337, 'T', 1), (312437, 'T', 0)]
            elif variant == 'hold-reselect':
                changes += [(72091, 'F', 1), (192241, 'H', (pad + 1) % 4), (192273, 'R', (pad + 1) % 4),
                            (192301, 'X', position), (240337, 'F', 0)]
            elif variant == 'quantize-toggle':
                changes += [(120157, 'Q', 0), (144239, 'Q', 1), (192241, 'X', 204), (192273, 'T', 1), (312437, 'T', 0)]
            c = dict(name=f'performance-{drum}-{variant}', drum=drum, variant=variant,
                     block=[128, 31, 263, 4093, 79, 127, 1021, 17][index], level=128, pitch=128,
                     position=position, bpm=120, automatic=0, quantize=quantize, hold=0, overdub=0,
                     hits=[e[0] for e in changes if e[1] == 'H'],
                     changes=[dict(frame=f, type=k, value=v) for f, k, v in sorted(changes, key=lambda e: e[0])])
            rows.append(c)
    require(stage == 'discovery', 'Unknown stage')
    return rows


def original_plan(c, inventory):
    plan = plan_for(c, inventory)
    values = dict(AutoButton=c['automatic'], QuantizeButton=c['quantize'], HoldButton=c['hold'], OverDubButton=c['overdub'])
    plan['bpm'] = c['bpm']
    plan['parameters'] = [p | dict(value=values.get(p['name'], p['value'])) for p in plan['parameters']]
    names = dict(T='XpadTouch', X='XpadPosition', F='HoldButton', L='XpadLevelVolume', P='PitchVolume',
                 Q='QuantizeButton', A='AutoButton', O='OverDubButton', M='MuteButton', D='DeleteButton')
    events = []
    for e in c['changes']:
        kind, raw = e['type'], e['value']
        name = list(DRUMS.values())[raw] if kind in ['H', 'R'] else names[kind]
        p = next(p for p in inventory['parameters'] if p['name'] == name)
        value = 1 if kind == 'H' else 0 if kind == 'R' else raw / 255 if kind in ['X', 'L', 'P'] else raw
        events.append({k: p[k] for k in ['name', 'id', 'index']} | dict(frame=e['frame'], type='parameter', value=value))
    plan['events'] = events
    return plan


def schedule(c):
    return 'RMX_DRUM_PERFORMANCE 1\n' + ' '.join(str(c[k]) for k in ['level', 'pitch', 'position', 'block', 'bpm', 'quantize', 'automatic', 'hold', 'overdub']) + '\n' + ''.join(f'{e["frame"]} {e["type"]} {e["value"]}\n' for e in c['changes'])


def capture(a):
    bound = bindings(); root = a.session
    prediction = None
    if a.stage not in FRESH_STAGES: new_directory(root)
    else:
        prediction = json.loads((root / 'prediction.json').read_text())
        require(prediction['source_sha256'] == bound and prediction['cases'] == recipe(a.stage), 'Frozen source/programs changed')
        require(sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Frozen binary changed')
        for name, h in prediction['output_sha256'].items(): require(sha256(root / 'predictions' / (name + '.wav')) == h, 'Frozen WAV changed')
    inventory = json.loads(run([a.host, 'inventory', a.plugin]))
    require(all(inventory[k] == v for k, v in IDENTITY.items()), 'Wrong Original identity')
    save_json(root / 'inventory.json', inventory)
    if a.stage not in FRESH_STAGES: write_wav(root / 'silence.wav', 48000, np.zeros(FRAMES * 2))
    def one(c):
        plan = root / (c['name'] + '.json'); save_json(plan, original_plan(c, inventory))
        run([a.host, 'render', a.plugin, root / 'silence.wav', plan, root / c['name'], c['block']])
        print('CAPTURED', c['name'], flush=True)
        return c | dict(receipt_sha256=sha256(root / c['name'] / 'receipt.json'))
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:
        rows = list(pool.map(one, recipe(a.stage)))
    require(bound == bindings(), 'Source changed during capture')
    save_json(root / 'matrix.json', dict(kind='rmx220-drum-performance-captures', stage=a.stage, cases=rows, source_sha256=bound,
        prediction_sha256=sha256(root / 'prediction.json') if prediction else None,
        scope='Default48k, declared public controls and fixed audio schedule. Discovery and sealed-prediction roles are separate.'))


def predict(a):
    require(a.stage in FRESH_STAGES, 'Use a fresh stage')
    bound = bindings(); binary = sha256(a.renderer); root = new_directory(a.session); (root / 'predictions').mkdir()
    write_wav(root / 'silence.wav', 48000, np.zeros(FRAMES * 2)); outputs = {}
    for c in recipe(a.stage):
        plan = root / 'predictions' / (c['name'] + '.tsv'); plan.write_text(schedule(c))
        out = plan.with_suffix('.wav'); dry = plan.with_name(plan.stem + '-dry.wav')
        run([a.renderer, root / 'silence.wav', out, plan, dry]); outputs[c['name']] = sha256(out)
    require(bound == bindings() and binary == sha256(a.renderer), 'Prediction source/binary changed')
    save_json(root / 'prediction.json', dict(kind='rmx220-drum-performance-sealed-audio-prediction', stage=a.stage, cases=recipe(a.stage),
        source_sha256=bound, renderer=str(a.renderer.resolve()), renderer_sha256=binary, input_sha256=sha256(root / 'silence.wav'),
        output_sha256=outputs, acceptance=ACCEPTANCE, expected='All whole/second/event1%perchannel gates and exact prediction/native/sanitizer bytes.'))


def original(a, c):
    x, provenance = checked(a.session, c, plan_builder=original_plan)
    r = json.loads((a.session / c['name'] / 'receipt.json').read_text())
    require(r['host_sha256'] == sha256(a.host), 'Original host changed')
    for member in r['plugin']['binary_files']:
        require(sha256(Path(r['plugin']['bundle']) / member['path']) == member['sha256'], 'Original binary changed')
    return x, provenance


def compare(a):
    bound = bindings(); binary = sha256(a.renderer); root = new_directory(a.output)
    symbols = subprocess.check_output(['nm', '-C', str(a.renderer)], text=True)
    require('rmx::Engine::process(' in symbols, 'Performance fixture must use the actual Engine')
    sanitizer_hash = sha256(a.sanitizer) if a.sanitizer else None
    matrix_hash = sha256(a.session / 'matrix.json')
    prediction = None
    if a.stage in FRESH_STAGES:
        prediction = json.loads((a.session / 'prediction.json').read_text())
        require(prediction['cases'] == recipe(a.stage) and prediction['acceptance'] == ACCEPTANCE, 'Frozen programs/gates changed')
        require(json.loads((a.session / 'matrix.json').read_text())['prediction_sha256'] == sha256(a.session / 'prediction.json'), 'Captured prediction binding differs')
        require(sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Frozen binary changed')
        if not a.regression: require(prediction['source_sha256'] == bound and prediction['renderer_sha256'] == binary, 'Prospective candidate changed')
    def one(c):
        x, provenance = original(a, c); plan = root / (c['name'] + '.tsv'); plan.write_text(schedule(c))
        out = plan.with_suffix('.wav'); dry = root / (c['name'] + '-dry.wav')
        run([a.renderer, a.session / 'silence.wav', out, plan, dry])
        rate, y = float_wav(out); drate, d = float_wav(dry)
        require(rate == drate == 48000 and x.shape == y.shape == d.shape == (FRAMES, 2) and not np.any(d), 'Extent/rate/dry changed')
        if prediction:
            require(sha256(a.session / 'predictions' / (c['name'] + '.wav')) == prediction['output_sha256'][c['name']], 'Prediction WAV changed')
            if not a.regression: require(sha256(out) == prediction['output_sha256'][c['name']], 'Rendered audio differs from sealed prediction')
        sanitized = None
        if a.sanitizer:
            san = root / (c['name'] + '-asan.wav'); sd = root / (c['name'] + '-asan-dry.wav')
            r = subprocess.run([str(a.sanitizer), str(a.session / 'silence.wav'), str(san), str(plan), str(sd)],
                capture_output=True, text=True, timeout=120,
                env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            require(r.returncode == 0 and not r.stderr, 'Sanitizer failure: ' + r.stderr)
            sanitized = sha256(san) == sha256(out) and sha256(sd) == sha256(dry)
            require(sanitized, 'Complete sanitizer WAV bytes differ')
        x, y = x[32:].astype(float), y[32:].astype(float)
        windows = [(0, len(x), 'complete')] + [(s, min(s + 48000, len(x)), 'second') for s in range(0, len(x), 48000)]
        windows += [(max(0, e['frame'] - 64), min(len(x), e['frame'] + 2048), 'event') for e in c['changes']]
        scores = [dict(start=s, stop=t, kind=k, score=screen(x[s:t], y[s:t])) for s, t, k in windows]
        passed = all(w['score']['passed'] for w in scores)
        row = provenance | dict(passed=passed, windows=scores, candidate_sha256=sha256(out), dry_sha256=sha256(dry),
            schedule_sha256=sha256(plan), sanitizer_byte_identical=sanitized, complete_sample_bit_identity=bool(np.array_equal(x, y)))
        print('PASS' if passed else 'FAIL', c['name'], flush=True)
        return row
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:
        rows = list(pool.map(one, recipe(a.stage)))
    require(bound == bindings() and binary == sha256(a.renderer), 'Source or binary changed')
    require(matrix_hash == sha256(a.session / 'matrix.json'), 'Original matrix changed')
    if a.sanitizer: require(sanitizer_hash == sha256(a.sanitizer), 'Sanitizer binary changed')
    save_json(root / 'comparison.json', dict(kind='rmx220-drum-performance-comparison', passed=all(r['passed'] for r in rows),
        stage=a.stage, cases=rows, source_sha256=bound, renderer_sha256=binary, sanitizer_sha256=sanitizer_hash, original_matrix_sha256=matrix_hash, acceptance=ACCEPTANCE,
        prediction_sha256=sha256(a.session / 'prediction.json') if prediction else None,
        prospective=prediction is not None and not a.regression,
        scope='Actual Engine, Default48k, fixed32/32; independent1%perchannel whole/second/event gates. Sealed fresh predictions are distinct from regressions.'))


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    for name in ['predict', 'capture', 'compare']:
        q = sub.add_parser(name); q.add_argument('--stage', default='discovery'); q.add_argument('--workers', type=int, default=2)
        q.add_argument('--session', type=Path, required=True)
        if name != 'predict': q.add_argument('--host', type=Path, required=True)
        if name == 'capture': q.add_argument('--plugin', type=Path, required=True)
        elif name == 'compare':
            for k in ['renderer', 'output']: q.add_argument('--' + k, type=Path, required=True)
            q.add_argument('--sanitizer', type=Path)
            q.add_argument('--regression', action='store_true')
        else: q.add_argument('--renderer', type=Path, required=True)
    a = p.parse_args(); require(1 <= a.workers <= 4, 'Invalid worker count'); globals()[a.command](a)


if __name__ == '__main__':
    main()
