#!/usr/bin/env python3
"""Repeatable Spiral identification experiments, not an effect-match certificate."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, probe, run
from tools.rmx_spiral_return import BUTTONS


STAGES = ('initial', 'levels', 'structure', 'nonlinearity', 'crossings', 'binary')


def recipe(stage):
    waves, cases = {}, []
    t = np.arange(48000)/48000

    def pulse(offset=0, amplitude=.05, both=True, double=False):
        x = np.zeros((144000, 2))
        x[48000+offset] = [amplitude, -.8*amplitude if both else 0]
        if double:
            x[48064] = [amplitude, -.8*amplitude]
        return x

    def tone(amplitude=.01, left=1000, right=710, seconds=3):
        x = np.zeros((48000*seconds, 2))
        x[48000:96000] = amplitude*np.column_stack((np.sin(2*np.pi*left*t), .8*np.sin(2*np.pi*right*t)))
        return x

    def add(name, source, direction, main=128, time=0, pitch=0):
        cases.append({'name': direction+'-'+name, 'source': source, 'direction': direction,
                      'main': main, 'time': time, 'pitch': pitch})

    if stage == 'initial':
        x = np.zeros((240000, 2))
        x[48000, 0], x[144000, 1] = .05, -.04
        waves = {'impulses': x, 'probe': probe(), 'tones': tone(.05, seconds=6)}
        for direction in BUTTONS:
            for raw in (0, 32, 64, 96, 128, 160, 192, 224, 255):
                add(f'main-{raw}', 'impulses', direction, raw, 128)
            for raw in (64, 128, 192, 255):
                add(f'pitch-{raw}', 'impulses', direction, time=128, pitch=raw)
            for raw in (0, 32, 64, 96, 160, 192, 224, 255):
                add(f'time-{raw}', 'impulses', direction, time=raw)
            for raw in (0, 64, 128, 192, 255):
                add(f'tone-pitch-{raw}', 'tones', direction, time=128, pitch=raw)
            for raw in (64, 128, 255):
                add(f'probe-main-{raw}', 'probe', direction, raw, 128)
    elif stage == 'levels':
        for amplitude in (.0001, .001, .01, .05, .2):
            name = f'tone-{amplitude}'
            waves[name] = tone(amplitude)
            for direction in BUTTONS:
                for main in (32, 128):
                    add(f'tone-{main}-{amplitude}', name, direction, main)
        for amplitude in (.001, .01, .2, .5):
            name = f'impulse-{amplitude}'
            waves[name] = pulse(amplitude=amplitude)
            for direction in BUTTONS:
                add(name, name, direction)
    elif stage == 'structure':
        for offset in (0, 1, 16, 64, 128, 255):
            name = f'pulse-{offset}'
            waves[name] = pulse(offset)
            for direction in BUTTONS:
                add(f'offset-{offset}', name, direction)
        waves['double-pulse'] = pulse(double=True)
        for direction in BUTTONS:
            add('double-pulse', 'double-pulse', direction)
        for left, right in ((984.375, 1007.8125), (500, 710), (1000, 1010), (233, 3111), (48, 200)):
            name = f'freq-{left}-{right}'
            waves[name] = tone(left=left, right=right)
            for direction in BUTTONS:
                add(name, name, direction)
        waves['tones'] = tone(.05, seconds=6)
        for direction in BUTTONS:
            for raw in (8, 16, 32, 48, 80, 96, 112, 144, 160, 176, 208, 224, 240):
                add(f'pitch-{raw}', 'tones', direction, pitch=raw)
    elif stage == 'nonlinearity':
        signals = {'step': np.ones(48000)*.02,
                   'square': .01*np.sign(np.sin(2*np.pi*1000*t)),
                   'triangle': .01*(2/np.pi)*np.arcsin(np.sin(2*np.pi*1000*t)),
                   'biased': .02+.005*np.sin(2*np.pi*1000*t),
                   'two-tone': .007*(np.sin(2*np.pi*1000*t)+np.sin(2*np.pi*710*t))}
        for name, signal in signals.items():
            x = np.zeros((144000, 2))
            x[48000:96000] = np.column_stack((signal, -.8*signal))
            waves[name] = x
            for direction in BUTTONS:
                add(name, name, direction)
        waves['pulse'], waves['double-pulse'] = pulse(), pulse(double=True)
        for direction in BUTTONS:
            for repeat in (0, 1):
                add(f'pulse-repeat-{repeat}', 'pulse', direction)
                add(f'double-repeat-{repeat}', 'double-pulse', direction)
    elif stage == 'crossings':
        for phase in (0, 1/48, 1/24, 1/12, 1/3):
            signal = .01*np.sin(2*np.pi*1000*t+np.pi*phase)
            for right in ('zero', 'same', 'opposite'):
                x = np.zeros((144000, 2))
                x[48000:96000, 0] = signal
                if right != 'zero':
                    x[48000:96000, 1] = signal*(.8 if right == 'same' else -.8)
                name = f'phase-{phase}-{right}'
                waves[name] = x
                for direction in BUTTONS:
                    add(name, name, direction)
        for name, signal in (('square', .01*np.sign(np.sin(2*np.pi*1000*t))),
                             ('triangle', .01*(2/np.pi)*np.arcsin(np.sin(2*np.pi*1000*t)))):
            x = np.zeros((144000, 2))
            x[48000:96000, 0] = signal
            waves[name] = x
            for direction in BUTTONS:
                add(name, name, direction)
    elif stage == 'binary':
        rng = np.random.default_rng(0x5A17A1)
        for name in ('binary', 'white'):
            x = np.zeros((336000, 2))
            signal = rng.standard_normal(240000)
            x[48000:288000, 0] = .01*(np.sign(signal) if name == 'binary' else signal)
            waves[name] = x
            for direction in BUTTONS:
                add(name, name, direction)
    return waves, cases


def capture(args):
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')

    def setting(name, value):
        parameter = next(p for p in inventory['parameters'] if p['name'] == name)
        return {k: parameter[k] for k in ('index', 'id', 'name')} | {'value': value}

    for stage in STAGES if args.stage == 'all' else (args.stage,):
        destination = new_directory(root/stage)
        waves, cases = recipe(stage)
        for name, samples in waves.items():
            write_wav(destination/(name+'.wav'), 48000, samples.ravel())
        for case in cases:
            controls = {'AutoButton': 1, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
                        'IsolatorButton': 0, 'DefaultSwitch': 1, 'UserSwitch': 0,
                        'SceneVolume': case['main']/255, 'Sub1Volume': case['time']/255,
                        'Sub2Volume': case['pitch']/255, BUTTONS[case['direction']]: 1}
            plan = {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'reference',
                    'expected_plugin': IDENTITY, 'sample_rate': 48000, 'bpm': 120,
                    'tail_seconds': 12 if stage == 'initial' else 2,
                    'parameters': [setting(k, v) for k, v in controls.items()], 'events': []}
            save_json(destination/(case['name']+'.json'), plan)
            run([args.host, 'render', args.plugin, destination/(case['source']+'.wav'),
                 destination/(case['name']+'.json'), destination/case['name'], 128])
            case['receipt_sha256'] = sha256(destination/case['name']/'receipt.json')
            print(stage, case['name'], flush=True)
        save_json(destination/'matrix.json', {'kind': 'rmx220-spiral-characterization-captures',
                  'stage': stage, 'cases': cases, 'capture_script_sha256': sha256(Path(__file__))})


def relative(a, b):
    return float(np.linalg.norm(a-b)/max(np.linalg.norm(a), 1e-25))


def characterize(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration = json.loads(args.calibration.read_text())
    if (calibration.get('verified') is not True or calibration.get('eligible_for_review') is not True
            or calibration.get('sample_rate') != 48000 or calibration.get('candidate_delay_frames') != -32):
        raise ValueError('Requires the independently reviewed -32-frame original-to-core bypass offset')
    roots = {stage: getattr(args, stage) or (args.session/stage if args.session else None) for stage in STAGES}
    if any(root is None for root in roots.values()):
        raise ValueError('Supply a complete session or all six stage directories')
    sources = {}

    def read(stage, name, wet=False):
        folder = roots[stage]/name
        receipt = json.loads((folder/'receipt.json').read_text())
        if (not receipt['complete'] or receipt['role'] != 'reference'
                or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
            raise ValueError('Incorrect reference: ' + str(folder))
        for path, key in ((folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                          (Path(receipt['input_path']), 'input_sha256')):
            if sha256(path) != receipt[key]:
                raise ValueError('Modified reference: ' + str(path))
        plan = json.loads((folder/'plan.json').read_text())
        controls = {p['name']: p['value'] for p in plan['parameters']}
        if (plan['sample_rate'] != 48000 or plan['events'] or controls['DefaultSwitch'] != 1
                or controls['AutoButton'] != 1 or controls['QuantizeButton'] != 0
                or controls['UserSwitch'] != 0 or controls['InputButton'] != 1 or controls['XpadButton'] != 0):
            raise ValueError('Outside static factory characterization')
        rate, audio = float_wav(folder/'audio.wav')
        if rate != 48000:
            raise ValueError('Requires 48 kHz')
        sources[stage+'/'+name] = {'stage': stage, 'case': name,
            'receipt_sha256': sha256(folder/'receipt.json'), 'input_sha256': receipt['input_sha256'],
            'output_sha256': receipt['output_sha256'], 'plan_sha256': receipt['plan_sha256'],
            'bpm': plan['bpm'], 'raw_controls': {k: round(controls[k]*255) for k in ('SceneVolume', 'Sub1Volume', 'Sub2Volume')}}
        if wet:
            if controls['SceneVolume'] > 128/255+1e-7:
                raise ValueError('Wet subtraction here requires measured unity dry')
            audio = audio[32:].astype(float)
            _, source = float_wav(Path(receipt['input_path']))
            count = min(len(audio), len(source))
            audio[:count] -= source[:count]
        return audio

    findings = {}
    for direction, delay in (('up', 1792), ('down', 640)):
        current = {'initial_dry_and_onset': [], 'pitch_diagnostics': [], 'tone_scaling': [],
                   'repeatability': [], 'time_shift_diagnostics': [], 'stereo_coupling': []}
        for raw in (0, 32, 64, 96, 128, 160, 192, 224, 255):
            audio = read('initial', f'{direction}-main-{raw}')
            dry = float(audio[48032, 0]/np.float32(.05))
            model = 1 if direction == 'up' else float(np.clip((255-raw)/126, 0, 1))
            response = audio[48032:60032, 0].astype(float).copy()
            response[0] -= float(np.float32(.05))*model
            hits = np.flatnonzero(abs(response) > 5e-8)
            current['initial_dry_and_onset'].append({'main_raw': raw, 'measured_dry_gain': dry,
                'dry_law_value': model, 'dry_gain_error': abs(dry-model),
                'first_wet_above_5e_8_frames': int(hits[0]) if len(hits) else None})
        for raw in (0, 8, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 255):
            stage = 'initial' if raw in (0, 64, 128, 192, 255) else 'structure'
            name = f'{direction}-tone-pitch-{raw}' if stage == 'initial' else f'{direction}-pitch-{raw}'
            audio = read(stage, name, wet=True)
            length = 32768
            magnitude = abs(np.fft.rfft(audio[57600:57600+length, 0]*np.hanning(length)))
            index = int(magnitude.argmax())
            correction = 0.
            if 0 < index < len(magnitude)-1:
                values = np.log(np.maximum(magnitude[index-1:index+2], 1e-30))
                correction = .5*(values[0]-values[2])/(values[0]-2*values[1]+values[2])
            current['pitch_diagnostics'].append({'sub2_raw': raw,
                'dominant_wet_frequency_hz': float((index+correction)*48000/length),
                'note': 'Dominant spectral component, not a fitted pitch law; default Sub1 differs between the two capture sets.'})
        baseline = read('levels', f'{direction}-tone-128-0.01', wet=True)[60000:80000]/.01
        for amplitude in (.0001, .001, .01, .05, .2):
            normalized = read('levels', f'{direction}-tone-128-{amplitude}', wet=True)[60000:80000]/amplitude
            current['tone_scaling'].append({'input_peak': amplitude,
                'normalized_waveform_relative_difference': relative(baseline, normalized)})
        for name in ('pulse', 'double'):
            first = read('nonlinearity', f'{direction}-{name}-repeat-0')
            second = read('nonlinearity', f'{direction}-{name}-repeat-1')
            current['repeatability'].append({'source': name, 'bit_exact': bool(np.array_equal(first, second))})
        first = read('structure', f'{direction}-offset-0', wet=True)
        second = read('structure', f'{direction}-offset-64', wet=True)
        together = read('structure', f'{direction}-double-pulse', wet=True)
        current['superposition_wet_relative_error'] = relative(together[48000:96000], first[48000:96000]+second[48000:96000])
        for offset in (1, 16, 64, 128, 255):
            shifted = read('structure', f'{direction}-offset-{offset}', wet=True)
            current['time_shift_diagnostics'].append({'input_shift_frames': offset,
                'wet_relative_error_after_known_input_shift': relative(first[48000:96000], shifted[48000+offset:96000+offset])})
        mono = read('crossings', f'{direction}-phase-0-zero', wet=True)
        level = float(np.sqrt(np.mean(mono[60000:80000, 0]**2)))
        for right in ('zero', 'same', 'opposite'):
            audio = read('crossings', f'{direction}-phase-0-{right}', wet=True)[60000:80000]
            current['stereo_coupling'].append({'right_input': right, 'left_input_unchanged': True,
                'left_wet_rms': float(np.sqrt(np.mean(audio[:, 0]**2))),
                'left_wet_rms_relative_to_right_silent': float(np.sqrt(np.mean(audio[:, 0]**2))/level)})
        current['waveform_tests'] = []
        for name in ('step', 'square', 'triangle', 'biased', 'two-tone'):
            audio = read('nonlinearity', f'{direction}-{name}', wet=True)[60000:80000]
            current['waveform_tests'].append({'source': name, 'left_wet_rms': float(np.sqrt(np.mean(audio[:, 0]**2)))})
        starts = np.arange(48000+delay+144, 96000+delay-48, 48)
        time = (starts+24-(48000+delay))/48000
        levels = np.array([np.sqrt(np.mean(mono[n:n+48, 0]**2)) for n in starts])

        def envelope(tau):
            design = np.column_stack((np.ones(len(time)), np.exp(-time/tau)))
            coefficients = np.linalg.lstsq(design, levels, rcond=None)[0]
            return np.linalg.norm(design@coefficients-levels), coefficients

        low, high = .04, .4
        for _ in range(50):
            a, b = low+(high-low)/3, high-(high-low)/3
            if envelope(a)[0] < envelope(b)[0]:
                high = b
            else:
                low = a
        tau = (low+high)/2
        error, coefficients = envelope(tau)
        current['attack_envelope_diagnostic'] = {'time_constant_seconds': tau,
            'relative_rms_fit_error': float(error/np.linalg.norm(levels)),
            'model': 'cycle RMS = c0+c1*exp(-elapsed/tau)', 'coefficients': coefficients.tolist(),
            'note': 'Diagnostic fit; not a verified internal envelope algorithm.'}
        current['constant_envelope_noise_diagnostic'] = []
        for name in ('binary', 'white'):
            audio = read('binary', f'{direction}-{name}', wet=True)
            receipt = json.loads((roots['binary']/f'{direction}-{name}'/'receipt.json').read_text())
            _, source = float_wav(Path(receipt['input_path']))
            size, hop = 16384, 8192
            starts = range(96000, 240000-size, hop)
            window = np.hanning(size)
            x = np.array([np.fft.rfft(source[n:n+size, 0]*window) for n in starts])
            y = np.array([np.fft.rfft(audio[n+delay:n+delay+size, 0]*window) for n in starts])
            xx, yy = np.mean(abs(x)**2, axis=0), np.mean(abs(y)**2, axis=0)
            xy = np.mean(np.conj(x)*y, axis=0)
            frequencies = np.fft.rfftfreq(size, 1/48000)
            selected = (frequencies >= 100) & (frequencies <= 15000)
            coherence = abs(xy)**2/np.maximum(xx*yy, 1e-30)
            current['constant_envelope_noise_diagnostic'].append({'source': name,
                'mean_magnitude_squared_coherence_100_15000_hz': float(np.mean(coherence[selected])),
                'fft_frames': size, 'hop_frames': hop,
                'output_window_offset_frames': delay,
                'note': 'Diagnostic only; windows use the independently observed wet onset offset. Finite-window coherence is not an architecture identification.'})
        findings[direction] = current
    save_json(args.report, {'kind': 'rmx220-spiral-characterization', 'sample_rate': 48000,
        'identity': IDENTITY, 'identifier_sha256': sha256(Path(__file__)),
        'calibration_sha256': sha256(args.calibration), 'sources': list(sources.values()), 'findings': findings,
        'full_spiral_match': False, 'physical_hardware': False,
        'conclusions': ['Repeated checked captures are deterministic; superposition does not hold.',
            'Wet response scales nearly homogeneously across checked tone levels.',
            'Changing the right channel strongly changes left wet level despite unchanged left input.',
            'A positive DC-biased tone produces almost no late wet output in the checked window.',
            'The generator architecture is not established. Fixed latency alone does not prove an FFT implementation.'],
        'remaining': ['Identify the shared amplitude detector and pitch/phase reconstruction.',
            'Measure Main time mapping, inner feedback, profiles and gestures, then validate an independent generator.']})
    print('Characterized', len(sources), 'original captures; no full Spiral match claimed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    for name in ('host', 'plugin', 'session'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--stage', choices=('all', *STAGES), default='all')
    p = commands.add_parser('analyze')
    p.add_argument('--session', type=Path)
    for stage in STAGES:
        p.add_argument('--'+stage, type=Path)
    p.add_argument('--calibration', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    {'capture': capture, 'analyze': characterize}[args.command](args)


if __name__ == '__main__':
    main()
