#!/usr/bin/env python3
"""Validate only Spiral's outer return using separately captured pitch fixtures.

The original generator remains the source of the fixture. A passing component
comparison is not a passing Spiral effect or a full-device similarity claim.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, probe, run
from tools.rmx_filter_match import screen


BUTTONS = {'up': 'SpiralUpButton', 'down': 'SpiralDownButto'}


def capture(args):
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')

    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous control: ' + name)
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value}

    if args.stimulus == 'impulses':
        source = np.zeros((240000, 2))
        source[48000, 0], source[144000, 1] = .05, -.04
    else:
        source = probe()
        source[48000:96000] = np.random.default_rng(0xC205AF).normal(0, .032, (48000, 2))
        source[96000:144000] = source[96000:144000, ::-1]*-.91
    write_wav(root/'source.wav', 48000, source.ravel())
    cases = []
    for direction, button in BUTTONS.items():
        for bpm in args.bpm:
            for raw in sorted(set((0, *args.times))):
                name = f'{direction}-{bpm:g}-time-{raw}'
                controls = {'AutoButton': 1, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
                            'IsolatorButton': 0, 'DefaultSwitch': 1, 'UserSwitch': 0,
                            'SceneVolume': args.main/255, 'Sub1Volume': raw/255, 'Sub2Volume': 0, button: 1}
                plan = {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'reference',
                        'expected_plugin': IDENTITY, 'sample_rate': 48000, 'bpm': bpm, 'tail_seconds': 12,
                        'parameters': [setting(k, v) for k, v in controls.items()], 'events': []}
                save_json(root/(name+'.json'), plan)
                run([args.host, 'render', args.plugin, root/'source.wav', root/(name+'.json'), root/name, 128])
                cases.append({'name': name, 'receipt_sha256': sha256(root/name/'receipt.json')})
                print(name, flush=True)
    save_json(root/'matrix.json', {'kind': 'rmx220-spiral-return-captures', 'main': args.main,
                                  'cases': cases, 'capture_script_sha256': sha256(Path(__file__))})


def checked(folder):
    receipt = json.loads((folder/'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role'] != 'reference'
            or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
        raise ValueError('Wrong reference: ' + str(folder))
    for path, key in ((folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                      (Path(receipt['input_path']), 'input_sha256')):
        if sha256(path) != receipt[key]:
            raise ValueError('Modified reference: ' + str(path))
    plan = json.loads((folder/'plan.json').read_text())
    controls = {p['name']: p['value'] for p in plan['parameters']}
    if (plan['sample_rate'] != 48000 or plan.get('events') or controls['Sub2Volume'] != 0
            or controls['AutoButton'] != 1 or controls['QuantizeButton'] != 0
            or controls['InputButton'] != 1 or controls['XpadButton'] != 0
            or controls['DefaultSwitch'] != 1 or controls['UserSwitch'] != 0):
        raise ValueError('Outside static factory return recipe')
    rate, audio = float_wav(folder/'audio.wav')
    if rate != 48000:
        raise ValueError('Requires 48 kHz')
    return receipt, plan, controls, audio.astype(float)


def compare(args):
    calibration = json.loads(args.calibration.read_text())
    if (calibration.get('verified') is not True or calibration.get('eligible_for_review') is not True
            or calibration.get('sample_rate') != 48000 or calibration.get('candidate_delay_frames') != -32):
        raise ValueError('Requires independently reviewed -32-frame original-to-core bypass calibration')
    root = new_directory(args.output)
    cases = []
    for session in args.session:
        for direction in BUTTONS:
            candidates = sorted(p for p in session.iterdir() if p.is_dir()
                                and p.name.startswith(direction+'-') and (p/'receipt.json').exists()
                                and ('-time-' in p.name or p.name == direction+'-main-128'))
            for folder in candidates:
                receipt, plan, controls, audio = checked(folder)
                raw = round(controls['Sub1Volume']*255)
                if raw == 0:
                    continue
                legacy = args.legacy_initial is not None and args.legacy_initial.resolve() == session.resolve()
                baseline_name = direction+'-time-0' if legacy else f'{direction}-{plan["bpm"]:g}-time-0'
                baseline = session/baseline_name
                before, base_plan, base_controls, base_audio = checked(baseline)
                if (receipt['input_sha256'] != before['input_sha256'] or len(audio) != len(base_audio)
                        or plan['bpm'] != base_plan['bpm']
                        or any(controls[k] != base_controls[k] for k in controls if k != 'Sub1Volume')
                        or controls[BUTTONS[direction]] != 1 or controls['SceneVolume'] > 128/255+1e-7):
                    raise ValueError('Baseline differs in more than Sub1 or unsupported dry-gain range')
                name = f'{len(cases):02d}-'+folder.name
                _, source = float_wav(Path(receipt['input_path']))
                fixture = base_audio.copy()
                # Independently established 32-frame original bypass latency;
                # both compared streams keep the same original host timeline.
                count = min(len(source), max(0, len(fixture)-32))
                fixture[32:32+count] -= source[:count]
                fixture_path = root/(name+'-original-pitch-fixture.wav')
                output_path = root/(name+'-candidate-return.wav')
                write_wav(fixture_path, 48000, fixture.ravel())
                run([args.renderer, fixture_path, output_path, raw, plan['bpm']])
                _, candidate = float_wav(output_path)
                target = audio-base_audio
                result = screen(target, candidate)
                cases.append({'case': folder.name, 'direction': direction, 'bpm': plan['bpm'],
                    'main_raw': round(controls['SceneVolume']*255), 'sub1_raw': raw,
                    'reference_receipt_sha256': sha256(folder/'receipt.json'),
                    'original_fixture_receipt_sha256': sha256(baseline/'receipt.json'),
                    'original_pitch_fixture_sha256': sha256(fixture_path),
                    'candidate_return_sha256': sha256(output_path), 'measurement': result})
                print('PASS' if result['passed'] else 'FAIL', folder.name, flush=True)
    if not cases:
        raise ValueError('No return cases')
    repo = Path(__file__).resolve().parents[1]
    files = ('include/rmx/FactoryEchoReturn.h', 'include/rmx/Dsp.h', 'src/core/Wav.cpp',
             'tools/spiral_return_probe.cpp', 'tools/rmx_spiral_return.py')
    passed = all(case['measurement']['passed'] for case in cases)
    save_json(root/'comparison.json', {'kind': 'rmx220-spiral-outer-return-component-comparison',
        'passed': passed, 'sample_rate': 48000, 'reference_identity': IDENTITY,
        'renderer_sha256': sha256(args.renderer), 'source_sha256': {f: sha256(repo/f) for f in files},
        'calibration_sha256': sha256(args.calibration),
        'component_input_origin': 'Measured original pitch output; no clone pitch generator is being assessed.',
        'full_spiral_match': False, 'physical_hardware': False, 'cases': cases,
        'model': {'feedback': .75, 'return_gain': .7, 'send_gain_db': -3,
                  'divisions_beats': [.25, .5, .75, 1],
                  'crossfade_position': 'clamp((rawSub1-3)/62.25,0,4)',
                  'beat_period_ms': 'floor(60000/BPM)', 'extra_return_filter': 'none'},
        'limitations': ['Only the outer return component is tested; the inner generator remains unmatched.',
                       'Static factory settings, Sub2 zero, Main at/below raw 128, 48 kHz. No overload or gesture claim.']})
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    for name in ('host', 'plugin', 'session'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--main', type=int, choices=range(129), default=113)
    p.add_argument('--bpm', type=float, nargs='+', default=[120, 137])
    p.add_argument('--times', type=int, nargs='+', default=[17, 81, 147, 233])
    p.add_argument('--stimulus', choices=('probe', 'impulses'), default='probe')
    p = commands.add_parser('compare')
    p.add_argument('--session', type=Path, action='append', required=True)
    p.add_argument('--legacy-initial', type=Path)
    p.add_argument('--renderer', type=Path, required=True)
    p.add_argument('--calibration', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'capture':
        if any(not 40 <= bpm <= 240 for bpm in args.bpm) or any(not 0 <= raw <= 255 for raw in args.times):
            raise ValueError('Use BPM 40..240 and raw time 0..255')
        capture(args)
    else:
        raise SystemExit(compare(args))


if __name__ == '__main__':
    main()
