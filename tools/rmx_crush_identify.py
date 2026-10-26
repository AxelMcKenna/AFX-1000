#!/usr/bin/env python3
"""Capture and identify the factory Crush sample-hold/filter path at 48 kHz.

No reference recordings or manufacturer DSP code are distributed. Static
settled controls only; first-host-block startup is a separate diagnostic.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, probe, run
from tools.rmx_filter_capture import TIMES
from tools.rmx_filter_identify import response_error, topology


CALIBRATION = (0, 1, 3, 4, 8, 16, 24, 32, 48, 64, 80, 96, 112, 128,
               144, 160, 176, 192, 208, 224, 240, 255)
HOLDOUT = (17, 81, 147, 233)


def capture(args):
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')

    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Missing/ambiguous control: ' + name)
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value}

    step = np.zeros((144000, 2))
    step[48000:120000] = [.125, -.09]
    white = np.random.default_rng(0xC205AC).normal(0, .035, (96000, 2))
    holdout = probe()
    holdout[48000:96000] = np.random.default_rng(0xC205AF).normal(0, .032, (48000, 2))
    holdout[96000:144000] = holdout[96000:144000, ::-1]*-.91
    impulses = np.zeros((240000, 2))
    impulses[48000, 0], impulses[144000, 1] = .05, -.04
    clock_white = np.zeros((336000, 2))
    clock_white[48000:288000] = np.random.default_rng(0xC205AC77).normal(0, .03, (240000, 2))
    for name, x in (('steps', step), ('white', white), ('probe', holdout), ('impulses', impulses), ('clock-white', clock_white)):
        write_wav(root/(name+'.wav'), 48000, x.ravel())
    cases = []

    def add(name, input_name, main, time=128, bpm=120, block=128, off=False, diagnostic=False):
        cases.append({'name': name, 'input': input_name+'.wav', 'main': main, 'time': time,
                      'bpm': bpm, 'block': block, 'off': off, 'diagnostic': diagnostic})

    for raw in (*CALIBRATION, *HOLDOUT):
        add(f'crush-step-main-{raw}', 'steps', raw)
    for raw in (17, 32, 64, 96, 128, 160, 192, 224, 255):
        add(f'diagnostic-white-main-{raw}', 'white', raw, 0, diagnostic=True)
    for block in (32, 256):
        add(f'diagnostic-white-main-128-block-{block}', 'white', 128, 0, block=block, diagnostic=True)
    for raw, frame in ((113, 157445), (177, 140949), (213, 199821), (253, 291869)):
        add(f'diagnostic-long-main-{raw}', 'clock-white', raw, 0, diagnostic=True)
        name = f'crush-clock-late-{raw}'
        impulse = np.zeros((frame+24000, 2))
        impulse[frame] = [.05, -.04]
        write_wav(root/(name+'.wav'), 48000, impulse.ravel())
        add(name, name, raw, 0)
    for raw in (4, 8, 17, 47, 81, 113, 147, 177, 213, 233, 249, 253, 255):
        add(f'crush-probe-main-{raw}', 'probe', raw)
    for raw in TIMES:
        add(f'crush-time-{raw}', 'impulses', 32, raw)
    for bpm in (90, 128, 137):
        for raw in (16, 96, 176, 255):
            add(f'crush-{bpm}-time-{raw}', 'probe', 233, raw, bpm)
    add('crush-off', 'impulses', 32, off=True)
    for i, case in enumerate(cases):
        controls = {'AutoButton': 1, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
                    'IsolatorButton': 0, 'DefaultSwitch': 1, 'UserSwitch': 0,
                    'Sub1Volume': case['time']/255, 'Sub2Volume': 0,
                    'SceneVolume': case['main']/255, 'CrushEchoButton': 1}
        tail = 2 if case['input'] in ('steps.wav', 'white.wav') else 16 if case['bpm'] == 90 else 12
        plan = {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'reference',
                'expected_plugin': IDENTITY, 'sample_rate': 48000, 'bpm': case['bpm'],
                'tail_seconds': tail, 'parameters': [setting(k, v) for k, v in controls.items()], 'events': []}
        if case['off']:
            plan['events'] = [setting('CrushEchoButton', 0) | {'type': 'parameter', 'frame': 52800}]
        save_json(root/(case['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/case['input'], root/(case['name']+'.json'),
             root/case['name'], case['block']])
        case['receipt_sha256'] = sha256(root/case['name']/'receipt.json')
        print(i+1, '/', len(cases), case['name'], flush=True)
    save_json(root/'matrix.json', {'kind': 'rmx220-crush-capture-matrix', 'cases': cases,
                                  'capture_script_sha256': sha256(Path(__file__))})


def checked(folder):
    receipt = json.loads((folder/'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role'] != 'reference'
            or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
        raise ValueError('Incorrect reference: ' + str(folder))
    for file, key in ((folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                      (Path(receipt['input_path']), 'input_sha256')):
        if sha256(file) != receipt[key]:
            raise ValueError('Modified capture: ' + str(file))
    rate, audio = float_wav(folder/'audio.wav')
    if rate != 48000:
        raise ValueError('Requires 48 kHz captures')
    return receipt, audio


def hold_events(raw, count):
    counter = 0.
    normalized = np.float32(np.float32(raw)*np.float32(1/255))
    period = max(1., float(np.float32(normalized*24)))
    for frame in range(32, count):
        counter -= 1
        if counter < 0:
            counter += period
            yield frame


def fit_step(impulse, cutoff):
    parameters = np.array([np.log(np.tan(np.pi*cutoff/48000)), .919118])

    def residual(p):
        d, b = topology(p[0], p[1], 1, 'hpf')
        e = np.convolve(impulse, d)[:len(impulse)]
        e[:len(b)] -= b
        return e

    for _ in range(20):
        e = residual(parameters)
        jacobian = np.stack([(residual(parameters+np.eye(2)[j]*1e-5)-e)/1e-5 for j in range(2)], 1)
        step = np.linalg.lstsq(jacobian, -e, rcond=1e-10)[0]
        parameters += step
        if np.linalg.norm(step) < 1e-10:
            break
    d, b = topology(parameters[0], parameters[1], 1, 'hpf')
    return {'cutoff_hz': float(2*np.arctan(np.exp(parameters[0]))*48000/(2*np.pi)),
            'resonance': float(parameters[1]), 'reconstructed_relative_rms_error': response_error(impulse, d, b)}


def long_clock(session):
    rows = []
    for raw in (113, 177, 213, 253):
        folder = next((session/name for name in (f'diagnostic-long-main-{raw}', f'crush-clock-{raw}')
                       if (session/name/'receipt.json').exists()), None)
        if folder is None:
            raise ValueError('Missing long clock capture at ' + str(raw))
        receipt, output = checked(folder)
        rate, source = float_wav(Path(receipt['input_path']))
        if rate != 48000 or len(source) != 336000:
            raise ValueError('Use the seven-second clock-white recipe')
        expected = np.zeros((336000, 2), dtype=np.float32)
        expected[48000:288000] = np.random.default_rng(0xC205AC77).normal(0, .03, (240000, 2))
        if not np.array_equal(source, expected):
            raise ValueError('Incorrect clock-white source')
        plan = json.loads((folder/'plan.json').read_text())
        controls = {p['name']: p['value'] for p in plan['parameters']}
        if (plan['events'] or controls['Sub1Volume'] != 0 or controls['Sub2Volume'] != 0
                or abs(controls['SceneVolume']-raw/255) > 1e-7 or controls['CrushEchoButton'] != 1):
            raise ValueError('Incorrect direct-only clock plan')
        count = min(len(source), len(output)-32)
        dry = max(0, 1-max(0, raw-3)/126)**2
        cutoff = round(60*np.exp(max(raw-4, 0)*.0168583737))
        d, b = topology(np.log(np.tan(np.pi*cutoff/48000)), .919118, 1, 'hpf')
        pole = -b[3]/b[0]
        predicted = np.zeros(count, dtype=bool)
        predicted[list(hold_events(raw, count))] = True
        channels = []
        for channel in (0, 1):
            wet = (output[32:32+count, channel].astype(float)-source[:count, channel].astype(float)*dry)/(1-dry)
            v = np.convolve(wet, d)[:count]/b[0]
            # Recover first differences of held input, avoiding the unstable
            # double integration that direct HP inversion would require.
            delta = np.zeros(count)
            for i in range(count):
                delta[i] = v[i]+((1+pole)*delta[i-1] if i else 0)-(pole*delta[i-2] if i >= 2 else 0)
            observed = abs(delta) > 1e-4
            observed[:48000], observed[288000:] = False, False
            missed = int(np.count_nonzero(observed & ~predicted))
            if np.count_nonzero(observed) < 5000:
                raise ValueError('Too few observed hold events for clock validation')
            channels.append({'channel': ('left', 'right')[channel],
                             'nontrivial_observed_events': int(np.count_nonzero(observed)),
                             'missed_by_model': missed})
            if missed:
                raise ValueError('Long clock differs at raw ' + str(raw))
        rows.append({'raw': raw, 'receipt_sha256': sha256(folder/'receipt.json'), 'channels': channels})
    return rows


def identify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration = json.loads(args.calibration.read_text())
    if (calibration.get('verified') is not True or calibration.get('eligible_for_review') is not True
            or calibration.get('sample_rate') != 48000 or calibration.get('candidate_delay_frames') != -32):
        raise ValueError('Requires the separately reviewed original-to-core -32-frame bypass offset')
    rows = []
    for raw in (*CALIBRATION, *HOLDOUT):
        folder = next((args.session/name for name in (f'crush-step-main-{raw}', f'step-main-{raw}')
                       if (args.session/name/'receipt.json').exists()), None)
        if folder is None:
            raise ValueError('Missing step capture at raw ' + str(raw))
        receipt, output = checked(folder)
        rate, source = float_wav(Path(receipt['input_path']))
        expected = np.zeros((144000, 2), dtype=np.float32)
        expected[48000:120000] = [.125, -.09]
        plan = json.loads((folder/'plan.json').read_text())
        controls = {p['name']: p['value'] for p in plan['parameters']}
        if (rate != 48000 or not np.array_equal(source, expected) or plan['events']
                or plan['bpm'] != 120 or abs(controls['SceneVolume']-raw/255) > 1e-7
                or controls['CrushEchoButton'] != 1 or controls['Sub2Volume'] != 0):
            raise ValueError('Incorrect step recipe: ' + str(folder))
        dry = max(0, 1-max(0, raw-3)/126)**2
        row = {'raw': raw, 'used_for_fit': raw not in HOLDOUT, 'dry_gain': dry,
               'receipt_sha256': sha256(folder/'receipt.json'), 'output_sha256': receipt['output_sha256']}
        if raw > 3:
            channels = []
            predicted = next(frame-48000 for frame in hold_events(raw, 48100) if frame >= 48000)
            cutoff = round(60*np.exp(max(raw-4, 0)*.0168583737))
            for channel, amplitude in enumerate((float(np.float32(.125)), float(np.float32(-.09)))):
                step = (output[48032:56032, channel].astype(float)-amplitude*dry)/(1-dry)
                onset = int(np.flatnonzero(abs(step) > 1e-5)[0])
                impulse = np.diff(np.r_[0, step[onset:onset+6000]])/amplitude
                channels.append({'channel': ('left', 'right')[channel], 'observed_hold_onset': onset,
                                 'predicted_hold_onset': predicted, **fit_step(impulse, cutoff)})
                if onset != predicted:
                    raise ValueError('Hold clock differs from step onset at ' + str(raw))
            row['rounded_cutoff_law_hz'], row['channels'] = cutoff, channels
        rows.append(row)
    block_rows = []
    paths = [next((args.session/name for name in (f'diagnostic-white-main-128{suffix}', f'white-main-128{suffix}')
                   if (args.session/name/'receipt.json').exists()), None) for suffix in ('', '-block-32', '-block-256')]
    if all(paths):
        _, reference = checked(paths[0])
        for folder, block in zip(paths[1:], (32, 256), strict=True):
            _, candidate = checked(folder)
            end = max(128, block)
            block_rows.append({'block': block, 'receipt_sha256': sha256(folder/'receipt.json'),
                'maximum_startup_difference': float(np.max(abs(candidate[:end]-reference[:end]))),
                'bit_exact_after_frame': end, 'settled_bit_exact': bool(np.array_equal(candidate[end:], reference[end:]))})
    clocks = long_clock(args.clock_session) if args.clock_session else []
    save_json(args.report, {'kind': 'rmx220-crush-identification', 'identity': IDENTITY, 'sample_rate': 48000,
        'physical_hardware': False, 'calibration_sha256': sha256(args.calibration),
        'identifier_sha256': sha256(Path(__file__)), 'steps': rows, 'host_block_diagnostics': block_rows,
        'long_clock_checks': clocks,
        'model': {'amplitude_quantizer': 'No amplitude-resolution reduction required by the measured captures.',
            'hold_period_frames': 'max(1, float32(float32(raw*float32(1/255))*24)); retain both float rounding steps, then double accumulator',
            'settled_clock': 'counter initialized to zero at input frame 32; subtract 1 each frame; when counter<0, add period and sample both input channels.',
            'dry_gain': 'clamp((129-raw)/126,0,1)^2', 'wet_gain': '1-dry_gain',
            'filter': 'HPF Echo resonance topology, with raw-dependent resonance and round(60*exp(max(raw-4,0)*0.0168583737)) Hz cutoff.',
            'echo': 'Crossfaded quarter/half/three-quarter/one-beat combs; feedback 0.75, return 0.7, HP4 at 60 Hz.'},
        'limitations': ['Static factory Normal-width, Sub2 zero, 48 kHz. No general nonlinearity, overload or gesture claim.',
                       'The original first host block differs by host block size. Startup with immediate nonzero audio is not matched.']})
    print('Identified', len(rows), 'step cases; checked', len(block_rows), 'host-block diagnostics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    for name in ('host', 'plugin', 'session'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('identify')
    for name in ('session', 'calibration', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--clock-session', type=Path)
    args = parser.parse_args()
    {'capture': capture, 'identify': identify}[args.command](args)


if __name__ == '__main__':
    main()
