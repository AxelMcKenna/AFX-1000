#!/usr/bin/env python3
"""Audit Spiral sensitivity and local recurrence without relaxing full-render gates."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_spiral_characterize import recipe as character_recipe
from tools.rmx_spiral_core import calibration, filtered, lowpass, relative
from tools.rmx_spiral_envelope import ALPHA, minimum, post_impulse
from tools.rmx_spiral_return import BUTTONS, checked


STAGES = ('sensitivity', 'collisions', 'reset-refinement', 'quiet-up')


def recipe(stage):
    waves, cases = {}, []

    def add(name, samples, direction, tail, **metadata):
        waves[name] = samples
        cases.append(dict(name=direction+'-'+name, source=name, direction=direction,
                          tail=tail, **metadata))

    if stage == 'sensitivity':
        x = character_recipe('initial')[0]['impulses'].astype(np.float32)
        for name, destination in (('repeat', None), ('ulp-up', np.float32(np.inf)),
                                   ('ulp-down', np.float32(-np.inf))):
            y = x.copy()
            if destination is not None:
                y[48000, 0] = np.nextafter(y[48000, 0], destination, dtype=np.float32)
            add(name, y, 'up', 12, pulse_amplitude=float(y[48000, 0]))
    elif stage == 'collisions':
        for blocks in (60, 61, 62, 63, 65, 66, 67, 68):
            frame = 48000+blocks*32
            amplitude = 8*.01*(1-(1-ALPHA)**blocks)
            x = np.zeros((240000, 2))
            x[48000:frame, 0], x[frame, 1] = .01, amplitude
            add(f'blocks-{blocks}', x, 'down', 1, query_frame=frame, precondition_blocks=blocks)
    elif stage == 'reset-refinement':
        for ratio in (3.885e-5, 3.89e-5, 3.895e-5, 3.8975e-5):
            x = np.zeros((144000, 2))
            x[48000, 0], x[51840, 0], x[54720, 1] = .05, .05*ratio, .002
            add(f'ratio-{ratio}', x, 'down', 1, reset_ratio=ratio)
    elif stage == 'quiet-up':
        for amplitude in (0, 1e-16, 1e-24):
            x = np.zeros((384000, 2))
            x[24000:360000, 1], x[48000, 0] = .2, amplitude
            add(f'quiet-{amplitude}', x, 'up', 1, pulse_amplitude=amplitude)
    else:
        raise ValueError('Unknown stage: '+stage)
    return waves, cases


def capture(args):
    if args.predictor and args.stage != 'collisions':
        raise ValueError('Forecasting supports only the collision recipe')
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    waves, cases = recipe(args.stage)
    for name, wave in waves.items():
        write_wav(root/(name+'.wav'), 48000, wave.ravel())
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
        forecasts = []
        if args.predictor:
            for index, renderer in enumerate(args.predictor):
                output, trace = root/f'{case["name"]}-forecast-{index}.wav', root/f'{case["name"]}-trace-{index}'
                run([renderer, root/(case['source']+'.wav'), output, 'down', 0, 1, trace])
                _, limited = float_wav(trace/'limited.wav')
                frame = case['query_frame']
                before = float(abs(limited[frame:frame+32, 1]).max())
                after = float(abs(limited[frame+12144:frame+12144+32, 1]).max())
                if before <= 0:
                    raise ValueError('Forecast needs a nonzero clipped right query')
                forecasts.append(dict(model=renderer.name, renderer_sha256=sha256(renderer),
                                      first_return_threshold_ratio=after/before))
            save_json(root/(case['name']+'-predictions.json'), dict(
                input_sha256=sha256(root/(case['source']+'.wav')), predictions=forecasts,
                before_reference_capture=True))
        run([args.host, 'render', args.plugin, root/(case['source']+'.wav'),
             root/(case['name']+'.json'), root/case['name'], 128])
        print(case['name'], flush=True)
    save_json(root/'matrix.json', dict(kind='rmx220-spiral-robustness-captures', stage=args.stage,
        cases=cases, capture_script_sha256=sha256(Path(__file__))))


def read_case(session, case, expected):
    folder = session/case['name']
    receipt, plan, controls, audio = checked(folder)
    _, source = float_wav(Path(receipt['input_path']))
    if (not np.array_equal(source, expected.astype(np.float32)) or plan['bpm'] != 120
            or plan['tail_seconds'] != case['tail'] or receipt['maximum_block_size'] != 128
            or round(controls['SceneVolume']*255) != 128 or controls['Sub1Volume'] != 0
            or controls.get(BUTTONS[case['direction']]) != 1):
        raise ValueError('Outside robustness recipe: '+str(folder))
    provenance = dict(case=case['name'], receipt_sha256=sha256(folder/'receipt.json'),
        input_sha256=receipt['input_sha256'], output_sha256=receipt['output_sha256'],
        plan_sha256=receipt['plan_sha256'])
    return receipt, audio, source, provenance


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves, cases = recipe(args.stage)
    results = [read_case(args.session, case, waves[case['source']])[3] for case in cases]
    save_json(args.report, dict(kind='rmx220-spiral-robustness-recipe-verification', stage=args.stage,
        script_sha256=sha256(Path(__file__)), reference_identity=IDENTITY, cases=results,
        passed=True, scope='Exact inputs, static controls and capture hashes only.'))
    print('Verified', len(results), args.stage, 'recipes')


def wet(audio, source):
    result = audio[32:].copy()
    count = min(len(source), len(result))
    result[:count] -= source[:count]
    return result


def sensitivity(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    waves, cases = recipe('sensitivity')
    records = [read_case(args.session, case, waves[case['source']]) for case in cases]
    baseline = wet(records[0][1], records[0][2])
    comparisons = []
    for case, (_, audio, source, provenance) in zip(cases, records):
        signal = wet(audio, source)
        if len(signal) != len(baseline):
            raise ValueError('Mismatched capture length')
        windows = []
        for second in (1, 3, 4, 5, 6, 8, 10, 12, 14):
            window = slice(second*48000, (second+1)*48000)
            windows.append(dict(start_seconds=second, measurement=screen(baseline[window], signal[window])))
        delta = case['pulse_amplitude']-cases[0]['pulse_amplitude']
        comparisons.append(dict(**provenance, input_sample_delta=delta,
            input_pulse_relative_delta=delta/cases[0]['pulse_amplitude'], windows=windows))
    original, reference_audio, _, _ = read_case(args.baseline.parent,
        cases[0] | {'name': args.baseline.name}, waves[cases[0]['source']])
    repeat_exact = records[0][0]['output_sha256'] == original['output_sha256']
    if not np.array_equal(reference_audio, records[0][1]):
        raise ValueError('Identical-input reference repeat is not bit-exact')
    save_json(args.report, dict(kind='rmx220-spiral-original-input-sensitivity', sample_rate=48000,
        reference_identity=IDENTITY, identifier_sha256=sha256(Path(__file__)),
        calibration_sha256=sha256(args.calibration), same_input_repeat_bit_exact=repeat_exact,
        earlier_reference_receipt_sha256=sha256(args.baseline/'receipt.json'), comparisons=comparisons,
        full_spiral_match=False, physical_hardware=False, acceptance_criteria_changed=False,
        limitations=['Original-versus-original perturbation audit; no clone similarity certificate.',
            'Waveform sensitivity alone does not establish perceptual similarity or authorize a changed acceptance gate.']))
    print('Recorded original-only sensitivity; acceptance criteria remain unchanged')


def collisions(args):
    calibration(args.calibration)
    root = new_directory(args.output)
    components = json.loads(args.components.read_text())
    if components['calibration_sha256'] != sha256(args.calibration):
        raise ValueError('Component calibration differs')
    impulse = post_impulse(components)
    waves, cases = recipe('collisions')
    results = []
    for index, case in enumerate(cases):
        receipt, audio, source, provenance = read_case(args.session, case, waves[case['source']])
        output, trace = root/f'{index:02d}-candidate.wav', root/f'{index:02d}-trace'
        run([args.renderer, receipt['input_path'], output, 'down', 0, 1, trace])
        _, incoming = float_wav(trace/'pre.wav')
        _, limited = float_wav(trace/'limited.wav')
        frame = case['query_frame']
        nominal = float(abs(limited[frame:frame+32, 1]).max())
        query = np.zeros(128)
        query[0] = source[frame, 1]
        query = filtered(*lowpass(12000, .707), query)
        first = audio[32+frame+640:32+frame+640+2048, 1]
        scale, initial_error = minimum(lambda s: relative(first, np.convolve(
            np.clip(query, -nominal*s, nominal*s), impulse)[:2048]), .5, 1.5)
        nominal *= scale
        start = frame+12144
        target = audio[32+start+640:32+start+640+2048, 1]
        values = incoming[start:start+2048, 1].astype(float)
        ratio, error = minimum(lambda s: relative(target, np.convolve(
            np.clip(values, -nominal*s, nominal*s), impulse)[:2048]), .4, 1.2)
        forecasts = json.loads((args.session/(case['name']+'-predictions.json')).read_text())
        if forecasts['input_sha256'] != receipt['input_sha256'] or not forecasts['before_reference_capture']:
            raise ValueError('Forecast provenance differs')
        results.append(dict(**provenance, first_pass_fit_error=initial_error,
            first_return_fit_error=error, measured_threshold_ratio=ratio,
            candidate_sha256=sha256(output), pre_trace_sha256=sha256(trace/'pre.wav'),
            forecasts_sha256=sha256(args.session/(case['name']+'-predictions.json')),
            predictions=[p | {'matched': abs(p['first_return_threshold_ratio']-ratio) < 1e-4}
                         for p in forecasts['predictions']]))
    save_json(root/'collisions.json', dict(kind='rmx220-spiral-release-collision-audit', cases=results,
        sample_rate=48000, full_spiral_match=False, physical_hardware=False,
        identifier_sha256=sha256(Path(__file__)), renderer_sha256=sha256(args.renderer),
        components_sha256=sha256(args.components), calibration_sha256=sha256(args.calibration),
        limitations=['Only the first isolated right repeat is identified.',
            'Candidate incoming state is conditioned on the preceding right query; whole-tail agreement is separate.']))
    print('Recorded collision fits and preserved unsuccessful prospective predictions')


def quiet(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    waves, cases = recipe('quiet-up')
    records = [read_case(args.session, case, waves[case['source']]) for case in cases]
    zero = records[0][1][32:, 0]
    baseline_zero = bool(np.count_nonzero(zero) == 0)
    small = wet(records[2][1], records[2][2])[:, 0]
    large = wet(records[1][1], records[1][2])[:, 0]
    low = float(records[2][2][48000, 0])
    high = float(records[1][2][48000, 0])
    windows = []
    for second in (1, 2, 3, 4):
        window = slice(second*48000, (second+1)*48000)
        windows.append(dict(start_seconds=second,
            amplitude_normalized_relative_rms_error=relative(small[window]/low, large[window]/high)))
    save_json(args.report, dict(kind='rmx220-spiral-quiet-up-scaling', sample_rate=48000,
        reference_identity=IDENTITY, identifier_sha256=sha256(Path(__file__)),
        calibration_sha256=sha256(args.calibration), sources=[r[3] for r in records],
        silent_left_baseline_bit_zero=baseline_zero, input_amplitudes=[low, high], windows=windows,
        full_spiral_match=False, physical_hardware=False,
        limitations=['Only the left quiet response, before clipping of the larger input, is compared.',
            'Both signals use their known input amplitude; no fitted candidate gain or wet alignment.',
            'The right DC diagnostic channel and the later saturated output are excluded.']))
    print('Recorded quiet original scaling; no full-effect claim')


def refinement(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    components = json.loads(args.components.read_text())
    previous = json.loads(args.previous.read_text())
    if (components['calibration_sha256'] != sha256(args.calibration)
            or previous['components_sha256'] != sha256(args.components)):
        raise ValueError('Prior measurement/calibration differs')
    impulse = post_impulse(components)
    model = components['input_clip_model']
    beta = model['first_block_threshold_per_input_peak']
    query = np.zeros(128)
    query[0] = .002
    query = filtered(*lowpass(model['lowpass_hz'], model['lowpass_Q']), query)
    unit = np.zeros(128)
    unit[0] = 1
    unit = filtered(*lowpass(model['lowpass_hz'], model['lowpass_Q']), unit)
    peak = float(abs(np.convolve(unit, impulse)).max())
    lower, upper = previous['activity_gate_bracket']['lower'], previous['activity_gate_bracket']['upper']
    waves, cases = recipe('reset-refinement')
    results = []
    for case in cases:
        _, audio, source, provenance = read_case(args.session, case, waves[case['source']])
        target = audio[32+54720+640:32+54720+640+2048, 1]
        scale, error = minimum(lambda s: relative(target, np.convolve(
            np.clip(query, -beta*.05*s, beta*.05*s), impulse)[:2048]), .5, 1.1)
        boundary = peak*float(source[51840, 0])/float(source[48000, 0])/(2*beta)
        reset = bool(scale > .95)
        if reset:
            upper = min(upper, boundary)
        else:
            lower = max(lower, boundary)
        results.append(dict(**provenance, reset_ratio=case['reset_ratio'],
            threshold_relative_to_initial=scale, component_relative_rms_error=error,
            reset=reset, activity_gate_boundary=boundary))
    save_json(args.report, dict(kind='rmx220-spiral-activity-gate-refinement',
        sample_rate=48000, reference_identity=IDENTITY, full_spiral_match=False,
        physical_hardware=False, cases=results, gate_lower=lower, gate_upper=upper,
        gate_midpoint=(lower+upper)/2, bracket_consistent=bool(lower < upper),
        identifier_sha256=sha256(Path(__file__)), components_sha256=sha256(args.components),
        previous_measurement_sha256=sha256(args.previous), calibration_sha256=sha256(args.calibration),
        limitations=['An empirical gate in the existing envelope/output normalization.',
            'The narrower isolated-control bracket does not establish feedback activity timing or full fidelity.']))
    print('Recorded narrower activity bracket', lower, upper)


def recurrence(args):
    calibration(args.calibration)
    root = new_directory(args.output)
    receipt, plan, controls, audio = checked(args.case)
    _, source = float_wav(Path(receipt['input_path']))
    expected = character_recipe('initial')[0]['impulses'].astype(np.float32)
    if (not np.array_equal(source, expected) or controls.get(BUTTONS['up']) != 1
            or round(controls['SceneVolume']*255) != 128 or controls['Sub1Volume'] != 0
            or plan['bpm'] != 120 or plan['tail_seconds'] != 12):
        raise ValueError('Requires the static Up stereo impulse recipe, with no outer return')
    components = json.loads(args.components.read_text())
    if components['calibration_sha256'] != sha256(args.calibration):
        raise ValueError('Component calibration differs')
    output, trace = root/'candidate.wav', root/'trace'
    run([args.renderer, receipt['input_path'], output, 'up', 0, 12, trace])
    _, candidate = float_wav(output)
    _, actual_limited = float_wav(trace/'limited.wav')
    reference = wet(audio, source)
    candidate = candidate[:len(reference)].astype(float)
    whole_screen = screen(audio[32:], candidate)
    candidate_wet = candidate.copy()
    candidate_wet[:min(len(source), len(candidate))] -= source[:min(len(source), len(candidate))]
    wet_screen = screen(reference, candidate_wet)
    reference, candidate_wet = reference[1792:], candidate_wet[1792:]
    actual_limited = actual_limited[:len(reference)].astype(float)
    h = post_impulse(components, 65536)*components['first_pass_output_scale']['up']
    nfft = 1 << (len(reference)+len(h)-2).bit_length()
    spectrum = np.fft.rfft(h, nfft)
    unit = np.zeros(8192)
    unit[0] = 1
    loop = unit
    from tools.rmx_spiral_core import highpass
    for pole in components['highpass_tail']['poles'][1:]:
        loop = highpass(pole, loop)
    loop = filtered(*lowpass(12100, .7), loop)
    loop_spectrum = np.fft.rfft(loop, nfft)
    source_impulse = filtered(*lowpass(12000, .707), unit[:256])
    source_padded = np.zeros_like(reference)
    source_padded[:len(source)] = source
    source_filtered = np.fft.irfft(np.fft.rfft(source_padded, n=nfft, axis=0)
        * np.fft.rfft(source_impulse, nfft)[:, None], n=nfft, axis=0)[:len(reference)]
    frames = np.arange(len(reference))
    phase = 2.086162567138672e-6*((frames//32)*32-64)
    fraction = (1-abs((phase+1) % 4-2)) % 1
    position = frames-2496-fraction
    indices = np.floor(position).astype(int)
    weights = (position-indices).astype(np.float32)
    valid = indices >= 0
    indices = np.maximum(indices, 0)
    threshold = float(abs(actual_limited[48000:48032]).max())
    results, negatives = [], []

    def synthesize(tap, gain):
        predicted_input = np.clip(source_filtered+gain*tap, -threshold, threshold)
        return np.fft.irfft(np.fft.rfft(predicted_input, n=nfft, axis=0)
            * spectrum[:, None], n=nfft, axis=0)[:len(reference)]

    for regularizer in (1e-8, 1e-10, 1e-12):
        for name, signal in (('original', reference), ('candidate-control', candidate_wet)):
            reconstructed = np.fft.irfft(np.fft.rfft(signal, n=nfft, axis=0)
                * spectrum.conj()[:, None]/(abs(spectrum[:, None])**2+regularizer),
                n=nfft, axis=0)[:len(reference)]
            filtered_state = np.fft.irfft(np.fft.rfft(reconstructed, n=nfft, axis=0)
                * loop_spectrum[:, None], n=nfft, axis=0)[:len(reference)].astype(np.float32)
            tap = filtered_state[indices]*(1-weights[:, None])
            tap += filtered_state[np.minimum(indices+1, len(filtered_state)-1)]*weights[:, None]
            tap[~valid] = 0
            predicted = synthesize(tap, 1.5)
            windows = []
            for second in (4, 6, 8, 10, 12, 14):
                window = slice(second*48000, (second+1)*48000)
                bins = np.linspace(.5, 2, 1501)
                modes = []
                for ch in range(2):
                    histogram, _ = np.histogram(abs(reconstructed[window, ch])/threshold, bins)
                    at = int(np.argmax(histogram))
                    modes.append(float((bins[at]+bins[at+1])/2))
                windows.append(dict(start_seconds=second,
                    relative_rms_error=[relative(signal[window, ch], predicted[window, ch]) for ch in range(2)],
                    reconstructed_clipping_mode_relative_to_candidate=modes,
                    candidate_actual_peak_relative_to_initial=[
                        float(abs(actual_limited[window, ch]).max()/threshold) for ch in range(2)]))
            results.append(dict(signal=name, regularization=regularizer, windows=windows))
            if name == 'original' and regularizer == 1e-12:
                shifted_position = position-1
                shifted_indices = np.floor(shifted_position).astype(int)
                shifted_weights = (shifted_position-shifted_indices).astype(np.float32)
                shifted_valid = shifted_indices >= 0
                shifted_indices = np.maximum(shifted_indices, 0)
                shifted = filtered_state[shifted_indices]*(1-shifted_weights[:, None])
                shifted += filtered_state[np.minimum(shifted_indices+1, len(filtered_state)-1)]*shifted_weights[:, None]
                shifted[~shifted_valid] = 0
                for label, altered in (('one-extra-delay-frame', synthesize(shifted, 1.5)),
                                       ('ten-percent-less-loop-gain', synthesize(tap, 1.35))):
                    window = slice(8*48000, 9*48000)
                    negatives.append(dict(change=label, start_seconds=8,
                        relative_rms_error=[relative(reference[window, ch], altered[window, ch])
                                            for ch in range(2)]))
    save_json(root/'recurrence.json', dict(kind='rmx220-spiral-conditioned-recurrence-audit',
        reference_identity=IDENTITY, sample_rate=48000, full_spiral_match=False,
        physical_hardware=False, autonomous_whole=whole_screen, autonomous_wet=wet_screen,
        acceptance_criteria_changed=False, results=results, negative_controls=negatives,
        candidate_threshold=threshold,
        identifier_sha256=sha256(Path(__file__)), renderer_sha256=sha256(args.renderer),
        components_sha256=sha256(args.components), calibration_sha256=sha256(args.calibration),
        reference_receipt_sha256=sha256(args.case/'receipt.json'), candidate_sha256=sha256(output),
        limited_trace_sha256=sha256(trace/'limited.wav'),
        limitations=['Recovered original state is supplied to the candidate recurrence; this is not autonomous cloning.',
            'Regularized inversion is checked against the known candidate state and carries reconstruction error.',
            'Small conditioned errors do not replace the failed complete-render waveform screen.']))
    print('Recorded conditioned recurrence; autonomous waveform failure remains explicit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('capture')
    p.add_argument('--stage', choices=STAGES, required=True)
    p.add_argument('--predictor', type=Path, action='append', default=[])
    for name in ('host', 'plugin', 'session'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('verify')
    p.add_argument('--stage', choices=STAGES, required=True)
    for name in ('session', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('sensitivity')
    for name in ('session', 'baseline', 'calibration', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('collisions')
    for name in ('session', 'components', 'renderer', 'calibration', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('quiet')
    for name in ('session', 'calibration', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('refinement')
    for name in ('session', 'previous', 'components', 'calibration', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('recurrence')
    for name in ('case', 'components', 'renderer', 'calibration', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    {'capture': capture, 'verify': verify, 'sensitivity': sensitivity,
     'collisions': collisions, 'quiet': quiet, 'refinement': refinement,
     'recurrence': recurrence}[args.command](args)


if __name__ == '__main__':
    main()
