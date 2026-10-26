#!/usr/bin/env python3
"""Capture and diagnose factory Reverb; component fits do not certify a clone."""
import argparse
import datetime
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, probe, run
from tools.rmx_filter_match import screen
from tools.rmx_spiral_core import calibration

BUTTONS = {'up': 'ReverbUpButton', 'down': 'ReverbDownButto'}
STAGES = ('initial', 'timing', 'long-tail', 'filters')


def recipe(stage='initial'):
    waves = {}
    for name, left, right, offset in (
            ('left', .02, 0, 0), ('low', .002, 0, 0), ('high', .2, 0, 0),
            ('right', 0, .02, 0), ('same', .02, .02, 0),
            ('opposite', .02, -.02, 0), ('shifted', .02, 0, 512), ('silence', 0, 0, 0)):
        x = np.zeros((96000, 2))
        x[48000+offset] = [left, right]
        waves[name] = x
    waves['probe'] = probe()
    cases = []
    for direction in BUTTONS:
        def add(name, source='left', main=128, amount=128, cutoff=0):
            cases.append(dict(name=direction+'-'+name, source=source, direction=direction,
                main=main, amount=amount, cutoff=cutoff, tail=12 if source == 'probe' else 18))
        if stage == 'timing':
            for raw in (16, 48, 80, 112, 144, 176, 208, 240):
                add(f'main-{raw}', main=raw)
                cases[-1]['tail'] = 3
            continue
        if stage == 'long-tail':
            for raw in (192, 255):
                add(f'amount-{raw}', amount=raw)
                cases[-1]['tail'] = 90
            continue
        if stage == 'filters':
            for raw in (32,96,160,224):
                add(f'cutoff-{raw}',cutoff=raw)
            for raw in (96,224):
                add(f'probe-cutoff-{raw}',source='probe',cutoff=raw)
            continue
        if stage != 'initial':
            raise ValueError('Unknown recipe stage')
        for raw in (0, 32, 64, 96, 128, 160, 192, 224, 255):
            add(f'main-{raw}', main=raw)
        for raw in (0, 32, 64, 96, 192, 255):
            add(f'amount-{raw}', amount=raw)
        for raw in (64, 128, 192, 255):
            add(f'cutoff-{raw}', cutoff=raw)
        for source in ('left', 'low', 'high', 'right', 'same', 'opposite', 'shifted', 'silence', 'probe'):
            add('source-'+source, source)
    return waves, cases


def controls(case):
    return {'AutoButton': 1, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
        'IsolatorButton': 0, 'DefaultSwitch': 1, 'UserSwitch': 0,
        'SceneVolume': case['main']/255, 'Sub1Volume': case['amount']/255,
        'Sub2Volume': case['cutoff']/255, BUTTONS[case['direction']]: 1}


def capture(args):
    if args.stage in ('timing','filters') and args.prediction is None:
        raise ValueError('Timing/filter capture requires saved prospective predictions')
    if args.stage not in ('timing','filters') and args.prediction is not None:
        raise ValueError('Predictions apply only to timing/filter stages')
    prediction = json.loads(args.prediction.read_text()) if args.prediction else None
    expected_kind={'timing':'rmx220-reverb-onset-predictions','filters':'rmx220-reverb-output-filter-model'}
    if prediction is not None and prediction.get('kind') != expected_kind[args.stage]:
        raise ValueError('Wrong prediction type')
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json', inventory)
    waves, cases = recipe(args.stage)
    for name, audio in waves.items():
        write_wav(root/(name+'.wav'), 48000, audio.ravel())
    for case in cases:
        parameters = []
        for name, value in controls(case).items():
            matches = [p for p in inventory['parameters'] if p['name'] == name]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous control: '+name)
            parameters.append({k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value})
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference',
            expected_plugin=IDENTITY, sample_rate=48000, bpm=120, tail_seconds=case['tail'],
            parameters=parameters, events=[])
        save_json(root/(case['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/(case['source']+'.wav'),
             root/(case['name']+'.json'), root/case['name'], 128])
        case['receipt_sha256'] = sha256(root/case['name']/'receipt.json')
        print(case['name'], flush=True)
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-identification-captures',
        stage=args.stage, sample_rate=48000, cases=cases, capture_script_sha256=sha256(Path(__file__)),
        prospective_prediction_sha256=sha256(args.prediction) if args.prediction else None))


def checked(session, case, expected):
    folder = session/case['name']
    receipt = json.loads((folder/'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role'] != 'reference'
            or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
        raise ValueError('Wrong reference: '+str(folder))
    for path, key in ((folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                       (Path(receipt['input_path']), 'input_sha256')):
        if sha256(path) != receipt[key]:
            raise ValueError('Modified reference: '+str(path))
    plan = json.loads((folder/'plan.json').read_text())
    actual = {p['name']: p['value'] for p in plan['parameters']}
    if (plan['sample_rate'] != 48000 or plan['bpm'] != 120 or plan['events']
            or plan['tail_seconds'] != case['tail'] or receipt['maximum_block_size'] != 128
            or actual != controls(case)):
        raise ValueError('Outside exact static factory Reverb recipe: '+str(folder))
    rate, audio = float_wav(folder/'audio.wav')
    source_rate, source = float_wav(Path(receipt['input_path']))
    if (rate != 48000 or source_rate != rate or not np.array_equal(source, expected.astype(np.float32))
            or len(audio) != len(source)+case['tail']*48000):
        raise ValueError('Source/rate/extent differs: '+str(folder))
    matrix = json.loads((session/'matrix.json').read_text())
    stored = next(x for x in matrix['cases'] if x['name'] == case['name'])
    if stored['receipt_sha256'] != sha256(folder/'receipt.json'):
        raise ValueError('Receipt differs from capture manifest')
    provenance = dict(case=case['name'], receipt_sha256=sha256(folder/'receipt.json'),
        input_sha256=receipt['input_sha256'], output_sha256=receipt['output_sha256'],
        plan_sha256=receipt['plan_sha256'])
    return receipt, audio[32:].astype(float), source, provenance


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves, cases = recipe(args.stage)
    result = [checked(args.session, case, waves[case['source']])[3] for case in cases]
    save_json(args.report, dict(kind='rmx220-reverb-recipe-verification', passed=True, stage=args.stage,
        reference_identity=IDENTITY, cases=result, script_sha256=sha256(Path(__file__)),
        scope='Exact captured samples, controls, extent and hashes; no sonic matching claim.'))
    print('Verified', len(result), 'Reverb captures')


def relative(a, b):
    energy = float(np.sum(a*a))
    return float(np.linalg.norm(a-b)/np.sqrt(energy)) if energy > 1e-30 else None


def fit_scale(a, b):
    energy = float(np.sum(b*b))
    gain = float(np.sum(a*b)/energy) if energy > 1e-30 else 0.
    return dict(diagnostic_gain=gain, relative_rms_error=relative(a, b*gain),
                acceptance_gain_fit=False)


def decay(signal):
    power = np.sum(signal*signal, axis=1)
    energy = np.cumsum(power[::-1])[::-1]
    if not len(energy) or energy[0] <= 1e-30:
        return dict(total_energy=float(energy[0]) if len(energy) else 0., fits=[])
    db = 10*np.log10(np.maximum(energy/energy[0], 1e-300))
    fits = []
    # Decimate only the fit coordinates; integrate every sample above.
    t = np.arange(0, len(db), 48)/48000
    y = db[::48]
    for lower in (-25, -35):
        keep = (y <= -5) & (y >= lower)
        if np.count_nonzero(keep) < 20:
            continue
        slope, intercept = np.polyfit(t[keep], y[keep], 1)
        residual = float(np.sum((y[keep]-(slope*t[keep]+intercept))**2))
        variance = float(np.sum((y[keep]-y[keep].mean())**2))
        fits.append(dict(range_db=[-5, lower], t60_seconds=float(-60/slope),
            slope_db_per_second=float(slope), r_squared=1-residual/variance,
            start_seconds=float(t[keep][0]), end_seconds=float(t[keep][-1])))
    return dict(total_energy=float(energy[0]), fits=fits,
        final_half_second_energy_fraction=float(np.sum(power[-24000:])/energy[0]),
        limitation='Finite-window Schroeder integration; no noise-floor subtraction or hardware-room inference.')


def residual(audio, source, gain):
    y = audio.copy()
    n = min(len(y), len(source))
    y[:n] -= source[:n]*gain
    return y


def analyze(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    waves, cases = recipe('initial')
    records = {c['name']: checked(args.session, c, waves[c['source']]) for c in cases}
    findings = {}
    for direction in BUTTONS:
        rows = [c for c in cases if c['direction'] == direction]
        _, baseline, source, _ = records[direction+'-main-128']
        amplitude = float(source[48000, 0])
        direct = float(baseline[48000, 0]/amplitude)
        base = residual(baseline, source, direct)
        diagnostics = dict(instantaneous_input_coefficient=direct,
            coefficient_limitation='Sample at the input impulse; zero-delay wet cannot be excluded by this coefficient alone.',
            cases=[], repeatability={}, linearity=[], stereo_superposition=[], macro_shapes=[], amount_shapes=[])
        for case in rows:
            _, audio, x, provenance = records[case['name']]
            row = dict(**provenance, main_raw=case['main'], amount_raw=case['amount'], cutoff_raw=case['cutoff'])
            if case['source'] == 'left':
                coefficient = float(audio[48000, 0]/amplitude)
                wet = residual(audio, x, coefficient)[48000:]
                onset = []
                for ch in range(2):
                    values = np.flatnonzero(abs(wet[:, ch]) > max(1e-15, float(abs(wet[:, ch]).max())*1e-7))
                    onset.append(int(values[0]) if len(values) else None)
                row |= dict(instantaneous_input_coefficient=coefficient,
                    residual_onset_frames=onset, residual_decay=decay(wet),
                    residual_channel_energy=np.sum(wet*wet, axis=0).tolist())
                if '-main-' in case['name'] or '-amount-' in case['name']:
                    fitted = fit_scale(wet, base[48000:])
                    entry = dict(case=case['name'], **fitted)
                    diagnostics['macro_shapes' if '-main-' in case['name'] else 'amount_shapes'].append(entry)
            diagnostics['cases'].append(row)
        repeat = records[direction+'-source-left']
        diagnostics['repeatability'] = dict(bit_exact=bool(np.array_equal(baseline, repeat[1])),
            relative_rms_error=relative(baseline, repeat[1]))
        for kind in ('low','high'):
            _, audio, x, _ = records[direction+'-source-'+kind]
            ratio = float(x[48000,0])/amplitude
            diagnostics['linearity'].append(dict(source=kind, known_input_ratio=ratio,
                whole_relative_rms_error=relative(baseline, audio/ratio),
                residual_relative_rms_error=relative(base, residual(audio,x,direct)/ratio)))
        right = records[direction+'-source-right'][1]
        for kind, sign in (('same',1),('opposite',-1)):
            target = records[direction+'-source-'+kind][1]
            diagnostics['stereo_superposition'].append(dict(source=kind,
                whole_relative_rms_error=relative(target, baseline+sign*right),
                post_input_tail_relative_rms_error=relative(target[96000:], (baseline+sign*right)[96000:])))
        shifted = records[direction+'-source-shifted'][1]
        diagnostics['shift_512_frames'] = dict(relative_rms_error=relative(baseline[:-512],shifted[512:]))
        silent = records[direction+'-source-silence'][1]
        diagnostics['silence'] = dict(bit_zero=bool(np.count_nonzero(silent)==0),peak=float(abs(silent).max()))
        findings[direction] = diagnostics
    save_json(args.report, dict(kind='rmx220-reverb-initial-identification', sample_rate=48000,
        reference_identity=IDENTITY, full_reverb_match=False, physical_hardware=False,
        calibration_sha256=sha256(args.calibration), identifier_sha256=sha256(Path(__file__)),
        reference_offset_frames=32, findings=findings,
        limitations=['Static factory controls, 120 BPM, 48 kHz; no User profiles or moving controls.',
            'Fitted gains describe component shape only and are not used for clone acceptance.',
            'No numerical implementation is identified by these diagnostics alone.']))
    print('Recorded Reverb diagnostics; full-effect matching remains unproven')


def predict(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    initial = json.loads(args.initial.read_text())
    if initial.get('kind') != 'rmx220-reverb-initial-identification':
        raise ValueError('Wrong initial identification')
    forecasts, fits = [], []
    for direction, degree in (('up',4),('down',2)):
        rows = [x for x in initial['findings'][direction]['cases']
                if '-main-' in x['case'] and x['main_raw'] > 0]
        raw = np.array([x['main_raw']/255 for x in rows])
        onset = np.array([x['residual_onset_frames'] for x in rows])
        coefficients = np.polynomial.polynomial.polyfit(raw,onset,degree)
        training = np.polynomial.polynomial.polyval(raw,coefficients).T
        fits.append(dict(direction=direction,degree=degree,coefficients_ascending=coefficients.tolist(),
            training_maximum_absolute_error_frames=float(abs(training-onset).max())))
        for case in recipe('timing')[1]:
            if case['direction'] != direction:
                continue
            forecasts.append(dict(case=case['name'],main_raw=case['main'],
                onset_frames=np.polynomial.polynomial.polyval(case['main']/255,coefficients).tolist()))
    save_json(args.report,dict(kind='rmx220-reverb-onset-predictions',
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        initial_measurement_sha256=sha256(args.initial),script_sha256=sha256(Path(__file__)),
        sample_rate=48000,maximum_absolute_error_frames=2,forecasts=forecasts,fits=fits,
        full_reverb_match=False,physical_hardware=False,
        scope='Prospective first detectable residual onset only; no waveform or topology certificate.'))
    print('Saved 16 prospective onset predictions before new captures')


def validate_timing(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    prediction=json.loads(args.prediction.read_text())
    manifest=json.loads((args.session/'matrix.json').read_text())
    if (prediction.get('kind') != 'rmx220-reverb-onset-predictions'
            or manifest.get('prospective_prediction_sha256') != sha256(args.prediction)):
        raise ValueError('Capture lacks this saved prospective prediction')
    waves,cases=recipe('timing')
    results=[]
    for case in cases:
        _,audio,source,provenance=checked(args.session,case,waves[case['source']])
        coefficient=float(audio[48000,0]/source[48000,0])
        response=residual(audio,source,coefficient)[48000:]
        onset=[]
        for ch in range(2):
            values=np.flatnonzero(abs(response[:,ch]) > max(1e-15,float(abs(response[:,ch]).max())*1e-7))
            if not len(values):
                raise ValueError('Expected nonzero residual response')
            onset.append(int(values[0]))
        forecast=next(x for x in prediction['forecasts'] if x['case']==case['name'])
        error=np.array(onset)-forecast['onset_frames']
        results.append(dict(**provenance,measured_onset_frames=onset,predicted_onset_frames=forecast['onset_frames'],
            error_frames=error.tolist(),passed=bool(np.max(abs(error)) <= prediction['maximum_absolute_error_frames'])))
    passed=all(x['passed'] for x in results)
    save_json(args.report,dict(kind='rmx220-reverb-onset-prediction-validation',passed=passed,
        full_reverb_match=False,physical_hardware=False,calibration_sha256=sha256(args.calibration),
        prediction_sha256=sha256(args.prediction),script_sha256=sha256(Path(__file__)),cases=results,
        maximum_absolute_error_frames=prediction['maximum_absolute_error_frames'],
        limitation='First detectable residual onset only; no whole-output, tail or listening match.'))
    print('PASS' if passed else 'FAIL','prospective Reverb onset predictions')
    return 0 if passed else 1


def long_tail(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    waves,cases=recipe('long-tail')
    rows=[]
    for case in cases:
        _,audio,source,provenance=checked(args.session,case,waves[case['source']])
        coefficient=float(audio[48000,0]/source[48000,0])
        response=residual(audio,source,coefficient)[48000:]
        rows.append(dict(**provenance,amount_raw=case['amount'],decay=decay(response)))
    save_json(args.report,dict(kind='rmx220-reverb-long-tail-diagnostics',sample_rate=48000,
        full_reverb_match=False,physical_hardware=False,calibration_sha256=sha256(args.calibration),
        script_sha256=sha256(Path(__file__)),cases=rows,
        scope='Main128, Sub2 zero; 90-second post-input tail; no clone acceptance.'))
    print('Recorded long Reverb decay diagnostics')


def filter_model(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    waves,cases=recipe('initial')
    by_name={c['name']:c for c in cases}
    measurements=[]
    for direction in BUTTONS:
        case=by_name[direction+'-main-128']
        _,audio,source,_=checked(args.session,case,waves[case['source']])
        base=residual(audio,source,1)[48000:]
        for raw in (64,128,192,255):
            case=by_name[f'{direction}-cutoff-{raw}']
            _,audio,source,provenance=checked(args.session,case,waves[case['source']])
            target=residual(audio,source,1)[48000:]
            n=np.arange(2,96000)
            design=np.column_stack([-target[n-1].ravel(),-target[n-2].ravel(),
                base[n].ravel(),base[n-1].ravel(),base[n-2].ravel()])
            values=target[n].ravel()
            coefficients=np.linalg.lstsq(design,values,rcond=1e-13)[0]
            def properties(a1,a2):
                alpha=(1-a2)/(1+a2)
                w=np.arccos(np.clip(-a1/(1+a2),-1,1))
                return dict(hz=float(w*48000/(2*np.pi)),Q=float(np.sin(w)/(2*alpha)))
            measurements.append(dict(**provenance,direction=direction,cutoff_raw=raw,
                ratio_coefficients=coefficients.tolist(),
                recurrence_relative_rms_error=relative(values,design@coefficients),
                target_poles=properties(*coefficients[:2]),
                baseline_poles=properties(coefficients[3]/coefficients[2],coefficients[4]/coefficients[2])))
    model=dict(up=dict(type='highpass',minimum_hz=54,maximum_hz=6310),
               down=dict(type='lowpass',minimum_hz=261,maximum_hz=17330),
               Q=float(np.sqrt(.5)),cutoff_dead_raw=4,cutoff_span_raw=251,
               output_gain_offset=1,output_gain_slope=.5/255)
    save_json(args.report,dict(kind='rmx220-reverb-output-filter-model',sample_rate=48000,
        full_reverb_match=False,physical_hardware=False,model=model,measurements=measurements,
        script_sha256=sha256(Path(__file__)),calibration_sha256=sha256(args.calibration),
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        assumptions=['Rounded endpoint frequencies, exponential cutoff map with four-count dead region, Butterworth Q and linear output gain.',
            'The fit supplies original reverb output as the input fixture; this is not an autonomous Reverb model.',
            'Fixed hypotheses are validated separately on withheld knob positions and broadband stimuli.']))
    print('Saved output-filter model before fresh held-out captures')


def validate_filters(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    model_record=json.loads(args.model.read_text())
    manifest=json.loads((args.session/'matrix.json').read_text())
    if (model_record.get('kind') != 'rmx220-reverb-output-filter-model'
            or model_record['calibration_sha256'] != sha256(args.calibration)
            or manifest.get('prospective_prediction_sha256') != sha256(args.model)):
        raise ValueError('Wrong filter model/calibration')
    model=model_record['model']
    waves,cases=recipe('filters')
    initial_waves,initial_cases=recipe('initial')
    initial_by={c['name']:c for c in initial_cases}
    results=[]
    for case in cases:
        _,target,source,provenance=checked(args.session,case,waves[case['source']])
        baseline=initial_by[case['direction']+('-source-probe' if case['source']=='probe' else '-main-128')]
        _,base,_,base_provenance=checked(args.initial,baseline,initial_waves[baseline['source']])
        wet_base=residual(base,source,1)
        wet_target=residual(target,source,1)
        if len(base) != len(target):
            raise ValueError('Filter component extent differs')
        spec=model[case['direction']]
        low,high=spec['minimum_hz'],spec['maximum_hz']
        position=max(0,case['cutoff']-model['cutoff_dead_raw'])/model['cutoff_span_raw']
        frequency=low*(high/low)**position if case['direction']=='up' else high*(low/high)**position
        baseline_frequency=low if case['direction']=='up' else high
        def coefficients(hz):
            w=2*np.pi*hz/48000
            alpha=np.sin(w)/(2*model['Q'])
            b0=(1+np.cos(w) if case['direction']=='up' else 1-np.cos(w))/2/(1+alpha)
            return b0,np.array([1.,-2*np.cos(w)/(1+alpha),(1-alpha)/(1+alpha)])
        b0,a=coefficients(frequency)
        base_b0,base_a=coefficients(baseline_frequency)
        nfft=1 << (2*len(base)-1).bit_length()
        z=np.exp(-2j*np.pi*np.arange(nfft//2+1)/nfft)
        numerator=base_a[0]+base_a[1]*z+base_a[2]*z*z
        denominator=a[0]+a[1]*z+a[2]*z*z
        gain=model['output_gain_offset']+model['output_gain_slope']*case['cutoff']
        transfer=gain*b0/base_b0*numerator/denominator
        predicted=np.fft.irfft(np.fft.rfft(wet_base,n=nfft,axis=0)*transfer[:,None],n=nfft,axis=0)[:len(base)]
        results.append(dict(**provenance,baseline=base_provenance,
            predicted_cutoff_hz=float(frequency),predicted_output_gain=float(gain),
            wet=screen(wet_target,predicted),post_input_tail=screen(wet_target[len(source):],predicted[len(source):])))
    passed=all(x['wet']['passed'] and x['post_input_tail']['passed'] for x in results)
    save_json(args.report,dict(kind='rmx220-reverb-output-filter-validation',passed=passed,
        full_reverb_match=False,physical_hardware=False,cases=results,
        sample_rate=48000,script_sha256=sha256(Path(__file__)),model_sha256=sha256(args.model),
        calibration_sha256=sha256(args.calibration),
        acceptance=dict(relative_rms_error_limit=.01,silent_channel_absolute_rms_limit=1e-8,
            gain_fit=False,wet_alignment_search=False),
        limitations=['Original neutral-filter reverb supplies the component input.',
            'FFT implements the fixed rational filter ratio with zero padding; no fitted comparison gain or alignment.',
            'Passing this component does not validate the reverberator, Main/Sub1 laws, gestures or hardware.']))
    print('PASS' if passed else 'FAIL','held-out Reverb output-filter component')
    return 0 if passed else 1


def compare(args):
    calibration(args.calibration)
    root = new_directory(args.output)
    waves, cases = recipe(args.stage)
    results = []
    for case in cases:
        receipt, audio, source, provenance = checked(args.session, case, waves[case['source']])
        settings = dict(input_gain=0, output_gain=0, bypass=0, auto_tempo=0, quantize=0,
            tempo=120, scene_on=1, scene_type=4 if case['direction']=='up' else 9,
            scene_source=0, scene_depth=case['main']/255, scene_time=case['amount']/255*7,
            scene_resonance=case['cutoff']/255, sampler_mute=1, isolate_on=0)
        preset, output = root/(case['name']+'.rmx'), root/(case['name']+'.wav')
        preset.write_text('RMX_STATE 1\n'+''.join(f'param {k} {v:.9g}\n' for k,v in settings.items()))
        run([args.renderer, receipt['input_path'], output, preset, case['tail']])
        rate, candidate = float_wav(output)
        if rate != 48000 or len(candidate) != len(audio)+32:
            raise ValueError('Candidate extent/rate differs')
        candidate = candidate[:len(audio)]
        row = dict(**provenance, candidate_sha256=sha256(output), preset_sha256=sha256(preset),
            whole=screen(audio,candidate), post_input_tail=screen(audio[len(source):],candidate[len(source):]))
        results.append(row)
        print('PASS' if row['whole']['passed'] and row['post_input_tail']['passed'] else 'FAIL',case['name'],flush=True)
    passed = all(x['whole']['passed'] and x['post_input_tail']['passed'] for x in results)
    repo = Path(__file__).resolve().parents[1]
    source_paths = [*sorted((repo/'include/rmx').glob('*.h')), *sorted((repo/'src/core').glob('*.cpp')),
                    repo/'tools/render.cpp',Path(__file__).resolve()]
    save_json(root/'comparison.json',dict(kind='rmx220-reverb-production-baseline', passed=passed,
        full_reverb_match=False, physical_hardware=False, reference_identity=IDENTITY, sample_rate=48000,
        renderer_sha256=sha256(args.renderer),calibration_sha256=sha256(args.calibration),
        source_sha256={str(p.relative_to(repo)):sha256(p) for p in source_paths},cases=results,
        acceptance=dict(relative_rms_error_limit=.01,silent_channel_absolute_rms_limit=1e-8,
            reference_channel_energy_floor=1e-20,reference_offset_frames=32,gain_fit=False,wet_alignment_search=False),
        limitations=['Whole output and post-input tail are screened separately per channel.',
            'No fitted candidate gain or effect-specific alignment; only reviewed bypass offset.',
            'No perceptual similarity percentage or hardware equivalence is established.']))
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('capture')
    p.add_argument('--stage',choices=STAGES,default='initial')
    p.add_argument('--prediction',type=Path)
    for name in ('host','plugin','session'):
        p.add_argument('--'+name,type=Path,required=True)
    for command in ('verify','analyze','compare'):
        p=commands.add_parser(command)
        p.add_argument('--session',type=Path,required=True)
        if command in ('verify','compare'):
            p.add_argument('--stage',choices=STAGES,default='initial')
        if command != 'verify':
            p.add_argument('--calibration',type=Path,required=True)
        if command == 'compare':
            p.add_argument('--renderer',type=Path,required=True)
            p.add_argument('--output',type=Path,required=True)
        else:
            p.add_argument('--report',type=Path,required=True)
    p=commands.add_parser('predict')
    for name in ('initial','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('filter-model')
    for name in ('session','calibration','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('filter-validate')
    for name in ('session','initial','model','calibration','report'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('timing','long-tail'):
        p=commands.add_parser(name)
        for key in ('session','calibration','report'):
            p.add_argument('--'+key,type=Path,required=True)
        if name == 'timing':
            p.add_argument('--prediction',type=Path,required=True)
    args=parser.parse_args()
    result={'capture':capture,'verify':verify,'analyze':analyze,'compare':compare,
        'predict':predict,'timing':validate_timing,'long-tail':long_tail,
        'filter-model':filter_model,'filter-validate':validate_filters}[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__=='__main__':
    main()
