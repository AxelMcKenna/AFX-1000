#!/usr/bin/env python3
"""Identify and validate an autonomous, scoped Reverb Down research candidate."""
import argparse
import datetime
import itertools
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked, controls, recipe, residual
from tools.rmx_spiral_core import calibration

AP_DELAYS = ((335, 1091), (395, 1031))
AP_GAIN = .7


def biquad(z, hz, high):
    w = 2*np.pi*hz/48000
    alpha = np.sin(w)/np.sqrt(2)
    a = [1, -2*np.cos(w)/(1+alpha), (1-alpha)/(1+alpha)]
    b = (1+np.cos(w) if high else 1-np.cos(w))/2/(1+alpha)*np.array([1, -2 if high else 2, 1])
    return np.polynomial.polynomial.polyval(z, b)/np.polynomial.polynomial.polyval(z, a)


def global_filter(z):
    result = biquad(z, 54, True)*biquad(z, 17330, False)
    for hz, high in ((80, True), (10000, False)):
        pole = (1-np.tan(np.pi*hz/48000))/(1+np.tan(np.pi*hz/48000))
        numerator = (1+pole)/2*(1-z) if high else (1-pole)/2*(1+z)
        result *= numerator/(1-pole*z)
    return result


def allpass(z, channel):
    result = np.ones(len(z), complex)
    for delay in AP_DELAYS[channel]:
        result *= (z**delay-AP_GAIN)/(1-AP_GAIN*z**delay)
    return result


def first_peaks(values):
    x = values[:96000]
    peaks = np.flatnonzero((x[1:-1] > x[:-2]) & (x[1:-1] > x[2:])
                          & (x[1:-1] > .4*x.max()))+1
    if len(peaks) < 5:
        raise ValueError('Fewer than five identifiable positive arrivals')
    return peaks[:5].tolist()


def refine(function, initial):
    p = np.array(initial, dtype=float)
    for _ in range(35):
        error = function(p)
        steps = np.eye(len(p))*1e-6
        jacobian = np.column_stack([(function(p+s)-function(p-s))/2e-6 for s in steps])
        step = np.linalg.lstsq(jacobian, -error, rcond=1e-12)[0]
        if np.linalg.norm(step) < 1e-11:
            break
        accepted = False
        for divisor in (1, 2, 4, 8, 16, 32, 64, 128):
            proposal = p+step/divisor
            if (np.all(proposal < -1e-5) and np.all(proposal > -.5)
                    and np.linalg.norm(function(proposal)) < np.linalg.norm(error)):
                p, accepted = proposal, True
                break
        if not accepted:
            break
    return p


def identify(args):
    if args.report.exists() or args.header.exists():
        raise ValueError('Report and header must be new')
    calibration(args.calibration)
    waves, cases = recipe('initial')
    by_name = {c['name']: c for c in cases}
    records = {}
    for source in ('left', 'right'):
        case = by_name['down-source-'+source]
        records[source] = checked(args.initial, case, waves[case['source']])
    size = 2097152
    z = np.exp(-2j*np.pi*np.arange(size//2+1)/size)
    transfer = np.column_stack([allpass(z, ch)*global_filter(z) for ch in (0, 1)])
    arrivals = {}
    for source, (_, audio, x, _) in records.items():
        wet = residual(audio, x, 1)[48000:]/float(x[48000, 0 if source == 'left' else 1])
        whitened = np.fft.irfft(np.fft.rfft(wet, n=size, axis=0)*transfer.conj()
            /(abs(transfer)**2+1e-10), n=size, axis=0)
        arrivals[source] = [first_peaks(whitened[:, ch]) for ch in (0, 1)]
    if arrivals['left'][1] != arrivals['right'][0]:
        raise ValueError('Cross-channel arrival sets disagree')
    left, right = arrivals['left'][0], arrivals['right'][1]
    cross = arrivals['left'][1]
    pairings = [p for p in itertools.permutations(right)
                if sorted(a+b for a, b in zip(left, p)) == cross]
    if len(pairings) != 1:
        raise ValueError('Stereo comb pairing is not unique')
    delays = np.column_stack([left, pairings[0]])
    # Delays are identified from both columns; numerical gains are fitted only
    # to the left-input recording. No broadband or level fixtures enter the fit.
    _, audio, x, _ = records['left']
    wet = residual(audio, x, 1)[48000:]/float(x[48000, 0])
    nfft = 1048576
    bins = np.arange(64, nfft//2, 32)
    hz = bins*48000/nfft
    bins = bins[(hz >= 60) & (hz < 18000)]
    z = np.exp(-2j*np.pi*bins/nfft)
    observed = np.fft.rfft(wet, n=nfft, axis=0)[bins]
    diffusers = np.column_stack([allpass(z, ch) for ch in (0, 1)])
    dephased = observed/diffusers
    zl = z[:, None]**delays[:, 0]
    periods = z[:, None]**delays.sum(axis=1)

    def network(parameters):
        gl, loop = np.exp(parameters[:5]), np.exp(parameters[5:])
        return np.column_stack([np.sum(gl*zl/(1-loop*periods), axis=1),
                                np.sum(loop*periods/(1-loop*periods), axis=1)])

    initial = -3*np.log(10)/(48000*7)*np.r_[delays[:, 0], delays.sum(axis=1)]
    scale = np.linalg.norm(dephased[:, 0]*network(initial)[:, 1])

    def objective(parameters):
        candidate = network(parameters)
        error = (dephased[:, 1]*candidate[:, 0]-dephased[:, 0]*candidate[:, 1])/scale
        return np.r_[error.real, error.imag]

    fitted = refine(objective, initial)
    gl, gr = np.exp(fitted[:5]), np.exp(fitted[5:]-fitted[:5])
    if np.any(gl >= 1) or np.any(gr >= 1) or np.any(gr <= 0):
        raise ValueError('Fitted feedback is not stable and positive')
    unit = network(fitted)*diffusers*global_filter(z)[:, None]
    gain = float(np.real(np.sum(unit.conj()*observed))/np.sum(abs(unit)**2))
    prediction = unit*gain
    frequency_error = float(np.linalg.norm(prediction-observed)/np.linalg.norm(observed))
    if frequency_error > 1e-4:
        raise ValueError('Proposed network/filter structure fails its fitting screen')
    header = '// Own I/O calibration; Down Main128/Sub1-128/48 kHz only.\n#pragma once\n#include <array>\n'
    header += 'constexpr std::array<std::array<int,2>,5> reverbDownDelays{{'
    header += ','.join('{{'+','.join(map(str, pair))+'}}' for pair in delays.tolist())+'}};\n'
    for name, values in (('L', gl), ('R', gr)):
        header += 'constexpr std::array<double,5> reverbDownGain'+name+'{'
        header += ','.join(format(float(v), '.17g') for v in values)+'};\n'
    header += 'constexpr double reverbDownWetGain='+format(gain, '.17g')+';\n'
    args.header.parent.mkdir(parents=True, exist_ok=True)
    with args.header.open('x') as f:
        f.write(header)
    save_json(args.report, dict(kind='rmx220-reverb-down-neutral-network-identification',
        sample_rate=48000, reference_identity=IDENTITY, full_reverb_match=False, physical_hardware=False,
        identifier_sha256=sha256(Path(__file__)), recipe_script_sha256=sha256(Path('tools/rmx_reverb_characterize.py')),
        calibration_sha256=sha256(args.calibration), header_sha256=sha256(args.header),
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sources={name: record[3] for name, record in records.items()}, arrivals=arrivals,
        comb_delays=delays.tolist(), gain_left=gl.tolist(), gain_right=gr.tolist(), wet_gain=gain,
        allpass_delays=AP_DELAYS, allpass_gain=AP_GAIN,
        stereo_relation_relative_error=float(np.linalg.norm(objective(fitted))),
        fixed_filter_frequency_relative_error=frequency_error,
        fixed_filter_hypotheses=dict(highpass_one_pole_hz=80, lowpass_one_pole_hz=10000,
            highpass_biquad_hz=54, lowpass_biquad_hz=17330, biquad_Q=float(np.sqrt(.5))),
        scope='Factory Down, Main128, Sub1-128, Sub2 zero, 48 kHz, 120 BPM.',
        limitations=['Five comb-pair and two-per-channel allpass topology is an empirical candidate, not manufacturer attribution.',
            'Regularized inverse filtering locates discrete arrivals; it does not certify the complete model.',
            'The fitting screen is component evidence; independent autonomous renders are required.',
            'Other Main/Sub1 settings, Up, User profiles, gestures, startup, rates and hardware remain unproven.']))
    print('Identified five comb pairs; fixed-filter fitting error', frequency_error)


def holdout_recipe():
    rng = np.random.default_rng(0x5E7B28)
    x = np.zeros((384000, 2))
    t = np.arange(48000)/48000
    x[48000:144000] = rng.normal(0, .027, (96000, 2))
    x[144000:192000] = .02*np.column_stack((np.sin(2*np.pi*83*t)+np.sin(2*np.pi*4013*t),
                                          np.cos(2*np.pi*139*t)+np.sin(2*np.pi*7379*t)))
    for index in range(8):
        start = 192000+index*12000
        u = np.arange(12000)/48000
        x[start:start+12000, 0] = .11*np.sin(2*np.pi*(57+3*index)*u)*np.exp(-u*29)
        x[start:start+12000, 1] = rng.normal(0, .035, 12000)*np.exp(-u*43)
    pulse = np.zeros((288000, 2))
    pulse[59259, 0], pulse[209151, 1] = .03, -.027
    waves = {'probe': x, 'late': pulse}
    cases = [dict(name=f'down-{source}-cutoff-{raw}', source=source, direction='down',
                  main=128, amount=128, cutoff=raw, tail=18)
             for source in waves for raw in (0, 77, 173, 241)]
    return waves, cases


def model_checked(path, calibration_path):
    model = json.loads(path.read_text())
    if (model.get('kind') != 'rmx220-reverb-down-neutral-network-identification'
            or model['calibration_sha256'] != sha256(calibration_path)):
        raise ValueError('Wrong neutral network model/calibration')
    return model


def capture(args):
    calibration(args.calibration)
    model_checked(args.model, args.calibration)
    model_hash = sha256(args.model)
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    waves, cases = holdout_recipe()
    for name, samples in waves.items():
        write_wav(root/(name+'.wav'), 48000, samples.ravel())
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
    if sha256(args.model) != model_hash:
        raise ValueError('Prospective model changed during capture')
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-down-network-holdouts', cases=cases,
        prospective_model_sha256=model_hash, capture_script_sha256=sha256(Path(__file__))))


def verify(args):
    if args.report.exists():
        raise ValueError('Report must be new')
    waves, cases = holdout_recipe()
    rows = [checked(args.session, case, waves[case['source']])[3] for case in cases]
    save_json(args.report, dict(kind='rmx220-reverb-down-network-holdout-verification',
        passed=True, cases=rows, script_sha256=sha256(Path(__file__)),
        scope='Exact inputs, controls, extent and hashes only; no sonic matching claim.'))
    print('Verified eight fresh exact holdout recipes')


def compare(args):
    calibration(args.calibration)
    model_checked(args.model, args.calibration)
    if args.holdout:
        manifest = json.loads((args.holdout/'matrix.json').read_text())
        if manifest.get('prospective_model_sha256') != sha256(args.model):
            raise ValueError('Holdout does not bind this prospective model')
    root = new_directory(args.output)
    rows = []
    sessions = [('initial', args.initial, recipe('initial')), ('filters', args.filters, recipe('filters'))]
    if args.holdout:
        sessions.append(('network-holdout', args.holdout, holdout_recipe()))
    for stage, session, (waves, cases) in sessions:
        for case in cases:
            if case['direction'] != 'down' or case['main'] != 128 or case['amount'] != 128:
                continue
            receipt, audio, source, provenance = checked(session, case, waves[case['source']])
            output = root/(stage+'-'+case['name']+'.wav')
            run([args.renderer, receipt['input_path'], output, case['cutoff'], case['tail']])
            rate, candidate = float_wav(output)
            if rate != 48000 or len(candidate) != len(audio)+32:
                raise ValueError('Renderer extent/rate differs')
            candidate = candidate[:len(audio)].astype(float)
            wet_a, wet_b = residual(audio, source, 1), residual(candidate, source, 1)
            item = dict(**provenance, stage=stage, whole=screen(audio, candidate),
                wet=screen(wet_a, wet_b), post_input_tail=screen(audio[len(source):], candidate[len(source):]),
                candidate_sha256=sha256(output))
            rows.append(item)
            print('PASS' if all(item[k]['passed'] for k in ('whole', 'wet', 'post_input_tail'))
                  else 'FAIL', stage, case['name'], flush=True)
    passed = all(row[k]['passed'] for row in rows for k in ('whole', 'wet', 'post_input_tail'))
    repo = Path(__file__).resolve().parents[1]
    sources = [Path(__file__), repo/'research/audio/experiments/reverb_down_neutral_probe.cpp',
               repo/'research/audio/experiments/ReverbDownNeutralCalibration.h']
    save_json(root/'comparison.json', dict(kind='rmx220-reverb-down-neutral-autonomous-comparison',
        passed=passed, full_reverb_match=False, physical_hardware=False, sample_rate=48000,
        reference_identity=IDENTITY, cases=rows, calibration_sha256=sha256(args.calibration),
        model_sha256=sha256(args.model), renderer_sha256=sha256(args.renderer),
        source_sha256={str(path.resolve().relative_to(repo)): sha256(path) for path in sources},
        acceptance=dict(relative_rms_error_limit=.01, silent_channel_absolute_rms_limit=1e-8,
            reference_channel_energy_floor=1e-20, reference_offset_frames=32,
            gain_fit=False, wet_alignment_search=False),
        scope='Research Down Main128/Sub1-128, static factory Sub2, 48 kHz, 120 BPM; input silence precedes excitation.',
        limitations=['This renderer supplies its own reverberator and uses no original-derived wet fixture.',
            'Other Main/Sub1 settings and Up remain outside this candidate.',
            'No device-wide or perceptual similarity percentage, moving-control or hardware equivalence is established.']))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('identify')
    for name in ('initial', 'calibration', 'report', 'header'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('capture')
    for name in ('host', 'plugin', 'session', 'model', 'calibration'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('verify')
    for name in ('session', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('compare')
    for name in ('initial', 'filters', 'model', 'calibration', 'renderer', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--holdout', type=Path)
    args = parser.parse_args()
    result = {'identify': identify, 'capture': capture, 'verify': verify, 'compare': compare}[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__ == '__main__':
    main()
