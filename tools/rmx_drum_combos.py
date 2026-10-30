#!/usr/bin/env python3
"""Original-reference campaigns for drum patterns, User gestures and Scene coupling."""
import argparse
import concurrent.futures
import json
import os
import subprocess
from pathlib import Path

import numpy as np

from tools import rmx_drum_performance as performance
from tools import rmx_drum_user_settings as loader
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import DRUMS, FRAMES, checked, require
from tools.rmx_drums_fx import source_hashes as core_hashes
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE

NODES = ('Kick', 'Snare', 'Clap', 'Hihat')
EFFECTS = {0: 'BpfEchoButton', 1: 'EchoButton', 3: 'SpiralUpButton', 4: 'ReverbUpButton',
           5: 'HpfEchoButton', 6: 'LpfEchoButton', 7: 'CrushEchoButton', 8: 'SpiralDownButto', 9: 'ReverbDownButto'}


def bindings():
    names = ['tools/rmx_drum_combos.py', 'tools/rmx_drum_performance.py', 'tools/drum_performance_probe.cpp', 'tools/rmx_drum_user_settings.py', 'tools/rmx_drum_performance_audit.py']
    return core_hashes() | {name: sha256(Path(name)) for name in names}


def press(events, frame, *pads):
    for pad in pads: events.extend([(frame, 'H', pad), (frame + 32, 'R', pad)])


def profile(gain, decay, envelope):
    return dict(GainCb=gain, DecayCb=decay, EnvelopeCb=envelope)


def make_case(family, index, changes, **values):
    c = dict(name=f'combo-{family}-{index:02d}', family=family, variant=str(index), drum='kick', block=128,
        level=128, pitch=128, position=153, bpm=120, automatic=0, quantize=0, hold=0, overdub=0,
        user=0, settings={}, effect=1, route=1, main=0, amount=0, cutoff=0, enabled=0)
    c.update(values); c['changes'] = [dict(frame=f, type=k, value=v) for f, k, v in sorted(changes, key=lambda e: e[0])]
    c['hits'] = [e['frame'] for e in c['changes'] if e['type'] == 'H']
    return c


def recipe(stage):
    base = stage.split('-fresh')[0]; fresh = '-fresh' in stage
    require(base in ['multi', 'user-roll', 'user-overdub', 'fx'], 'Unknown combined stage')
    rows = []
    if base == 'multi':
        for i in range(18):
            variant = i % 9; changes = [(31, 'O', 1)]
            if variant == 0:
                press(changes, 48079, 0, 1, 2, 3); press(changes, 77113, 1, 3); press(changes, 128193, 0, 2)
            elif variant == 8:
                for slot in range(128): press(changes, 48079 + slot * 750, 0, 1, 2, 3)
            else:
                for at, pads in [(48079, (0, 3)), (60091, (3,)), (77113, (1, 3)), (96113, (3,)), (128193, (0, 2))]:
                    press(changes, at, *pads)
                if variant == 2:
                    for at, pads in [(144091, (0, 3)), (173135, (1, 3)), (224207, (0, 2))]: press(changes, at, *pads)
                if variant in [3, 4, 5, 6, 7]:
                    button = 'M' if variant in [3, 6, 7] else 'D'
                    changes += [(240313, button, 1), (240469, button, 0)]
                    press(changes, 240337, 0); press(changes, 240389, 3)
                    if variant in [3, 6]:
                        changes += [(336491, 'M', 1), (336687, 'M', 0)]
                        press(changes, 336523, 0); press(changes, 336579, 3)
                    if variant in [4, 5]: press(changes, 288419, 0, 3)
            changes += [(432701, 'O', 0)]
            rows.append(make_case(base, i, changes, quantize=int(i >= 9), block=[8, 31, 127, 509, 1021, 4093][i % 6]))
    elif base in ['user-roll', 'user-overdub']:
        profiles = [(0, 0, 0), (6, 2, 1), (3, 1, 1), (1, 2, 0), (5, 0, 1), (2, 1, 0)]
        for pad, node in enumerate(NODES):
            for i, values in enumerate(profiles):
                settings = {node: profile(*values)}
                if i == 5: settings = {n: profile((j * 2 + 1) % 7, j % 3, j % 2) for j, n in enumerate(NODES)}
                if base == 'user-roll':
                    position = [51, 102, 153, 204, 255, 153][i]
                    changes = [(1, 'X', position)]; press(changes, 48079 + pad * 6, pad)
                    changes += [(96113, 'T', 1), (168191, 'T', 0), (192241, 'X', position), (192273, 'T', 1), (312437, 'T', 0)]
                    if i >= 3: changes += [(120157, 'F', 1), (288373, 'F', 0)]
                    if i == 5: press(changes, 240337, (pad + 1) % 4)
                    rows.append(make_case(base, pad * 6 + i, changes, user=1, settings=settings, drum=list(DRUMS)[pad],
                        position=position, quantize=i % 2, block=[8, 31, 127, 509, 1021, 4093][i], pitch=[39, 117, 128, 139, 191, 239][i]))
                else:
                    changes = [(31, 'O', 1)]
                    for frame in [48079, 77113, 128193]: press(changes, frame + pad * 6, pad)
                    if i in [2, 3, 4, 5]:
                        button = 'M' if i in [2, 5] else 'D'
                        changes += [(240313, button, 1), (240401, button, 0)]; press(changes, 240337, pad)
                        if i in [2, 5]:
                            changes += [(336491, 'M', 1), (336587, 'M', 0)]; press(changes, 336523, pad)
                        if i == 4: press(changes, 288419, pad)
                    if i == 5:
                        for frame in [60091, 96113, 144239]: press(changes, frame, (pad + 1) % 4)
                    changes += [(432701, 'O', 0)]
                    rows.append(make_case(base, pad * 6 + i, changes, user=1, settings=settings, drum=list(DRUMS)[pad],
                        quantize=i % 2, block=[8, 31, 127, 509, 1021, 4093][i], pitch=[39, 117, 128, 139, 191, 239][i]))
    else:
        for user in [0, 1]:
            for index, effect in enumerate(EFFECTS):
                settings = {n: profile((j * 2) % 7, j % 3, (j + index) % 2) for j, n in enumerate(NODES)} if user else {}
                changes = []
                for frame, pads in [(48079, (0, 3)), (77113, (1,)), (96113, (3,)), (128193, (2,)), (144217, (0,)),
                                     (192241, (0, 1, 2, 3)), (240337, (1, 3)), (288371, (0, 2))]: press(changes, frame, *pads)
                for enabled in [0, 1]:
                    rows.append(make_case(base, user * 18 + index * 2 + enabled, changes, user=user, settings=settings, effect=effect,
                        enabled=enabled, main=[95, 151, 73, 155, 95, 123, 83, 95, 93][index], amount=97,
                        cutoff=0 if effect in [0, 5, 6, 7] else 131, block=[31, 127, 509, 4093][index % 4],
                        level=107 if user else 128, pitch=117 if user else 128))
    if fresh:
        seed = {'multi': 0x434D5031, 'user-roll': 0x43555231, 'user-overdub': 0x43554F31, 'fx': 0x43465831}[base]
        rng = np.random.default_rng(seed + int(stage.endswith('fresh2')))
        for index, c in enumerate(rows):
            c['name'] = c['name'].replace('combo-', 'combo-fresh2-' if stage.endswith('fresh2') else 'combo-fresh-')
            shift = int(rng.integers(17, 1700)); c['block'] = [11, 43, 131, 257, 1021, 4096][index % 6]
            c['level'] = [17, 107, 173, 239][index % 4]; c['pitch'] = int(rng.choice([3, 117, 121, 128, 135, 139, 191, 255]))
            for e in c['changes']:
                if e['frame'] != 1: e['frame'] += shift
            if c['user']:
                c['settings'] = {n: profile(int(rng.integers(7)), int(rng.integers(3)), int(rng.integers(2))) for n in NODES}
            c['hits'] = [e['frame'] for e in c['changes'] if e['type'] == 'H']
        # Combine source performance with every effect; keep its dry partner
        # identical so wet subtraction never fits or changes source timing.
        if base == 'fx':
            for c in rows:
                controls = [(1, 'X', 153)]
                if (c['effect'] + c['user']) % 2:
                    controls += [(96113, 'T', 1), (144239, 'F', 1), (168191, 'T', 0), (192241, 'X', 204), (288373, 'F', 0)]
                else:
                    controls += [(31, 'O', 1), (432701, 'O', 0)]
                c['changes'] = sorted(c['changes'] + [dict(frame=f, type=k, value=v) for f, k, v in controls], key=lambda e: e['frame'])
        # FX pairs must have identical source/control programs for dry subtraction.
        if base == 'fx':
            for i in range(0, len(rows), 2):
                active = rows[i + 1]; dry = rows[i]
                for key in ['changes', 'hits', 'block', 'level', 'pitch', 'settings']: active[key] = dry[key]
    return rows


def original_plan(c, inventory, session):
    simple = c | dict(changes=[e for e in c['changes'] if e['type'] not in 'EVBC'])
    plan = performance.original_plan(simple, inventory)
    values = dict(DefaultSwitch=1 - c['user'], UserSwitch=c['user'], InputButton=int(c['route'] in [0, 2]), XpadButton=int(c['route'] in [1, 2]),
        SceneVolume=c['main'] / 255, Sub1Volume=c['amount'] / 255, Sub2Volume=c['cutoff'] / 255)
    values[EFFECTS[c['effect']]] = c['enabled']
    plan['parameters'] = [p | dict(value=values.get(p['name'], p['value'])) for p in plan['parameters']]
    if c['family'] == 'fx':
        present = {p['name'] for p in plan['parameters']}
        for name, value in values.items():
            if name not in present:
                p = next(p for p in inventory['parameters'] if p['name'] == name)
                plan['parameters'].append({k: p[k] for k in ['name', 'id', 'index']} | dict(value=value))
    controls = dict(E=EFFECTS[c['effect']], V='SceneVolume', B='Sub1Volume', C='Sub2Volume')
    for e in c['changes']:
        if e['type'] not in controls: continue
        p = next(p for p in inventory['parameters'] if p['name'] == controls[e['type']])
        plan['events'].append({k: p[k] for k in ['name', 'id', 'index']} | dict(frame=e['frame'], type='parameter', value=e['value'] if e['type'] == 'E' else e['value'] / 255))
    plan['events'].sort(key=lambda e: e['frame'])
    if c['user']: plan['initial_state'] = dict(path=c['name'] + '.bin', sha256=sha256(session / (c['name'] + '.bin')))
    return plan


def schedule(c):
    lines = performance.schedule(c).splitlines(); lines[0] = 'RMX_DRUM_PERFORMANCE 2'
    controls = ' '.join(str(c[k]) for k in ['user', 'effect', 'route', 'main', 'amount', 'cutoff', 'enabled'])
    profiles = ' '.join(str(c['settings'].get(node, {}).get(field, default)) for node in NODES for field, default in [('GainCb', 3), ('DecayCb', 1), ('EnvelopeCb', 0)])
    return '\n'.join(lines[:2] + [controls, profiles] + lines[2:]) + '\n'


def original(a, c):
    if c['user']:
        state = a.session / (c['name'] + '.bin'); rsd = a.session / (c['name'] + '.RSD')
        require(sha256(state) == c['requested_state_sha256'] and c['customization_retained'], 'User state binding differs')
        require(rsd.read_text() == loader.xml(c['settings']), 'User XML changed')
        require(loader.chunks(state.read_bytes())[b'cstm'] == loader.chunks((a.session / c['name'] / 'state-before.bin').read_bytes())[b'cstm'], 'Original lost customization')
    x, provenance = checked(a.session, c, plan_builder=lambda c, inv: original_plan(c, inv, a.session))
    receipt = json.loads((a.session / c['name'] / 'receipt.json').read_text())
    require(receipt['host_sha256'] == sha256(a.host), 'Original host changed')
    for member in receipt['plugin']['binary_files']:
        require(sha256(Path(receipt['plugin']['bundle']) / member['path']) == member['sha256'], 'Original binary changed')
    return x, provenance


def predict(a):
    require('-fresh' in a.stage, 'Predictions require a fresh recipe')
    bound = bindings(); binary = sha256(a.renderer); root = new_directory(a.session); (root / 'predictions').mkdir()
    write_wav(root / 'silence.wav', 48000, np.zeros(FRAMES * 2)); outputs = {}
    for c in recipe(a.stage):
        path = root / 'predictions' / (c['name'] + '.tsv'); path.write_text(schedule(c)); out = path.with_suffix('.wav')
        run([a.renderer, root / 'silence.wav', out, path, out.with_name(out.stem + '-dry.wav')]); outputs[c['name']] = sha256(out)
    require(bound == bindings() and binary == sha256(a.renderer), 'Prediction inputs changed')
    save_json(root / 'prediction.json', dict(kind='rmx220-drum-combo-sealed-prediction', stage=a.stage, cases=recipe(a.stage), source_sha256=bound,
        renderer=str(a.renderer.resolve()), renderer_sha256=binary, input_sha256=sha256(root / 'silence.wav'), output_sha256=outputs, acceptance=ACCEPTANCE))


def capture(a):
    bound = bindings(); fresh = '-fresh' in a.stage; root = a.session; prediction = None
    if fresh:
        prediction = json.loads((root / 'prediction.json').read_text()); require(prediction['source_sha256'] == bound and prediction['cases'] == recipe(a.stage), 'Frozen candidate changed')
        require(sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Frozen renderer changed')
        for name, digest in prediction['output_sha256'].items(): require(sha256(root / 'predictions' / (name + '.wav')) == digest, 'Frozen WAV changed')
    else:
        new_directory(root); write_wav(root / 'silence.wav', 48000, np.zeros(FRAMES * 2))
    inventory = json.loads(run([a.host, 'inventory', a.plugin])); require(all(inventory[k] == v for k, v in IDENTITY.items()), 'Wrong Original')
    save_json(root / 'inventory.json', inventory); template = a.template.read_bytes(); template_hash = sha256(a.template); loader.chunks(template)
    def one(c):
        metadata = {}
        if c['user']:
            rsd = root / (c['name'] + '.RSD'); rsd.write_text(loader.xml(c['settings']))
            state = root / (c['name'] + '.bin'); state.write_bytes(loader.state(template, c['settings'], str(rsd.resolve()), str(root.resolve()) + '/'))
            metadata['requested_state_sha256'] = sha256(state)
        plan = root / (c['name'] + '.json'); save_json(plan, original_plan(c, inventory, root))
        run([a.host, 'render', a.plugin, root / 'silence.wav', plan, root / c['name'], c['block']])
        if c['user']:
            require(loader.chunks((root / c['name'] / 'state-before.bin').read_bytes())[b'cstm'] == loader.chunks(state.read_bytes())[b'cstm'], 'Original customization not retained')
            metadata['customization_retained'] = True
        print('CAPTURED', c['name'], flush=True)
        return c | metadata | dict(receipt_sha256=sha256(root / c['name'] / 'receipt.json'))
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool: rows = list(pool.map(one, recipe(a.stage)))
    require(bound == bindings() and template_hash == sha256(a.template), 'Capture inputs changed')
    save_json(root / 'matrix.json', dict(kind='rmx220-drum-combo-captures', stage=a.stage, cases=rows, source_sha256=bound,
        template_sha256=template_hash, prediction_sha256=sha256(root / 'prediction.json') if fresh else None))


def compare(a):
    bound = bindings(); binary = sha256(a.renderer); matrix_path = a.session / 'matrix.json'; matrix_hash = sha256(matrix_path)
    matrix = json.loads(matrix_path.read_text()); expected = recipe(a.stage); cases = [{k: v for k, v in c.items() if k != 'receipt_sha256'} for c in matrix['cases']]
    require(len(cases) == len(expected) and all(all(c[k] == v for k, v in e.items()) for c, e in zip(cases, expected, strict=True)), 'Original recipe changed')
    require('rmx::Engine::process(' in subprocess.check_output(['nm', '-C', str(a.renderer)], text=True), 'Fixture lacks actual Engine')
    sanitizer_hash = sha256(a.sanitizer) if a.sanitizer else None; prediction = None
    if '-fresh' in a.stage:
        prediction = json.loads((a.session / 'prediction.json').read_text()); require(prediction['cases'] == expected and prediction['acceptance'] == ACCEPTANCE, 'Prediction programs/gates changed')
        require(matrix['prediction_sha256'] == sha256(a.session / 'prediction.json') and sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Prediction binding changed')
        if not a.regression: require(prediction['source_sha256'] == bound and prediction['renderer_sha256'] == binary, 'Prospective candidate changed')
    root = new_directory(a.output)
    def one(c):
        x, provenance = original(a, c); path = root / (c['name'] + '.tsv'); path.write_text(schedule(c)); out = path.with_suffix('.wav'); dry = path.with_name(path.stem + '-dry.wav')
        run([a.renderer, a.session / 'silence.wav', out, path, dry]); rate, y = float_wav(out); dry_rate, d = float_wav(dry)
        require(rate == dry_rate == 48000 and x.shape == y.shape == d.shape == (FRAMES, 2) and not np.any(d), 'Candidate extent/rate/dry changed')
        if prediction:
            require(sha256(a.session / 'predictions' / (c['name'] + '.wav')) == prediction['output_sha256'][c['name']], 'Prediction WAV changed')
            if not a.regression: require(sha256(out) == prediction['output_sha256'][c['name']], 'Audio differs from sealed prediction')
        sanitized = None
        if a.sanitizer:
            san = root / (c['name'] + '-asan.wav'); sd = root / (c['name'] + '-asan-dry.wav')
            result = subprocess.run([str(a.sanitizer), str(a.session / 'silence.wav'), str(san), str(path), str(sd)], capture_output=True, text=True,
                env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), timeout=120)
            require(result.returncode == 0 and not result.stderr, 'Sanitizer failure: ' + result.stderr)
            sanitized = sha256(san) == sha256(out) and sha256(sd) == sha256(dry); require(sanitized, 'Sanitizer WAV differs')
        x, y = x[32:].astype(float), y[32:].astype(float)
        windows = [(0, len(x), 'complete')] + [(s, min(s + 48000, len(x)), 'second') for s in range(0, len(x), 48000)]
        windows += [(max(0, e['frame'] - 64), min(len(x), e['frame'] + 2048), 'event') for e in c['changes']]
        scores = [dict(start=s, stop=t, kind=k, score=screen(x[s:t], y[s:t])) for s, t, k in windows]
        passed = all(w['score']['passed'] for w in scores)
        print('PASS' if passed else 'FAIL', c['name'], flush=True)
        return provenance | dict(passed=passed, windows=scores, candidate_sha256=sha256(out), dry_sha256=sha256(dry),
            schedule_sha256=sha256(path), sanitizer_byte_identical=sanitized, complete_sample_bit_identity=bool(np.array_equal(x, y)))
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool: rows = list(pool.map(one, cases))
    if a.stage.startswith('fx'):
        for index in range(0, len(cases), 2):
            baseline, active = rows[index:index + 2]; reference_dry, _ = original(a, cases[index]); reference, _ = original(a, cases[index + 1])
            _, native_dry = float_wav(root / (baseline['case'] + '.wav')); _, candidate = float_wav(root / (active['case'] + '.wav'))
            reference_wet = reference[32:].astype(float) - reference_dry[32:]
            candidate_wet = candidate[32:].astype(float) - native_dry[32:]
            wet_windows = [dict(start=w['start'], stop=w['stop'], kind=w['kind'], score=screen(reference_wet[w['start']:w['stop']], candidate_wet[w['start']:w['stop']])) for w in active['windows']]
            active['wet'] = wet_windows[0]['score']; active['wet_windows'] = wet_windows
            active['baseline'] = baseline['case']; active['passed'] &= all(w['score']['passed'] for w in wet_windows)
    require(bound == bindings() and binary == sha256(a.renderer) and matrix_hash == sha256(matrix_path), 'Comparison inputs changed')
    if a.sanitizer: require(sanitizer_hash == sha256(a.sanitizer), 'Sanitizer changed')
    save_json(root / 'comparison.json', dict(kind='rmx220-drum-combo-comparison', passed=all(r['passed'] for r in rows), stage=a.stage,
        cases=rows, source_sha256=bound, renderer_sha256=binary, sanitizer_sha256=sanitizer_hash, matrix_sha256=matrix_hash,
        prospective=prediction is not None and not a.regression, prediction_sha256=sha256(a.session / 'prediction.json') if prediction else None,
        acceptance=ACCEPTANCE, scope='Actual Engine, stereo48k, static User drum profiles/default pitch ranges and declared pattern/gesture/Scene controls. '
        'Fixed32/32, whole/second/event1%perchannel; FX wet in every window also checked against matched dry programs. No fitted gain/alignment or whole-device/hardware claim.'))


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    for command in ['predict', 'capture', 'compare']:
        q = sub.add_parser(command); q.add_argument('--stage', required=True); q.add_argument('--session', type=Path, required=True); q.add_argument('--workers', type=int, default=2)
        if command != 'predict': q.add_argument('--host', type=Path, required=True)
        if command == 'capture':
            q.add_argument('--plugin', type=Path, required=True); q.add_argument('--template', type=Path, required=True)
        else: q.add_argument('--renderer', type=Path, required=True)
        if command == 'compare':
            q.add_argument('--output', type=Path, required=True); q.add_argument('--sanitizer', type=Path); q.add_argument('--regression', action='store_true')
    a = p.parse_args(); require(1 <= a.workers <= 4, 'Invalid workers'); globals()[a.command](a)


if __name__ == '__main__': main()
