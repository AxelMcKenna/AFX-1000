#!/usr/bin/env python3
"""Identify Spiral components; a component fit is not a full-effect certificate."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, probe, run
from tools.rmx_filter_match import screen
from tools.rmx_spiral_return import BUTTONS, checked


STAGES = ('detector', 'peak-phase', 'linear', 'stereo-linear', 'long-clock', 'probe-zero')


def recipe(stage):
    waves, cases = {}, []

    def add(name, samples, mains=(128,), blocks=(128,), directions=BUTTONS, tail=3):
        waves[name] = samples
        for direction in directions:
            for main in mains:
                for block in blocks:
                    if stage == 'detector':
                        tag = f'{direction}-{name}-main-{main}'
                    elif stage == 'peak-phase':
                        tag = f'{direction}-offset-{name.removeprefix("spike-")}-block-{block}'
                    else:
                        tag = f'{direction}-{name}'
                    cases.append(dict(name=tag, direction=direction, main=main, block=block,
                                      source=name, tail=tail))

    if stage == 'detector':
        t = np.arange(120000)/48000
        sine = .01*np.sin(2*np.pi*1000*t)

        def tone(name, left, right, mains=(128,)):
            x = np.zeros((192000, 2))
            x[48000:168000, 0], x[48000:168000, 1] = left, right
            add(name, x, mains)

        for name, right in (('mono', 0), ('null', -sine), ('over-negative', -2*sine),
                            ('positive', 2*sine), ('right-dc-positive', .02), ('right-dc-negative', -.02)):
            tone(name, sine, right)
        tone('left-bias-balanced', sine+.02, -.02)
        tone('right-only', 0, sine)
        level = np.ones(len(t))
        level[24000:48000], level[48000:72000] = 2, .5
        tone('amplitude-steps', sine*level, 0, (32, 128, 224))
        level = np.zeros(len(t))
        level[24000:48000], level[48000:72000] = .8, -.8
        tone('stereo-steps', sine, sine*level, (32, 128, 224))
        for name, signal in (
            ('positive-pulses', .01*(np.arange(len(t)) % 48 == 0)),
            ('bipolar-pulses', .01*((np.arange(len(t)) % 48 == 0).astype(float)
                                   - (np.arange(len(t)) % 48 == 24))),
            ('square', .01*np.sign(sine)),
            ('triangle', .01*(2/np.pi)*np.arcsin(np.sin(2*np.pi*1000*t))),
        ):
            tone(name, signal, 0)
    elif stage == 'peak-phase':
        x = np.zeros((384000, 2))
        x[48000:288000, 0] = .01*np.sin(2*np.pi*1000*np.arange(240000)/48000)
        for offset in (0, 1, 7, 12, 16, 24, 31, 32, 64, 127):
            y = x.copy()
            y[72000+offset, 1] = .1-y[72000+offset, 0]
            add(f'spike-{offset}', y, blocks=(32, 128, 256) if offset in (12, 31) else (128,))
    elif stage == 'linear':
        for dc in (.02, .2):
            x = np.zeros((240000, 2))
            x[24000:192000, 1] = dc
            add(f'dc-{dc}-baseline', x)
            for amplitude in (.0001, .001):
                for source in ('impulse', 'tone'):
                    y = x.copy()
                    if source == 'impulse':
                        y[96000, 0] = amplitude
                    else:
                        y[96000:168000, 0] = amplitude*np.sin(2*np.pi*1000*np.arange(72000)/48000)
                    y[24000:192000, 1] -= y[24000:192000, 0]
                    add(f'dc-{dc}-{source}-{amplitude}', y)
    elif stage == 'stereo-linear':
        x = np.zeros((240000, 2))
        x[24000:48000] = (.1*np.sin(2*np.pi*20000*np.arange(24000)/48000))[:, None]
        add('baseline', x)
        for name, pulse in (('mono', [.0001, 0]), ('same', [.0001, .0001]),
                            ('opposite', [.0001, -.0001]), ('asymmetric', [.0001, -.00005])):
            y = x.copy()
            y[96000] = pulse
            add(name, y)
    elif stage == 'long-clock':
        # Tiny left input keeps more than 100 Down repeats below clipping.
        # The DC channel maintains detector level; this is an offline fixture.
        x = np.zeros((33*48000, 2))
        x[24000:32*48000, 1] = .2
        x[48000, 0] = 1e-12
        add('long-clock', x, directions=('down',), tail=1)
    elif stage == 'probe-zero':
        add('probe-time-0', probe(), tail=12)
    else:
        raise ValueError('Unknown stage: '+stage)
    return waves, cases


def capture(args):
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    waves, cases = recipe(args.stage)
    for name, samples in waves.items():
        write_wav(root/(name+'.wav'), 48000, samples.ravel())
    for case in cases:
        controls = {'AutoButton': 1, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
                    'DefaultSwitch': 1, 'UserSwitch': 0, 'Sub1Volume': 0, 'Sub2Volume': 0,
                    'SceneVolume': case['main']/255, BUTTONS[case['direction']]: 1}
        parameters = []
        for name, value in controls.items():
            matches = [p for p in inventory['parameters'] if p['name'] == name]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous control: '+name)
            parameters.append({k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value})
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference',
                    expected_plugin=IDENTITY, sample_rate=48000, bpm=120, tail_seconds=case['tail'],
                    parameters=parameters, events=[])
        save_json(root/(case['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/(case['source']+'.wav'),
             root/(case['name']+'.json'), root/case['name'], case['block']])
        print(case['name'], flush=True)
    save_json(root/'matrix.json', dict(kind='rmx220-spiral-core-captures', stage=args.stage,
              cases=cases, capture_script_sha256=sha256(Path(__file__))))


def filtered(b, a, source):
    """Double-precision direct-form II transposed, without SciPy dependency."""
    count = max(len(a), len(b))
    b, a = np.pad(b, (0, count-len(b))), np.pad(a, (0, count-len(a)))
    b, a = b/a[0], a/a[0]
    state = np.zeros(count-1)
    output = np.empty(len(source))
    for n, x in enumerate(source):
        y = b[0]*x+(state[0] if len(state) else 0)
        if len(state):
            state[:-1] = state[1:]+b[1:-1]*x-a[1:-1]*y
            state[-1] = b[-1]*x-a[-1]*y
        output[n] = y
    return output


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves, cases = recipe(args.stage)
    results = []
    for case in cases:
        folder = args.session/case['name']
        receipt, plan, controls, _ = checked(folder)
        _, source = float_wav(Path(receipt['input_path']))
        if (not np.array_equal(source, waves[case['source']].astype(np.float32))
                or round(controls['SceneVolume']*255) != case['main']
                or controls.get(BUTTONS[case['direction']]) != 1
                or plan['bpm'] != 120 or plan['tail_seconds'] != case['tail']
                or controls['Sub1Volume'] != 0
                or receipt['maximum_block_size'] != case['block']):
            raise ValueError('Capture differs from recipe: '+str(folder))
        results.append(dict(case=case['name'], receipt_sha256=sha256(folder/'receipt.json'),
                            input_sha256=receipt['input_sha256'], output_sha256=receipt['output_sha256'],
                            plan_sha256=receipt['plan_sha256']))
    save_json(args.report, dict(kind='rmx220-spiral-core-recipe-verification', stage=args.stage,
        recipe_script_sha256=sha256(Path(__file__)), reference_identity=IDENTITY, cases=results,
        passed=True, scope='Input samples, static controls and capture hashes only; no sonic-match claim.'))
    print('Verified', len(results), 'capture recipes')


def lowpass(hz, q):
    w = 2*np.pi*hz/48000
    alpha = np.sin(w)/(2*q)
    return (np.array([1-np.cos(w), 2*(1-np.cos(w)), 1-np.cos(w)])/2/(1+alpha),
            np.array([1, -2*np.cos(w)/(1+alpha), (1-alpha)/(1+alpha)]))


def highpass(pole, source):
    return filtered([(1+pole)/2, -(1+pole)/2], [1, -pole], source)


def refine(function, initial, iterations=25):
    p = np.array(initial, dtype=float)
    for _ in range(iterations):
        error = function(p)
        jacobian = np.column_stack([(function(p+np.eye(len(p))[j]*1e-5)-error)/1e-5
                                    for j in range(len(p))])
        step = np.linalg.lstsq(jacobian, -error, rcond=1e-10)[0]
        if np.linalg.norm(step) < 1e-10:
            break
        for divisor in (1, 2, 4, 8, 16, 32, 64, 128):
            proposal = p+step/divisor
            if np.isfinite(proposal).all() and np.linalg.norm(function(proposal)) < np.linalg.norm(error):
                p = proposal
                break
        else:
            break
    return p


def relative(reference, candidate):
    return float(np.linalg.norm(reference-candidate)/max(np.linalg.norm(reference), 1e-30))


def calibration(path):
    data = json.loads(path.read_text())
    if (data.get('verified') is not True or data.get('eligible_for_review') is not True
            or data.get('sample_rate') != 48000 or data.get('candidate_delay_frames') != -32):
        raise ValueError('Requires the independently reviewed -32-frame original bypass calibration')


def identify(args):
    if args.report.exists() or (args.header is not None and args.header.exists()):
        raise ValueError('Report and optional header must be new')
    calibration(args.calibration)
    provenance = {}

    def read(root, name, wet=False):
        folder = root/name
        receipt, plan, controls, audio = checked(folder)
        if plan['bpm'] != 120:
            raise ValueError('Identification recipe requires 120 BPM')
        if controls['SceneVolume'] > 128/255+1e-7:
            raise ValueError('Identification requires the measured unity-dry range')
        provenance[str(folder)] = dict(case=name, receipt_sha256=sha256(folder/'receipt.json'),
            input_sha256=receipt['input_sha256'], output_sha256=receipt['output_sha256'],
            plan_sha256=receipt['plan_sha256'], maximum_block_size=receipt['maximum_block_size'])
        audio = audio[32:]
        if wet:
            _, source = float_wav(Path(receipt['input_path']))
            count = min(len(audio), len(source))
            audio[:count] -= source[:count]
        return audio

    h = read(args.linear, 'down-dc-0.2-impulse-0.0001')[96640:98688, 0]/.0001
    # Only the uncontaminated first pass is fitted, before another internal repeat.
    indices = np.arange(48, 2048)

    def tail(p, result=False):
        poles = np.tanh(p)
        design = poles[None, :]**indices[:, None]
        coefficients = np.linalg.lstsq(design, h[indices], rcond=None)[0]
        residual = (design@coefficients-h[indices])/np.linalg.norm(h[indices])
        return (poles, coefficients, residual) if result else residual

    p = refine(tail, np.arctanh([.99738342, .9934764, .94277851]))
    poles, tail_coefficients, tail_residual = tail(p, True)
    scaling, clocks, loop_fits = [], [], []
    first_pass = {}
    for direction, latency, delay in (('up', 1792, 2496), ('down', 640, 12144)):
        audio = read(args.linear, f'{direction}-dc-0.2-impulse-0.0001')
        first = audio[96000+latency:96000+latency+2048, 0]/.0001
        first_pass[direction] = first
        for dc in (.02, .2):
            for amplitude in (.0001, .001):
                a = read(args.linear, f'{direction}-dc-{dc}-impulse-{amplitude}')
                measured = a[96000+latency:96000+latency+2048, 0]/amplitude
                scaling.append(dict(direction=direction, dc=dc, impulse_peak=amplitude,
                                    normalized_first_pass_relative_error=relative(first, measured)))
        second = audio[96000+latency+delay:96000+latency+delay+2048, 0]/.0001
        # The slow first-pass tail is removed before fitting a return.
        gain_ratio = np.dot(first, h)/np.dot(h, h)
        second = second-gain_ratio*((poles[None, :]**np.arange(delay, delay+2048)[:, None])@tail_coefficients)

        def loop(p, result=False):
            hz, q = np.exp(p)
            if not 1000 < hz < 23000 or not .1 < q < 5:
                return np.ones(512)*1e6
            filtered_first = filtered(*lowpass(hz, q), first)
            for pole in poles[1:]:
                filtered_first = highpass(pole, filtered_first)
            design = np.column_stack((filtered_first, np.r_[0, filtered_first[:-1]]))
            coefficients = np.linalg.lstsq(design[:512], second[:512], rcond=None)[0]
            residual = (design[:512]@coefficients-second[:512])/np.linalg.norm(second[:512])
            return (hz, q, coefficients, residual) if result else residual

        p = refine(loop, np.log([12100, .7]))
        hz, q, coefficients, residual = loop(p, True)
        loop_fits.append(dict(direction=direction, delay_floor_frames=delay, lowpass_hz=hz,
            lowpass_Q=q, gain=float(coefficients.sum()),
            interpolation_fraction=float(coefficients[1]/coefficients.sum()),
            relative_rms_error=float(np.linalg.norm(residual))))
        signal = audio[96000+latency:, 0]/.0001
        for repeat in range(16):
            x, y = signal[repeat*delay:repeat*delay+2048], signal[(repeat+1)*delay:(repeat+1)*delay+2048]
            v = filtered(*lowpass(12100, .7), x)
            for pole in poles[1:]:
                v = highpass(pole, v)
            design = np.column_stack((v, np.r_[0, v[:-1]]))
            coefficients = np.linalg.lstsq(design[:512], y[:512], rcond=None)[0]
            clocks.append(dict(direction=direction, repeat=repeat, gain=float(coefficients.sum()),
                fraction=float(coefficients[1]/coefficients.sum()),
                relative_rms_error=relative(y[:512], design[:512]@coefficients)))

    impulse = np.zeros(2048)
    impulse[0] = 1
    targets = [h]
    peaks = [.05, .01]
    for root, name in ((args.initial, 'down-main-128'), (args.structure, 'down-offset-0')):
        targets.append(read(root, name)[48640:50688, 0])

    def source_model(p, result=False):
        hz, q, m = np.exp(p)
        if not 6000 < hz < 18000 or not .3 < q < 2 or not 1e-5 < m < .05:
            return np.ones(6144)*1e6
        source = filtered(*lowpass(hz, q), impulse)
        signals = [source, *[np.clip(source*.05, -peak*m, peak*m) for peak in peaks]]
        matrices, values = [], []
        for signal, target in zip(signals, targets):
            v = filtered(*lowpass(12100, .7), signal)
            for pole in poles:
                v = highpass(pole, v)
            design = np.column_stack([np.r_[np.zeros(i), v[:len(v)-i]] for i in range(32)])
            matrices.append(design/np.linalg.norm(target))
            values.append(target/np.linalg.norm(target))
        design, desired = np.concatenate(matrices), np.concatenate(values)
        coefficients = np.linalg.lstsq(design, desired, rcond=1e-10)[0]
        residual = design@coefficients-desired
        return (hz, q, m, coefficients, residual) if result else residual

    p = refine(source_model, np.log([12000, .707, .0026738]), iterations=12)
    hz, q, m, shape, source_residual = source_model(p, True)
    blocks, stereo = [], []
    for direction in BUTTONS:
        baseline = read(args.peak_phase, f'{direction}-offset-0-block-128')
        for offset in (1, 7, 12, 16, 24, 31):
            audio = read(args.peak_phase, f'{direction}-offset-{offset}-block-128')
            blocks.append(dict(direction=direction, pulse_offset=offset,
                               left_bit_exact_with_offset_zero=bool(np.array_equal(baseline[:, 0], audio[:, 0]))))
        for offset in (12, 31):
            baseline = read(args.peak_phase, f'{direction}-offset-{offset}-block-128')
            for block in (32, 256):
                audio = read(args.peak_phase, f'{direction}-offset-{offset}-block-{block}')
                blocks.append(dict(direction=direction, pulse_offset=offset, host_block=block,
                                   stereo_bit_exact_with_block_128=bool(np.array_equal(baseline, audio))))
        reference = read(args.stereo_linear, direction+'-baseline')
        mono = read(args.stereo_linear, direction+'-mono')-reference
        for mode, scale in (('same', 1), ('opposite', -1), ('asymmetric', -.5)):
            audio = read(args.stereo_linear, direction+'-'+mode)-reference
            stereo.append(dict(direction=direction, mode=mode,
                unchanged_left_bit_exact=bool(np.array_equal(mono[:, 0], audio[:, 0])),
                scope='Quiet differential signals; first 30000 frames after the impulse only.',
                right_relative_to_scaled_left=relative(audio[96000:126000, 1],
                                                       audio[96000:126000, 0]*scale)))
        stereo.append(dict(direction=direction, mode='mono',
            right_differential_maximum=float(abs(mono[96000:126000, 1]).max())))
    save_json(args.report, dict(kind='rmx220-spiral-core-identification', sample_rate=48000,
        reference_identity=IDENTITY, full_spiral_match=False, physical_hardware=False,
        identifier_sha256=sha256(Path(__file__)), calibration_sha256=sha256(args.calibration),
        sources=list(provenance.values()), first_pass_scaling=scaling,
        highpass_tail=dict(poles=poles.tolist(), coefficients=tail_coefficients.tolist(),
                           relative_rms_error=float(np.linalg.norm(tail_residual))),
        linear_loop=loop_fits, repeat_clock=clocks, block_peak_evidence=blocks,
        first_pass_output_scale={direction: float(np.dot(first, h)/np.dot(h, h))
                                 for direction, first in first_pass.items()},
        quiet_stereo_differentials=stereo, input_clip_model=dict(lowpass_hz=hz, lowpass_Q=q,
            first_block_threshold_per_input_peak=m, output_shape_fir=shape.tolist(),
            normalized_component_errors=[float(np.linalg.norm(part)) for part in np.split(source_residual, 3)],
            note='Only first-pass windows. Separating envelope coefficient from threshold scale needs further evidence.'),
        limitations=['No full-effect, hardware, other Main/pitch, overload or gesture match.',
                     'Component fits alone do not validate nonlinear feedback or complete renders.',
                     'Quiet stereo differential evidence does not establish nonlinear channel behavior.']))
    if args.header is not None:
        def array(name, values):
            body = ',\n    '.join(','.join(format(x, '.17g') for x in values[n:n+4])
                                   for n in range(0, len(values), 4))
            return f'inline constexpr std::array<double,{len(values)}> {name}{{\n    {body}\n}};'
        up_scale = float(np.dot(first_pass['up'], h)/np.dot(h, h))
        delays = [row['delay_floor_frames']+row['interpolation_fraction'] for row in loop_fits]
        args.header.parent.mkdir(parents=True, exist_ok=True)
        args.header.write_text('\n'.join([
            '#pragma once', '#include <array>', '',
            '// First-pass calibration for an incomplete research model; see ../spiral-core.md.',
            '// Generated by tools.rmx_spiral_core identify. Full-effect matching fails.',
            array('spiralShape', shape.tolist()), array('spiralHighPassPoles', poles.tolist()),
            array('spiralLoopDelay', delays),
            '// A 0.5 threshold scale is a candidate convention, not a verified envelope model.',
            f'inline constexpr double spiralEnvelopeAlpha={2*m:.17g};',
            f'inline constexpr double spiralUpOutputScale={up_scale:.17g};', '']))
    print('Wrote component identification; full Spiral matching remains incomplete')


def compare(args):
    calibration(args.calibration)
    folders = list(args.case)
    excluded = []
    for session in getattr(args, 'session', []):
        for receipt_path in sorted(session.glob('*/receipt.json')):
            folder = receipt_path.parent
            plan = json.loads((folder/'plan.json').read_text())
            controls = {p['name']: p['value'] for p in plan['parameters']}
            if (round(controls['SceneVolume']*255) != 128 or controls['Sub2Volume'] != 0
                    or plan['bpm'] != 120):
                excluded.append(dict(session=session.name, case=folder.name,
                    reason='Outside the candidate Main128/Sub2-zero/120-BPM scope; not a sonic result.'))
            else:
                folders.append(folder)
    folders = list(dict.fromkeys(p.resolve() for p in folders))
    if not folders:
        raise ValueError('Supply at least one --case or eligible --session capture')
    root = new_directory(args.output)
    cases = []
    for folder in folders:
        receipt, plan, controls, audio = checked(folder)
        if round(controls['SceneVolume']*255) != 128 or plan['bpm'] != 120:
            raise ValueError('Diagnostic prototype supports only Main128, 120 BPM')
        direction = next(k for k, button in BUTTONS.items() if controls.get(button) == 1)
        destination = root/f'{len(cases):02d}-candidate.wav'
        run([args.renderer, receipt['input_path'], destination, direction,
             round(controls['Sub1Volume']*255), plan['tail_seconds']])
        _, candidate = float_wav(destination)
        reference = audio[32:]
        candidate = candidate[:len(reference)].astype(float)
        if len(candidate) != len(reference):
            raise ValueError('Candidate is too short')
        _, source = float_wav(Path(receipt['input_path']))
        dry = np.zeros_like(reference)
        count = min(len(dry), len(source))
        dry[:count] = source[:count]
        whole, wet = screen(reference, candidate), screen(reference-dry, candidate-dry)
        cases.append(dict(session=folder.parent.name, case=folder.name,
            reference_receipt_sha256=sha256(folder/'receipt.json'),
            input_sha256=receipt['input_sha256'], reference_output_sha256=receipt['output_sha256'],
            reference_plan_sha256=receipt['plan_sha256'], direction=direction,
            main_raw=128, sub1_raw=round(controls['Sub1Volume']*255), sub2_raw=0,
            bpm=120, tail_seconds=plan['tail_seconds'],
            candidate_sha256=sha256(destination), whole=whole, wet=wet))
        print('PASS' if whole['passed'] and wet['passed'] else 'FAIL', folder.name, flush=True)
    save_json(root/'comparison.json', dict(kind='diagnostic-spiral-neutral-prototype-comparison',
        full_spiral_match=False, physical_hardware=False, sample_rate=48000,
        reference_identity=IDENTITY,
        renderer_sha256=sha256(args.renderer), calibration_sha256=sha256(args.calibration),
        comparison_script_sha256=sha256(Path(__file__)),
        acceptance=dict(relative_rms_error_limit=.01, silent_channel_absolute_rms_limit=1e-8,
                        reference_channel_energy_floor=1e-20,
                        gain_fit=False, wet_alignment_search=False, reference_offset_frames=32),
        passed=all(c['whole']['passed'] and c['wet']['passed'] for c in cases), cases=cases,
        out_of_scope_captures=excluded,
        scope='Experimental Main128, Sub2 zero, Default, 48 kHz, 120 BPM. Includes failed full renders.'))
    return 0 if all(c['whole']['passed'] and c['wet']['passed'] for c in cases) else 1


def clock(args):
    """Identify a quiet left-channel clock, not the nonlinear complete effect."""
    calibration(args.calibration)
    root = new_directory(args.output)
    folder = args.session/'down-long-clock'
    receipt, plan, controls, audio = checked(folder)
    waves, cases = recipe('long-clock')
    _, source = float_wav(Path(receipt['input_path']))
    if (not np.array_equal(source, waves['long-clock'].astype(np.float32))
            or round(controls['SceneVolume']*255) != 128 or controls['Sub1Volume'] != 0
            or controls.get(BUTTONS['down']) != 1 or plan['bpm'] != 120
            or plan['tail_seconds'] != cases[0]['tail'] or receipt['maximum_block_size'] != 128):
        raise ValueError('Requires the exact long-clock capture recipe')
    # Remove only the reviewed bypass offset and the already measured Down
    # component latency. There is no per-repeat wet alignment or gain fit in
    # the independent complete-window comparison below.
    first = 48000+640
    measured = audio[32+first:, 0]/1e-12
    delay = 12144
    b, a = lowpass(12100, .7)
    observations = []
    for repeat in range(119):
        x = measured[repeat*delay:repeat*delay+2048]
        y = measured[(repeat+1)*delay:(repeat+1)*delay+2048]
        if len(y) != 2048:
            raise ValueError('Incomplete long-clock recording')
        f = filtered(b, a, x)
        for pole in (.9934764, .94277851):
            f = highpass(pole, f)
        best = None
        for lag in range(-3, 7):
            indices = np.arange(2048)-lag
            design = np.column_stack([np.interp(indices, np.arange(2048), f, left=0, right=0),
                np.interp(indices-1, np.arange(2048), f, left=0, right=0)])
            coefficients = np.linalg.lstsq(design[:1024], y[:1024], rcond=None)[0]
            if min(coefficients) < -.0001 or sum(coefficients) <= 0:
                continue
            error = relative(y[:1024], design[:1024]@coefficients)
            frame = 48000+(repeat+1)*delay
            phase = 2.086162567138672e-6*((frame//32)*32-64)
            triangle = 1-abs((phase+1) % 4-2)
            fraction = triangle % 1
            fitted = float(coefficients[1]/sum(coefficients))
            row = dict(repeat=repeat, transition_frame=frame, delay_floor=delay+lag,
                measured_fraction=fitted, model_fraction=fraction,
                circular_fraction_error=float((fitted-fraction+.5) % 1-.5),
                gain=float(sum(coefficients)), component_fit_relative_rms_error=error)
            if best is None or error < best['component_fit_relative_rms_error']:
                best = row
        if best is None:
            raise ValueError('No positive fractional-delay fit at repeat '+str(repeat))
        observations.append(best)
    output = root/'candidate.wav'
    run([args.renderer, receipt['input_path'], output, 'down', 0, 1])
    _, candidate = float_wav(output)
    reference = audio[32:]
    if len(candidate) < len(reference):
        raise ValueError('Candidate is too short')
    windows = []
    for second in range(1, 32):
        # Both sides use the known input amplitude for numerical conditioning;
        # this is not a candidate amplitude fit. Tiny signals must not silently
        # pass the ordinary silent-channel absolute leakage check.
        window = slice(second*48000, (second+1)*48000)
        error = relative(reference[window, 0]/1e-12, candidate[window, 0].astype(float)/1e-12)
        windows.append(dict(start_seconds=second, frames=48000,
                            relative_rms_error=error, passed=error <= .01))
    component_passed = (all(x['passed'] for x in windows)
        and all(x['delay_floor'] == delay and abs(x['circular_fraction_error']) < .001
                and abs(x['gain']-1.2) < .0001
                and x['component_fit_relative_rms_error'] < .0001 for x in observations))
    report = dict(kind='rmx220-spiral-long-neutral-clock-identification', sample_rate=48000,
        reference_identity=IDENTITY, full_spiral_match=False, physical_hardware=False,
        component_screen_passed=component_passed, identifier_sha256=sha256(Path(__file__)),
        renderer_sha256=sha256(args.renderer), calibration_sha256=sha256(args.calibration),
        reference_receipt_sha256=sha256(folder/'receipt.json'), input_sha256=receipt['input_sha256'],
        reference_output_sha256=receipt['output_sha256'], plan_sha256=receipt['plan_sha256'],
        candidate_sha256=sha256(output), observations=observations, left_complete_windows=windows,
        empirical_model=dict(delay_floor=delay, increment_per_frame=2.086162567138672e-6,
            block_frames=32, origin_frames=64,
            formula='u=increment*(32*floor(frame/32)-64); t=1-abs(((u+1) mod 4)-2); fraction=t-floor(t)'),
        limitations=['Only the quiet left-channel clock is assessed. Right-channel DC/tails are excluded.',
            'Per-repeat gain/fraction fits identify components; only complete windows use the fixed candidate.',
            'No attribution to manufacturer implementation, other pitch/Main/tempo, hardware or complete Spiral match.'])
    save_json(root/'clock.json', report)
    print('PASS' if component_passed else 'FAIL', 'quiet left clock; complete Spiral remains unmatched')
    return 0 if component_passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    for name in ('host', 'plugin', 'session'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--stage', choices=STAGES, required=True)
    p = commands.add_parser('verify')
    p.add_argument('--stage', choices=STAGES, required=True)
    p.add_argument('--session', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p = commands.add_parser('identify')
    for name in ('linear', 'peak-phase', 'stereo-linear', 'initial', 'structure', 'calibration', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--header', type=Path)
    p = commands.add_parser('compare')
    p.add_argument('--case', type=Path, action='append', default=[])
    p.add_argument('--session', type=Path, action='append', default=[])
    for name in ('renderer', 'calibration', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('clock')
    for name in ('session', 'renderer', 'calibration', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = {'capture': capture, 'verify': verify, 'identify': identify,
              'compare': compare, 'clock': clock}[args.command](args)
    raise SystemExit(result or 0)


if __name__ == '__main__':
    main()
