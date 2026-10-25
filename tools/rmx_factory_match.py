#!/usr/bin/env python3
"""Capture and check static RMX-1000 2.2.0 factory effects at 48 kHz.

Requires a separately obtained original plug-in; no vendor audio or binary is
distributed. Static controls only. Hardware, User profiles, gestures and other
sample rates are outside this measurement's scope.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess

import numpy as np

from tools.fidelity import calibrate, compare, stereo
from tools.reference_audio import read_wav, save_json, sha256, write_wav


IDENTITY = {'name': 'RMX-1000 Plug-in', 'manufacturer': 'Pioneer Corporation', 'version': '2.2.0'}
RATE = 48000


def run(args):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def new_directory(path):
    path.mkdir(parents=True, exist_ok=False)
    return path.resolve()


def read(path):
    return json.loads(path.read_text())


def probe():
    """New deterministic broadband, sweep, transient and multitone holdout."""
    rng = np.random.default_rng(0xAFA1000)
    x = np.zeros((RATE * 6, 2))
    t = np.arange(RATE) / RATE
    x[RATE:RATE * 2] = rng.normal(0, .035, (RATE, 2))
    # Different sweep direction and frequency content in each channel.
    phase = 2 * np.pi * 25 * (np.exp(t * np.log(720)) - 1) / np.log(720)
    x[RATE * 2:RATE * 3] = .07 * np.column_stack((np.sin(phase), np.sin(phase[::-1])))
    for n in range(4):
        start = RATE * 3 + n * RATE // 4
        u = np.arange(RATE // 4) / RATE
        x[start:start + len(u), 0] = .14 * np.sin(2 * np.pi * 67 * u) * np.exp(-u * 23)
        x[start:start + len(u), 1] = rng.normal(0, .04, len(u)) * np.exp(-u * 40)
    x[RATE * 4:RATE * 5, 0] = sum(.025 * np.sin(2 * np.pi * f * t) for f in (41, 311, 1703, 8111))
    x[RATE * 4:RATE * 5, 1] = sum(.025 * np.cos(2 * np.pi * f * t) for f in (79, 613, 3511, 13001))
    return x


def capture(args):
    if not 40 <= args.bpm <= 240:
        raise ValueError('BPM must be finite and within 40..240')
    root = new_directory(args.output)
    host, plugin = args.host.resolve(), args.plugin.resolve()
    inventory = json.loads(run([host, 'inventory', plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('This recipe requires the original RMX-1000 Plug-in 2.2.0')
    save_json(root / 'inventory.json', inventory)

    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous reference control: ' + name)
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value}

    write_wav(root / 'probe.wav', RATE, probe().ravel())
    cases = [{'name': 'bypass', 'enabled': False, 'raw': [17, 211, 96]},
             {'name': 'centre', 'enabled': True, 'raw': [128] * 3}]
    for b, band in enumerate(('low', 'mid', 'high')):
        for raw in (0, 32, 96, 123, 124, 131, 132, 192, 254, 255):
            knobs = [128] * 3
            knobs[b] = raw
            cases.append({'name': f'{band}-{raw}', 'enabled': True, 'raw': knobs})
    for n, knobs in enumerate(([17, 211, 96], [254, 67, 173], [49, 149, 237])):
        cases.append({'name': f'mixed-{n}', 'enabled': True, 'raw': knobs})
    if args.effect == 'echo':
        cases = [{'name': 'bypass', 'enabled': False, 'raw': [192, 128, 0]}]
        for raw in (0, 4, 47, 113, 191, 192, 255):
            cases.append({'name': f'main-{raw}', 'enabled': True, 'raw': [raw, 128, 0]})
        for raw in (22, 65, 66, 101, 131, 132, 153, 193, 194, 231):
            cases.append({'name': f'time-{raw}', 'enabled': True, 'raw': [192, raw, 0]})
        for raw in (17, 81, 147, 233):
            cases.append({'name': f'filter-{raw}', 'enabled': True, 'raw': [192, 128, raw]})
        for n, knobs in enumerate(([47, 22, 81], [113, 153, 233], [192, 231, 147])):
            cases.append({'name': f'mixed-{n}', 'enabled': True, 'raw': knobs})
    common = {'AutoButton': int(args.bpm != 120), 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
              'CutAddButton': 0, 'TransRollButton': 0, 'GateDriveButton': 0,
              'DefaultSwitch': 1, 'UserSwitch': 0}
    manifest = {'kind': 'rmx220-factory-capture-matrix', 'effect': args.effect, 'sample_rate': RATE, 'bpm': args.bpm,
                'identity': IDENTITY, 'physical_hardware': False,
                'probe_sha256': sha256(root / 'probe.wav'), 'cases': cases}
    for case in cases:
        settings = common | {'IsolatorButton': int(case['enabled'])}
        settings |= {name: raw / 255 for name, raw in zip(
            ('IsoLowVolume', 'IsoMidVolume', 'IsoHiVolume'), case['raw'])}
        if args.effect == 'echo':
            settings = common | {'IsolatorButton': 0, 'EchoButton': int(case['enabled'])}
            settings |= {name: raw / 255 for name, raw in zip(
                ('SceneVolume', 'Sub1Volume', 'Sub2Volume'), case['raw'])}
        plan = {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'reference',
                'expected_plugin': IDENTITY, 'sample_rate': RATE, 'bpm': args.bpm,
                'tail_seconds': max(12, math.ceil(25*60/args.bpm)) if args.effect == 'echo' else 1,
                'parameters': [setting(k, v) for k, v in settings.items()], 'events': []}
        plan_path = root / (case['name'] + '.json')
        save_json(plan_path, plan)
        run([host, 'render', plugin, root / 'probe.wav', plan_path, root / case['name'], args.block])
        case['receipt_sha256'] = sha256(root / case['name'] / 'receipt.json')
        print('Captured', case['name'], flush=True)
    save_json(root / 'matrix.json', manifest)


def checked_session(root):
    matrix = read(root / 'matrix.json')
    if matrix['kind'] not in ('rmx220-isolator-capture-matrix', 'rmx220-factory-capture-matrix') or matrix['sample_rate'] != RATE:
        raise ValueError('Wrong capture matrix')
    matrix.setdefault('effect', 'isolator')
    if matrix['effect'] not in ('isolator', 'echo'):
        raise ValueError('Unknown effect')
    if sha256(root / 'probe.wav') != matrix['probe_sha256']:
        raise ValueError('Probe changed after capture')
    for case in matrix['cases']:
        folder = root / case['name']
        receipt = read(folder / 'receipt.json')
        if sha256(folder / 'receipt.json') != case['receipt_sha256'] or not receipt['complete']:
            raise ValueError('Incomplete or modified reference receipt')
        if receipt['role'] != 'reference' or any(receipt['plugin'][k] != v for k, v in IDENTITY.items()):
            raise ValueError('Reference identity/role differs')
        for filename, key in (('audio.wav', 'output_sha256'), ('plan.json', 'plan_sha256')):
            if sha256(folder / filename) != receipt[key]:
                raise ValueError('Reference file changed: ' + str(folder / filename))
        if receipt['input_sha256'] != matrix['probe_sha256']:
            raise ValueError('Reference used another input')
    return matrix


def render(args):
    root, destination = args.session.resolve(), new_directory(args.output)
    matrix = checked_session(root)
    renderer = args.renderer.resolve()
    manifest = {'kind': 'rmx-factory-candidate-renders', 'renderer_sha256': sha256(renderer),
                'matrix_sha256': sha256(root / 'matrix.json'), 'cases': []}
    repo = Path(__file__).resolve().parents[1]
    sources = [repo / 'CMakeLists.txt', *sorted((repo / 'include/rmx').glob('*.h')),
               *sorted((repo / 'src/core').glob('*.cpp')), repo / 'tools/render.cpp', Path(__file__).resolve()]
    manifest['source_sha256'] = {str(path.relative_to(repo)): sha256(path) for path in sources}
    for case in matrix['cases']:
        settings = {'input_gain': 0, 'output_gain': 0, 'bypass': 0, 'auto_tempo': 0,
                    'quantize': 0, 'tempo': matrix.get('bpm', 120), 'scene_on': 0, 'sampler_mute': 1, 'sample_source': 0,
                    'isolate_mode': 0, 'isolate_source': 0, 'isolate_on': int(case['enabled'])}
        settings |= {key: raw / 127.5 - 1 for key, raw in zip(('low', 'mid', 'high'), case['raw'])}
        if matrix['effect'] == 'echo':
            settings |= {'low': 0, 'mid': 0, 'high': 0, 'isolate_on': 0,
                         'scene_on': int(case['enabled']), 'scene_type': 1, 'scene_source': 0,
                         'scene_depth': case['raw'][0] / 255, 'scene_time': case['raw'][1] * 7 / 255,
                         'scene_resonance': case['raw'][2] / 255}
        preset = destination / (case['name'] + '.rmx')
        preset.write_text('RMX_STATE 1\n' + ''.join(f'param {k} {v:.9g}\n' for k, v in settings.items()))
        output = destination / (case['name'] + '.wav')
        tail = read(root / case['name'] / 'plan.json')['tail_seconds']
        run([renderer, root / 'probe.wav', output, preset, tail])
        manifest['cases'].append({'name': case['name'], 'output_sha256': sha256(output),
                                  'preset_sha256': sha256(preset)})
    save_json(destination / 'renders.json', manifest)
    calibration = calibrate(stereo(read_wav(root / 'bypass/audio.wav')[1]),
                            stereo(read_wav(destination / 'bypass.wav')[1]), RATE)
    calibration['reference_sha256'] = sha256(root / 'bypass/audio.wav')
    calibration['candidate_sha256'] = sha256(destination / 'bypass.wav')
    save_json(destination / 'calibration-unreviewed.json', calibration)
    print('Rendered', len(matrix['cases']), 'cases. Review the bypass calibration before comparing.')


def measure(args):
    root, candidate = args.session.resolve(), args.candidate.resolve()
    matrix = checked_session(root)
    renders, calibration = read(candidate / 'renders.json'), read(args.calibration)
    if renders['matrix_sha256'] != sha256(root / 'matrix.json'):
        raise ValueError('Candidate belongs to another matrix')
    for path, key in ((root / 'bypass/audio.wav', 'reference_sha256'),
                      (candidate / 'bypass.wav', 'candidate_sha256')):
        if calibration.get(key) != sha256(path):
            raise ValueError('Calibration belongs to another bypass pair')
    results = []
    bypass_reference = stereo(read_wav(root / 'bypass/audio.wav')[1])
    bypass_candidate = stereo(read_wav(candidate / 'bypass.wav')[1])
    for case, rendered in zip(matrix['cases'], renders['cases'], strict=True):
        path = candidate / (case['name'] + '.wav')
        if case['name'] != rendered['name'] or sha256(path) != rendered['output_sha256']:
            raise ValueError('Candidate render changed')
        if sha256(candidate / (case['name'] + '.rmx')) != rendered['preset_sha256']:
            raise ValueError('Candidate preset changed')
        reference_audio, candidate_audio = stereo(read_wav(root / case['name'] / 'audio.wav')[1]), stereo(read_wav(path)[1])
        result = compare(reference_audio, candidate_audio, RATE, calibration)
        item = {'case': case['name'], 'measurement': result}
        if matrix['effect'] == 'echo' and case['enabled'] and case['raw'][0] > 3:
            # Isolate the additive return using independently captured dry
            # paths. Preserve both routes' original timing and relative level.
            item['isolated_return_measurement'] = compare(reference_audio - bypass_reference,
                candidate_audio - bypass_candidate, RATE, calibration)
        results.append(item)
    report = {'kind': 'rmx220-static-factory-comparison', 'effect': matrix['effect'], 'sample_rate': RATE, 'bpm': matrix.get('bpm', 120),
              'matrix_sha256': sha256(root / 'matrix.json'), 'renders_sha256': sha256(candidate / 'renders.json'),
              'calibration_sha256': sha256(args.calibration), 'cases': results,
              'scope': 'Static factory settings, software reference, 48 kHz only; no general similarity percentage.'}
    save_json(args.report, report)
    passed = all(item['measurement']['waveform_verdict'] == 'pass' and
                 item.get('isolated_return_measurement', item['measurement'])['waveform_verdict'] == 'pass'
                 for item in results)
    print('PASS' if passed else 'FAIL', len(results), matrix['effect'], 'cases')
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    p.add_argument('--host', type=Path, required=True)
    p.add_argument('--plugin', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--effect', choices=('isolator', 'echo'), default='isolator')
    p.add_argument('--bpm', type=float, default=120)
    p.add_argument('--block', type=int, choices=(32, 64, 128, 256), default=128)
    p = commands.add_parser('render')
    p.add_argument('--session', type=Path, required=True)
    p.add_argument('--renderer', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('compare')
    p.add_argument('--session', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--calibration', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        return {'capture': capture, 'render': render, 'compare': measure}[args.command](args) or 0
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
