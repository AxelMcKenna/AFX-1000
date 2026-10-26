#!/usr/bin/env python3
"""Measure static Reverb Down control maps; no full-device fidelity claim."""
import argparse
import datetime
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_reverb_characterize import checked, controls
from tools.rmx_reverb_network import allpass, first_peaks, global_filter
from tools.rmx_spiral_core import calibration


def nominal_decay(raw):
    return 1+49*(max(0, raw-3)/252)**3


def recipe(stage):
    source = np.zeros((96000, 2))
    source[48000, 0] = .02
    if stage == 'main':
        return source, [dict(name=f'down-main-{raw}', source='source', direction='down',
            main=raw, amount=128, cutoff=0, tail=3) for raw in range(256)]
    if stage == 'amount':
        return source, [dict(name=f'down-amount-{raw}', source='source', direction='down',
            main=128, amount=raw, cutoff=0, tail=3) for raw in range(256)]
    raise ValueError('Unknown control stage')


def capture(args):
    calibration(args.calibration)
    neutral = json.loads(args.neutral.read_text())
    if (neutral.get('kind') != 'rmx220-reverb-down-neutral-network-identification'
            or neutral['calibration_sha256'] != sha256(args.calibration)):
        raise ValueError('Wrong frozen neutral model')
    neutral_hash = sha256(args.neutral)
    root = new_directory(args.session)
    source, cases = recipe(args.stage)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    write_wav(root/'source.wav', 48000, source.ravel())
    if args.stage == 'amount':
        save_json(root/'predictions.json', dict(kind='reverb-down-sub1-feedback-predictions',
            created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            neutral_model_sha256=neutral_hash, maximum_absolute_gain_error=2e-6,
            formula='gain(raw) = gain(128) ** (nominal_decay(128) / nominal_decay(raw)); nominal_decay = 1 + 49*(max(0,raw-3)/252)^3',
            predictions=[dict(raw=c['amount'],
                left=[g**(nominal_decay(128)/nominal_decay(c['amount'])) for g in neutral['gain_left']],
                right=[g**(nominal_decay(128)/nominal_decay(c['amount'])) for g in neutral['gain_right']]) for c in cases]))
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
        run([args.host, 'render', args.plugin, root/'source.wav', root/(case['name']+'.json'), root/case['name'], 128])
        case['receipt_sha256'] = sha256(root/case['name']/'receipt.json')
        print(case['name'], flush=True)
    if sha256(args.neutral) != neutral_hash:
        raise ValueError('Frozen model changed during capture')
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-down-control-captures', stage=args.stage,
        cases=cases, capture_script_sha256=sha256(Path(__file__)), neutral_model_sha256=neutral_hash,
        predictions_sha256=sha256(root/'predictions.json') if args.stage == 'amount' else None))


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    source, cases = recipe(args.stage)
    records = [checked(args.session, c, source)[3] for c in cases]
    save_json(args.report, dict(kind='rmx220-reverb-down-control-recipe-verification', stage=args.stage,
        passed=True, cases=records, script_sha256=sha256(Path(__file__)),
        scope='Exact input, static controls, rate/extent and capture hashes only.'))
    print('Verified', len(records), args.stage, 'captures')


def refine(function, initial):
    p = np.array(initial, dtype=float)
    for _ in range(30):
        e = function(p)
        steps = np.eye(len(p))*1e-6
        jacobian = np.column_stack([(function(p+s)-function(p-s))/2e-6 for s in steps])
        step = np.linalg.lstsq(jacobian, -e, rcond=1e-12)[0]
        if np.linalg.norm(step) < 1e-10:
            break
        accepted = False
        for divisor in (1, 2, 4, 8, 16, 32, 64, 128):
            q = p+step/divisor
            if np.all(q < -1e-7) and np.all(q > -4) and np.linalg.norm(function(q)) < np.linalg.norm(e):
                p, accepted = q, True
                break
        if not accepted:
            break
    return p


def fit_case(audio, source, case, neutral, detector, frequency):
    h = audio[48000:].astype(float)/float(source[48000, 0])
    dry = float(h[0, 0])
    h[0, 0] = 0
    if not np.count_nonzero(h):
        return dict(dry_gain=dry, silent_wet=True)
    detector_size, transfer = detector
    if case['main'] == 128:
        delays = np.array(neutral['comb_delays'])
    else:
        white = np.fft.irfft(np.fft.rfft(h, n=detector_size, axis=0)*transfer.conj()
                            /(abs(transfer)**2+1e-10), n=detector_size, axis=0)
        left = np.array(first_peaks(white[:, 0]))
        cross = np.array(first_peaks(white[:, 1]))
        right = cross[[0, 1, 3, 2, 4]]-left
        delays = np.column_stack([left, right])
        if np.any(delays <= 0):
            raise ValueError('Invalid detected comb delays')
    size, bins, z, radius, diffusers, equalizer = frequency
    observed = np.fft.rfft(h*radius**np.arange(len(h))[:, None], n=size, axis=0)[bins]
    dephased = observed/diffusers
    zl, periods = z[:, None]**delays[:, 0], z[:, None]**delays.sum(axis=1)

    def network(p):
        gl, loop = np.exp(p[:5]), np.exp(p[5:])
        return np.column_stack([np.sum(gl*zl/(1-loop*periods), axis=1),
                                np.sum(loop*periods/(1-loop*periods), axis=1)])

    initial = -3*np.log(10)/(48000*nominal_decay(case['amount']))*np.r_[delays[:, 0], delays.sum(axis=1)]
    scale = np.linalg.norm(dephased[:, 0]*network(initial)[:, 1])

    def objective(p):
        candidate = network(p)
        e = (dephased[:, 1]*candidate[:, 0]-dephased[:, 0]*candidate[:, 1])/scale
        return np.r_[e.real, e.imag]

    fitted = refine(objective, initial)
    gl, gr = np.exp(fitted[:5]), np.exp(fitted[5:]-fitted[:5])
    unit = network(fitted)*diffusers*equalizer[:, None]
    wet_gain = float(np.real(np.sum(unit.conj()*observed))/np.sum(abs(unit)**2))
    error = float(np.linalg.norm(wet_gain*unit-observed)/np.linalg.norm(observed))
    nominal = -np.log(np.column_stack([gl, gr]))*48000*nominal_decay(case['amount'])/(3*np.log(10))
    return dict(dry_gain=dry, silent_wet=False, delays=delays.tolist(), gain_left=gl.tolist(),
        gain_right=gr.tolist(), nominal_delays=nominal.tolist(), wet_gain=wet_gain,
        damped_frequency_relative_error=error, stereo_relation_relative_error=float(np.linalg.norm(objective(fitted))))


def identify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    calibration(args.calibration)
    neutral = json.loads(args.neutral.read_text())
    if neutral['calibration_sha256'] != sha256(args.calibration):
        raise ValueError('Neutral calibration differs')
    detector_size = 524288
    z = np.exp(-2j*np.pi*np.arange(detector_size//2+1)/detector_size)
    detector = (detector_size, np.column_stack([allpass(z, ch)*global_filter(z) for ch in (0, 1)]))
    size = 262144
    bins = np.arange(16, size//2, 16)
    hz = bins*48000/size
    bins = bins[(hz >= 60) & (hz < 18000)]
    # Identification-only exponential weighting suppresses finite-tail bias.
    # Autonomous waveform acceptance always uses the original, undamped signal.
    radius = np.exp(-3*np.log(10)/(48000*.75))
    z = radius*np.exp(-2j*np.pi*bins/size)
    frequency = (size, bins, z, radius,
        np.column_stack([allpass(z, ch) for ch in (0, 1)]), global_filter(z))
    rows = []
    prediction = None
    if args.stage == 'amount':
        prediction = json.loads((args.session/'predictions.json').read_text())
        manifest = json.loads((args.session/'matrix.json').read_text())
        if (manifest['predictions_sha256'] != sha256(args.session/'predictions.json')
                or prediction['neutral_model_sha256'] != sha256(args.neutral)):
            raise ValueError('Prospective Sub1 prediction differs')
    source, cases = recipe(args.stage)
    for case in cases:
        _, audio, samples, provenance = checked(args.session, case, source)
        result = fit_case(audio, samples, case, neutral, detector, frequency)
        row = dict(**provenance, main_raw=case['main'], amount_raw=case['amount'], **result)
        if prediction is not None:
            forecast = next(x for x in prediction['predictions'] if x['raw'] == case['amount'])
            error = max(abs(np.array(result['gain_left'])-forecast['left']).max(),
                        abs(np.array(result['gain_right'])-forecast['right']).max())
            row['prospective_maximum_absolute_gain_error'] = float(error)
            row['prospective_prediction_passed'] = bool(error <= prediction['maximum_absolute_gain_error'])
        rows.append(row)
        print(case['name'], 'silent' if result['silent_wet'] else f'fit {result["damped_frequency_relative_error"]:.3g}', flush=True)
    passed = all(x.get('damped_frequency_relative_error', 0) <= 1e-4 for x in rows)
    predictions_passed = all(x.get('prospective_prediction_passed', True) for x in rows)
    save_json(args.report, dict(kind='rmx220-reverb-down-control-identification', stage=args.stage,
        fitting_screen_passed=passed, prospective_predictions_passed=predictions_passed, cases=rows,
        full_reverb_match=False, physical_hardware=False, calibration_sha256=sha256(args.calibration),
        neutral_model_sha256=sha256(args.neutral), identifier_sha256=sha256(Path(__file__)),
        prospective_predictions=prediction, identification_weighting_t60_seconds=.75,
        limitations=['Damped-frequency fitting is identification, not an autonomous waveform pass.',
            'Only static integer raw controls, Default, 48 kHz and 120 BPM.',
            'Main/Sub1 interaction and complete independent program material require separate validation.']))
    return 0 if passed and predictions_passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('capture', 'verify', 'identify'):
        p = commands.add_parser(name)
        p.add_argument('--stage', choices=('main', 'amount'), required=True)
        p.add_argument('--session', type=Path, required=True)
        if name in ('capture', 'identify'):
            for key in ('neutral', 'calibration'):
                p.add_argument('--'+key, type=Path, required=True)
        if name == 'capture':
            for key in ('host', 'plugin'):
                p.add_argument('--'+key, type=Path, required=True)
        else:
            p.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = {'capture': capture, 'verify': verify, 'identify': identify}[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__ == '__main__':
    main()
