#!/usr/bin/env python3
"""Probe Spiral's held clipping threshold; first-pass fits do not certify tails."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_spiral_core import calibration, filtered, highpass, lowpass, relative
from tools.rmx_spiral_return import BUTTONS, checked


STAGES = ('memory', 'timing', 'level', 'after-tone', 'reset', 'reset-small',
          'reset-edge', 'reset-fine', 'reset-validation', 'stereo-reset', 'boundary', 'attack')
ALPHA = .0053475940746570234  # Fixed stimulus design, not a new identified parameter.


def recipe(stage):
    waves, cases = {}, []

    def add(name, samples, frame, initial, directions=('down',), tail=1, **metadata):
        waves[name] = samples
        for direction in directions:
            cases.append(dict(name=direction+'-'+name, source=name, direction=direction,
                query_frame=frame, initial_amplitude=initial, tail=tail, **metadata))

    def pulse(name, initial=.05, offset=6720, onset=0, seconds=3, tail=1,
              directions=('down',), reset=None):
        x = np.zeros((seconds*48000, 2))
        x[48000+onset, 0] = initial
        frame = 48000+onset+offset
        x[frame, 1] = initial*.04
        if reset is not None:
            x[51840, 0] = reset
        add(name, x, frame, initial, directions, tail, precondition='pulse',
            offset=offset, onset=onset, reset_amplitude=reset)

    if stage == 'memory':
        for offset in (480, 2400, 4800, 12000, 24000, 48000, 96000, 192000):
            pulse(f'query-{offset}', offset=offset, seconds=7, tail=2, directions=tuple(BUTTONS))
    elif stage == 'timing':
        settings = [(0, offset) for offset in
            (5984, 8992, 11008, 11936, 11968, 12000, 12032, 12064, 15008, 17984, 23968, 24000, 24032)]
        settings += [(onset, offset) for onset in (16, 3200, 6000)
                     for offset in (8992, 11968, 12032, 15008)]
        for onset, offset in settings:
            pulse(f'onset-{onset}-query-{offset}', onset=onset, offset=offset)
    elif stage == 'boundary':
        for onset in (0, 16):
            for offset in (4768, 4800, 4832, 4864):
                pulse(f'onset-{onset}-query-{offset}', onset=onset, offset=offset)
    elif stage == 'level':
        for amplitude in (.0001, .001, .01, .05, .2, .5, .8):
            pulse(f'level-{amplitude}', initial=amplitude, offset=96000, seconds=5)
    elif stage == 'reset':
        for amplitude in (0, .0001, .00025, .0003, .0004, .00045, .00047, .0005, .001):
            pulse(f'reset-{amplitude}', reset=amplitude)
    elif stage == 'reset-small':
        for initial in (.0001, .05):
            for amplitude in (0, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, .00003):
                pulse(f'initial-{initial}-reset-{amplitude}', initial=initial, reset=amplitude)
    elif stage == 'reset-edge':
        for initial in (.0001, .05):
            for ratio in (1e-5, 2e-5, 3e-5, 4e-5, 5e-5, 6e-5, 8e-5, .0001):
                pulse(f'initial-{initial}-ratio-{ratio}', initial=initial, reset=initial*ratio)
                cases[-1]['reset_ratio'] = ratio
    elif stage == 'reset-fine':
        for ratio in (3.5e-5, 3.8e-5, 3.9e-5, 3.95e-5, 3.97e-5, 3.98e-5):
            pulse(f'ratio-{ratio}', reset=.05*ratio)
            cases[-1]['reset_ratio'] = ratio
    elif stage == 'reset-validation':
        # Prospective checks straddle the proposed 1/1024 gate and repeat at
        # three host block sizes. Predictions are part of the fixed recipe.
        for ratio, expected in ((3.87e-5, 10**(-1/20)), (3.88e-5, 1.)):
            for block in (32, 128, 256):
                pulse(f'ratio-{ratio}-block-{block}', reset=.05*ratio)
                cases[-1].update(reset_ratio=ratio, block=block,
                                 expected_threshold_relative=expected)
    elif stage == 'stereo-reset':
        for right in (0, 1, -1, -.99, -2):
            x = np.zeros((144000, 2))
            x[48000, 0], x[51840], x[54720, 1] = .05, [1e-5, right*1e-5], .002
            add(f'stereo-{right}', x, 54720, .05, precondition='pulse',
                reset_frame=51840, reset_amplitude=1e-5, reset_right_ratio=right)
    elif stage == 'after-tone':
        for frame in (172800, 192000, 240000, 288000):
            x = np.zeros((384000, 2))
            x[48000:168000, 0] = .01*np.sin(2*np.pi*1000*np.arange(120000)/48000)
            x[frame, 1] = .05
            add(f'query-{frame}', x, frame, .01, tuple(BUTTONS), precondition='tone')
    elif stage == 'attack':
        for blocks in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
            frame = 48000+blocks*32
            amplitude = 8*.01*(1-(1-ALPHA)**blocks)
            x = np.zeros((240000, 2))
            x[48000:frame, 0], x[frame, 1] = .01, amplitude
            add(f'blocks-{blocks}', x, frame, .01, precondition='dc', precondition_blocks=blocks)
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
            'DefaultSwitch': 1, 'UserSwitch': 0, 'SceneVolume': 128/255,
            'Sub1Volume': 0, 'Sub2Volume': 0, BUTTONS[case['direction']]: 1}
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
             root/(case['name']+'.json'), root/case['name'], case.get('block', 128)])
        print(case['name'], flush=True)
    save_json(root/'matrix.json', dict(kind='rmx220-spiral-envelope-captures', stage=args.stage,
        cases=cases, capture_script_sha256=sha256(Path(__file__))))


def checked_case(folder, case, expected):
    receipt, plan, controls, audio = checked(folder)
    _, source = float_wav(Path(receipt['input_path']))
    if (not np.array_equal(source, expected.astype(np.float32)) or plan['bpm'] != 120
            or plan['tail_seconds'] != case['tail']
            or receipt['maximum_block_size'] != case.get('block', 128)
            or round(controls['SceneVolume']*255) != 128 or controls['Sub1Volume'] != 0
            or controls.get(BUTTONS[case['direction']]) != 1):
        raise ValueError('Capture differs from envelope recipe: '+str(folder))
    return receipt, audio


def provenance(folder, receipt):
    return dict(receipt_sha256=sha256(folder/'receipt.json'), input_sha256=receipt['input_sha256'],
        output_sha256=receipt['output_sha256'], plan_sha256=receipt['plan_sha256'])


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves, cases = recipe(args.stage)
    result = []
    for case in cases:
        folder = args.session/case['name']
        receipt, _ = checked_case(folder, case, waves[case['source']])
        result.append(dict(case=case['name'], **provenance(folder, receipt)))
    save_json(args.report, dict(kind='rmx220-spiral-envelope-recipe-verification', stage=args.stage,
        script_sha256=sha256(Path(__file__)), reference_identity=IDENTITY, passed=True,
        scope='Exact inputs, static controls, capture hashes and timing only; no sonic certificate.', cases=result))
    print('Verified', len(result), args.stage, 'recipes')


def minimum(function, lower, upper):
    """Bounded scalar minimization using only NumPy and Python."""
    ratio = (np.sqrt(5)-1)/2
    x, y = upper-ratio*(upper-lower), lower+ratio*(upper-lower)
    fx, fy = function(x), function(y)
    for _ in range(90):
        if fx < fy:
            upper, y, fy = y, x, fx
            x = upper-ratio*(upper-lower)
            fx = function(x)
        else:
            lower, x, fx = x, y, fy
            y = lower+ratio*(upper-lower)
            fy = function(y)
    point, value = (x, fx) if fx < fy else (y, fy)
    return float(point), float(value)


def post_impulse(components, count=8192):
    impulse = np.zeros(count)
    impulse[0] = 1
    for pole in components['highpass_tail']['poles'][1:]:
        impulse = highpass(pole, impulse)
    impulse = filtered(*lowpass(12100, .7), impulse)
    impulse = highpass(components['highpass_tail']['poles'][0], impulse)
    return np.convolve(impulse, components['input_clip_model']['output_shape_fir'])[:count]


def identify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    components = json.loads(args.components.read_text())
    if (components['kind'] != 'rmx220-spiral-core-identification'
            or components['calibration_sha256'] != sha256(args.calibration)):
        raise ValueError('Requires the measured core components with the same bypass calibration')
    model = components['input_clip_model']
    beta = model['first_block_threshold_per_input_peak']
    impulse = post_impulse(components)
    results = []
    for stage in STAGES:
        session = getattr(args, stage.replace('-', '_'))
        waves, cases = recipe(stage)
        for case in cases:
            folder = session/case['name']
            receipt, audio = checked_case(folder, case, waves[case['source']])
            frame, direction = case['query_frame'], case['direction']
            query_amplitude = float(np.float32(waves[case['source']][frame, 1]))
            latency = 640 if direction == 'down' else 1792
            target = audio[32+frame+latency:32+frame+latency+2048, 1]
            if len(target) != 2048:
                raise ValueError('Incomplete first pass')
            gain = components['first_pass_output_scale'][direction]
            query = np.zeros(128)
            query[0] = query_amplitude
            source = filtered(*lowpass(model['lowpass_hz'], model['lowpass_Q']), query)
            if stage == 'stereo-reset':
                # The earlier right control is much smaller than the held
                # threshold and cannot yet have returned through the loop.
                # Subtract its known linear tail, without fitting another gain.
                control = np.zeros(128)
                control[0] = float(np.float32(waves[case['source']][case['reset_frame'], 1]))
                control = filtered(*lowpass(model['lowpass_hz'], model['lowpass_Q']), control)
                previous = gain*np.convolve(control, impulse)
                age = frame-case['reset_frame']
                target = target-previous[age:age+2048]
            if case['precondition'] == 'pulse':
                nominal = beta*case['initial_amplitude']
            elif case['precondition'] == 'tone':
                nominal = case['initial_amplitude']*.5
            else:
                nominal = case['initial_amplitude']*.5*(1-(1-ALPHA)**case['precondition_blocks'])

            def error(scale):
                limited = np.clip(source, -nominal*scale, nominal*scale)
                candidate = gain*np.convolve(limited, impulse)[:2048]
                return relative(target, candidate)

            scale, residual = minimum(error, .001, 3)
            result = dict(stage=stage, **case, query_amplitude=query_amplitude,
                fitted_threshold=nominal*scale, nominal_threshold=nominal,
                threshold_relative_to_nominal=scale, component_relative_rms_error=residual,
                **provenance(folder, receipt))
            if 'expected_threshold_relative' in case:
                result['prospective_prediction_passed'] = bool(abs(scale-case['expected_threshold_relative']) < 1e-6)
            results.append(result)
            print(stage, case['name'], f'threshold={scale:.9g}', f'error={residual:.3g}', flush=True)
    fits_passed = all(row['component_relative_rms_error'] < 1e-6 for row in results)
    predictions_passed = all(row.get('prospective_prediction_passed', True) for row in results)
    unit = np.zeros(128)
    unit[0] = 1
    unit = filtered(*lowpass(model['lowpass_hz'], model['lowpass_Q']), unit)
    peak = float(abs(np.convolve(unit, impulse)).max())
    lower, upper = 0., float('inf')
    boundaries = []
    for row in results:
        if row['stage'] not in ('reset', 'reset-small', 'reset-edge', 'reset-fine', 'reset-validation'):
            continue
        ratio = float(np.float32(row['reset_amplitude']))/float(np.float32(row['initial_amplitude']))
        boundary = peak*ratio/(2*beta)
        reset = bool(row['threshold_relative_to_nominal'] > .95)
        if reset:
            upper = min(upper, boundary)
        else:
            lower = max(lower, boundary)
        boundaries.append(dict(case=row['name'], boundary=boundary, reset=reset))
    bracket_passed = bool(np.isfinite(upper) and lower < upper)
    passed = fits_passed and predictions_passed and bracket_passed
    save_json(args.report, dict(kind='rmx220-spiral-envelope-first-pass-identification',
        reference_identity=IDENTITY, sample_rate=48000, full_spiral_match=False,
        physical_hardware=False, component_fits_passed=fits_passed,
        prospective_binary_gate_predictions_passed=predictions_passed,
        activity_gate_bracket=dict(consistent=bracket_passed, lower=lower, upper=upper,
            midpoint=(lower+upper)/2, linear_wet_peak_per_input=peak, boundaries=boundaries,
            scope='Candidate linked-wet-peak gate, expressed in the earlier envelope normalization. '
                  'Control tails are negligible in these isolated, unclipped reset probes.'),
        identifier_sha256=sha256(Path(__file__)), numpy_version=np.__version__,
        components_sha256=sha256(args.components), calibration_sha256=sha256(args.calibration),
        cases=results, component_fit_limit=1e-6,
        method='Fit one symmetric clipping threshold in the untouched right channel before its first repeat. '
               'Known fixed latency/filter/gain; no wet alignment search. Input LP truncated at 128 samples. '
               'Stereo-reset subtracts the earlier unclipped right control using its fixed linear response.',
        limitations=['First-pass threshold identification only; no full-render or hardware certificate.',
            'Tone/DC normalization is a model convention; pulse normalization uses the earlier first-block fit.',
            'Activity-reset criterion and exact arithmetic require independent complete-render checks.']))
    return 0 if passed else 1


def tail(args):
    """Identify early post-source thresholds before new tail feedback returns."""
    from tools.rmx_spiral_characterize import recipe as source_recipe

    calibration(args.calibration)
    root = new_directory(args.output)
    components = json.loads(args.components.read_text())
    if (components['kind'] != 'rmx220-spiral-core-identification'
            or components['calibration_sha256'] != sha256(args.calibration)):
        raise ValueError('Requires core components with the same calibration')
    impulse = post_impulse(components)
    expected = source_recipe('nonlinearity')[0]['square'].astype(np.float32)
    cases = []
    for index, folder in enumerate(args.case):
        receipt, plan, controls, audio = checked(folder)
        _, source = float_wav(Path(receipt['input_path']))
        if (not np.array_equal(source, expected) or plan['bpm'] != 120
                or plan['tail_seconds'] != 2 or controls['Sub1Volume'] != 0
                or round(controls['SceneVolume']*255) != 128):
            raise ValueError('Requires the exact factory stereo square recipe')
        direction = next(k for k, button in BUTTONS.items() if controls.get(button) == 1)
        output, trace = root/f'{index:02d}-candidate.wav', root/f'{index:02d}-trace'
        run([args.renderer, receipt['input_path'], output, direction, 0, 2, trace])
        pre_rate, pre = float_wav(trace/'pre.wav')
        limited_rate, limited = float_wav(trace/'limited.wav')
        if pre_rate != 48000 or limited_rate != 48000 or pre.shape != limited.shape:
            raise ValueError('Wrong diagnostic trace format')
        pre, limited = pre.astype(float), limited.astype(float)
        start = 96000
        delay = next(row['delay_floor_frames'] for row in components['linear_loop']
                     if row['direction'] == direction)
        stop = start+(delay//32)*32
        latency = 640 if direction == 'down' else 1792
        if min(len(pre), len(audio)-32-latency) < stop:
            raise ValueError('Traces or reference are incomplete')
        nominal = float(abs(limited[start-32:start]).max())
        if nominal <= 0:
            raise ValueError('No nonzero preceding threshold')
        # Flatten the candidate's entire post-source threshold to the preceding
        # level. The fitted release cannot simply inherit the renderer's curve.
        limited[start:] = np.clip(pre[start:], -nominal, nominal)
        size = 1 << (len(limited)+len(impulse)-2).bit_length()
        spectrum = np.fft.rfft(limited, n=size, axis=0)*np.fft.rfft(impulse, n=size)[:, None]
        predicted = np.fft.irfft(spectrum, n=size, axis=0)[:len(limited)]
        reference = audio[32:].copy()
        count = min(len(source), len(reference))
        reference[:count] -= source[:count]
        reference = reference[latency:]/components['first_pass_output_scale'][direction]
        correction = np.zeros((len(limited)+len(impulse), 2))
        rows, events = [], []
        previous = 1.
        for frame in range(start, stop, 32):
            target = reference[frame:frame+32]
            base = predicted[frame:frame+32]+correction[frame:frame+32]
            incoming, before = pre[frame:frame+32], limited[frame:frame+32]

            def error(scale):
                delta = np.clip(incoming, -nominal*scale, nominal*scale)-before
                change = np.column_stack([np.convolve(delta[:, ch], impulse[:32])[:32]
                                          for ch in range(2)])
                return relative(target, base+change)

            scale, residual = minimum(error, .4, 1.2)
            delta = np.clip(incoming, -nominal*scale, nominal*scale)-before
            future = np.column_stack([np.convolve(delta[:, ch], impulse) for ch in range(2)])
            correction[frame:frame+len(future)] += future
            identifiable = float(abs(incoming).max()) > nominal*1.2
            rows.append(dict(frame=frame, threshold_relative_to_preceding=scale,
                component_relative_rms_error=residual, identifiable=identifiable))
            if abs(np.log(scale/previous)) > .01:
                events.append(dict(frame=frame, threshold_relative_to_preceding=scale,
                                   step_db=float(20*np.log10(scale/previous))))
            previous = scale
        cases.append(dict(case=folder.name, direction=direction, **provenance(folder, receipt),
            candidate_sha256=sha256(output), pre_trace_sha256=sha256(trace/'pre.wav'),
            limited_trace_sha256=sha256(trace/'limited.wav'), nominal_threshold=nominal,
            first_new_feedback_frame=start+delay, threshold_events=events, windows=rows))
        print(direction, 'tail threshold events:', [(e['frame'], round(e['step_db'], 5)) for e in events])
    passed = bool(cases) and all(row['identifiable'] and row['component_relative_rms_error'] < 1e-4
                                for case in cases for row in case['windows'])
    save_json(root/'tail.json', dict(kind='rmx220-spiral-early-tail-threshold-identification',
        sample_rate=48000, reference_identity=IDENTITY, full_spiral_match=False,
        physical_hardware=False, component_fits_passed=passed, cases=cases,
        identifier_sha256=sha256(Path(__file__)), renderer_sha256=sha256(args.renderer),
        calibration_sha256=sha256(args.calibration), components_sha256=sha256(args.components),
        method='Fit a common stereo threshold every 32 frames using the fixed post-clip response. '
               'The baseline release is flattened; only windows before new post-source feedback returns are fitted.',
        limitations=['Candidate pre-feedback state is inferred from the preceding saturated source.',
            'Diagnostic traces are float32. These fits do not establish later nonlinear tails or complete fidelity.']))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    p.add_argument('--stage', choices=STAGES, required=True)
    for name in ('host', 'plugin', 'session'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('verify')
    p.add_argument('--stage', choices=STAGES, required=True)
    for name in ('session', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('identify')
    for name in (*STAGES, 'calibration', 'components', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('tail')
    p.add_argument('--case', type=Path, action='append', required=True)
    for name in ('calibration', 'components', 'renderer', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = {'capture': capture, 'verify': verify, 'identify': identify, 'tail': tail}[args.command](args)
    raise SystemExit(result or 0)


if __name__ == '__main__':
    main()
