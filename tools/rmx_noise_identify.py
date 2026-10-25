#!/usr/bin/env python3
"""Identify the factory Noise filter from common-seed public output captures.

This identifies filter/level statistics, not the original random generator.
Requires the local event-driven noise-active-SceneVolume-* capture matrix.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.fidelity import stereo
from tools.reference_audio import read_wav, save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, run


RATE = 48000
HOLDOUT = (17, 81, 147, 233)
CALIBRATION = (0, 1, 4, 8, 16, 24, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 255)


def capture_matrix(args):
    root = args.session.resolve()
    root.mkdir(parents=True, exist_ok=False)
    host, plugin = args.host.resolve(), args.plugin.resolve()
    inventory = json.loads(run([host, 'inventory', plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires the original RMX-1000 Plug-in 2.2.0')
    save_json(root / 'inventory.json', inventory)
    write_wav(root / 'silence.wav', RATE, np.zeros(RATE*6*2, dtype=np.float32))

    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Ambiguous reference control: ' + name)
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value}

    common = {'AutoButton': 0, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
              'DefaultSwitch': 1, 'UserSwitch': 0, 'SceneVolume': 128/255,
              'Sub1Volume': 128/255, 'Sub2Volume': 0}
    cases = [(f'noise-active-SceneVolume-{raw}', {'SceneVolume': raw/255}) for raw in (*CALIBRATION, *HOLDOUT)]
    cases += [(f'noise-active-Sub1Volume-{raw}', {'Sub1Volume': raw/255}) for raw in
              (0, 3, 4, 32, 64, 96, 123, 124, 131, 132, 160, 192, 224, 251, 252, 253, 255)]
    cases += [(f'noise-active-repeat-{i}', {}) for i in range(2)]
    matrix = {'kind': 'rmx220-noise-characterization', 'identity': IDENTITY, 'sample_rate': RATE,
              'bpm': 120, 'physical_hardware': False, 'probe_sha256': sha256(root / 'silence.wav'), 'cases': []}
    for name, updates in cases:
        settings = common | updates
        plan = {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'reference',
                'expected_plugin': IDENTITY, 'sample_rate': RATE, 'bpm': 120, 'tail_seconds': 4,
                'parameters': [setting(k, v) for k, v in settings.items()],
                'events': [setting('NoiseButton', 1) | {'type': 'parameter', 'frame': RATE},
                           setting('NoiseButton', 0) | {'type': 'parameter', 'frame': RATE*5}]}
        path = root / (name + '.json')
        save_json(path, plan)
        run([host, 'render', plugin, root / 'silence.wav', path, root / name])
        matrix['cases'].append({'name': name, 'receipt_sha256': sha256(root / name / 'receipt.json')})
        print('Captured', name, flush=True)
    save_json(root / 'matrix.json', matrix)


def capture(root, raw, control='SceneVolume'):
    folder = root / f'noise-active-{control}-{raw}'
    receipt = json.loads((folder / 'receipt.json').read_text())
    if not receipt['complete'] or receipt['role'] != 'reference' or any(receipt['plugin'][k] != v for k, v in IDENTITY.items()):
        raise ValueError('Wrong reference identity or incomplete capture')
    rate, samples = read_wav(folder / 'audio.wav')
    if rate != RATE or receipt['sample_rate'] != RATE or sha256(folder / 'audio.wav') != receipt['output_sha256']:
        raise ValueError('Rate/hash mismatch')
    if sha256(folder / 'plan.json') != receipt['plan_sha256']:
        raise ValueError('Reference plan changed')
    if sha256(root / 'silence.wav') != receipt['input_sha256']:
        raise ValueError('Capture did not use this session\'s silent probe')
    plan = json.loads((folder / 'plan.json').read_text())
    if not any(e.get('name') == 'NoiseButton' and e['value'] == 1 and e['frame'] == RATE for e in plan['events']):
        raise ValueError('Noise must be selected after processing starts')
    return stereo(samples), sha256(folder / 'receipt.json')


def regression(y, x, order=3):
    start, stop = RATE * 2, RATE * 9 // 2
    # Normalize signals separately so very quiet macro positions do not spoil
    # the numerical rank of the cross-relation regression.
    ys = float(np.sqrt(np.mean(y[start:stop] ** 2)))
    xs = float(np.sqrt(np.mean(x[start:stop] ** 2)))
    if ys < 1e-8:
        return None
    a = np.column_stack([y[start-k:stop-k].ravel() / ys for k in range(1, order + 1)] +
                        [x[start-k:stop-k].ravel() / xs for k in range(order + 1)])
    target = y[start:stop].ravel() / ys
    coefficients = np.linalg.lstsq(a, target, rcond=1e-10)[0]
    residual = float(np.linalg.norm(a @ coefficients - target) / np.linalg.norm(target))
    return np.r_[1, -coefficients[:order]], coefficients[order:] * ys / xs, residual


def remove_echo(y, first_return=.35, feedback=.5, delay=12000):
    result = y.copy()
    for start in range(delay, len(y), delay):
        stop = min(start + delay, len(y))
        result[start:stop] -= feedback * y[start-delay:stop-delay] + (first_return-feedback) * result[start-delay:stop-delay]
    return result


def response(point, omega):
    _, a1, a2, a3, b0 = point
    z = np.exp(-1j * omega)
    return b0 * (1-z*z) / (1+a1*z+a2*z*z+a3*z*z*z)


def interpolate(table, raw):
    """Shape-preserving cubic Hermite interpolation (PCHIP)."""
    x, y = table[:, 0], table[:, 1:]
    h = np.diff(x)
    d = np.diff(y, axis=0) / h[:, None]
    m = np.zeros_like(y)
    for i in range(1, len(x)-1):
        same = d[i-1] * d[i] > 0
        w1, w2 = 2*h[i]+h[i-1], h[i]+2*h[i-1]
        m[i, same] = (w1+w2) / (w1/d[i-1, same]+w2/d[i, same])
    for index, h0, h1, d0, d1 in ((0, h[0], h[1], d[0], d[1]),
                                  (-1, h[-1], h[-2], d[-1], d[-2])):
        slope = ((2*h0+h1)*d0-h0*d1)/(h0+h1)
        slope = np.where(slope*d0 <= 0, 0, slope)
        slope = np.where((d0*d1 <= 0) & (np.abs(slope) > 3*np.abs(d0)), 3*d0, slope)
        m[index] = slope
    i = min(len(x)-2, max(0, int(np.searchsorted(x, raw, side='right'))-1))
    t = (raw-x[i])/h[i]
    value = (2*t**3-3*t*t+1)*y[i] + (t**3-2*t*t+t)*h[i]*m[i] + (-2*t**3+3*t*t)*y[i+1] + (t**3-t*t)*h[i]*m[i+1]
    return np.r_[raw, value]


def identify(root):
    reference, reference_receipt = capture(root, 128)
    fits, receipts = {}, {128: reference_receipt}
    for raw in (*CALIBRATION, *HOLDOUT):
        if raw == 128:
            continue
        audio, receipt_hash = capture(root, raw)
        receipts[raw] = receipt_hash
        fits[raw] = regression(audio, reference)
    # Every cross-relation numerator contains the same reference denominator.
    # Robustly pool calibration cases; holdouts do not influence this estimate.
    estimates = [fits[raw][1] / fits[raw][1][0] for raw in CALIBRATION
                 if raw != 128 and fits[raw] is not None]
    baseline = np.median(estimates, axis=0)
    direct = remove_echo(reference)
    whitened = sum(baseline[k] * direct[RATE*2-k:RATE*9//2-k] for k in range(4))
    # A third-order IIR followed by the fixed numerator (1-z^-2) leaves
    # differences of uniform samples: E[(w[n]-w[n-2])^2] = 2/3.
    b0 = float(np.sqrt(np.mean(whitened * whitened) * 1.5))
    lag_two = float(np.sum(whitened[:-2] * whitened[2:]) / np.sqrt(
        np.sum(whitened[:-2] ** 2) * np.sum(whitened[2:] ** 2)))
    kurtosis = float(np.mean(whitened ** 4) / np.mean(whitened ** 2) ** 2)
    if abs(lag_two + .5) > .03 or abs(kurtosis - 2.4) > .1:
        raise ValueError('The assumed uniform moving-average excitation failed its statistical checks')
    points = []
    for raw in CALIBRATION:
        if raw == 128:
            point = [raw, *baseline[1:].tolist(), b0]
        elif fits[raw] is None:
            point = [raw, *baseline[1:].tolist(), 0.]
        else:
            a, b, _ = fits[raw]
            point = [raw, *a[1:].tolist(), b0 * float(b[0])]
        points.append(point)
    # Unexcited near-zero settings use the first excited filter; amplitude is
    # zero there, but a sudden unrelated denominator would disturb a gesture.
    first = next(p for p in points if p[-1] > 0)
    for point in points:
        if point[-1] == 0:
            point[1:4] = first[1:4]
    omega = np.linspace(2*np.pi*20/RATE, 2*np.pi*20000/RATE, 8192)
    table = np.array(points)
    held = []
    for raw in HOLDOUT:
        a, b, residual = fits[raw]
        actual = [raw, *a[1:].tolist(), b0 * float(b[0])]
        interpolated = interpolate(table, raw)
        h = np.abs(response(actual, omega))
        predicted = np.abs(response(interpolated, omega))
        useful = h > np.max(h) * .01
        error = 20 * np.log10(predicted[useful] / h[useful])
        held.append({'raw': raw, 'cross_relation_relative_error': residual,
                     'maximum_magnitude_error_db_above_minus40db': float(np.max(np.abs(error))),
                     'mean_absolute_magnitude_error_db': float(np.mean(np.abs(error)))})
    stable = all(np.max(np.abs(np.roots([1, *interpolate(table, raw)[1:4]]))) < 1 for raw in range(256))
    if not stable:
        raise ValueError('Interpolated filter has an unstable pole')
    tail = reference[RATE*6:RATE*8]
    next_tail = reference[RATE*6+12000:RATE*8+12000]
    tail_error = float(np.linalg.norm(next_tail-tail*.5) / np.linalg.norm(next_tail))
    off_residual = float(np.sqrt(np.mean(direct[RATE*5+512:RATE*6] ** 2)))
    level_rows = []
    centre = (10**(-18/20)+10**(6/20))*.5
    lo, hi = 10**(-18/20)/centre, 10**(6/20)/centre
    basis = reference[RATE*2:RATE*9//2].ravel()
    for raw in (0, 3, 4, 32, 64, 96, 123, 124, 131, 132, 160, 192, 224, 251, 252, 253, 255):
        audio, receipt_hash = capture(root, raw, 'Sub1Volume')
        measured = audio[RATE*2:RATE*9//2].ravel()
        gain = float(basis @ measured / (basis @ basis))
        expected = lo+(1-lo)*np.clip((raw-3)/121, 0, 1) if raw<124 else 1+(hi-1)*np.clip((raw-131)/121, 0, 1)
        if abs(gain-expected)>1e-6:
            raise ValueError('Noise level mapping differs from fitted factory law')
        level_rows.append({'raw_sub1': raw, 'gain_relative_to_raw128': gain,
            'predicted_gain': float(expected), 'receipt_sha256': receipt_hash,
            'relative_shape_residual': float(np.linalg.norm(measured-basis*gain)/np.linalg.norm(measured))})
    return {'kind': 'rmx220-noise-filter-identification', 'sample_rate': RATE,
            'reference_identity': IDENTITY, 'baseline_receipt_sha256': reference_receipt,
            'capture_receipt_sha256': {str(k): v for k, v in sorted(receipts.items())},
            'model': 'b0*(w[n]-w[n-2])/(1+a1*z^-1+a2*z^-2+a3*z^-3), independent uniform stereo excitation',
            'table_columns': ['raw_main', 'a1', 'a2', 'a3', 'b0_at_sub1_raw128'], 'table': points,
            'interpolation': 'shape-preserving cubic Hermite (PCHIP)',
            'baseline_denominator': baseline.tolist(), 'baseline_b0': b0,
            'excitation_checks': {'lag_two_correlation': lag_two, 'kurtosis': kurtosis,
                                  'expected_for_uniform_difference': {'lag_two_correlation': -.5, 'kurtosis': 2.4}},
            'echo': {'delay_frames_at_120bpm': 12000, 'first_return': .35, 'feedback': .5,
                     'tail_feedback_relative_error': tail_error, 'removed_echo_post_off_rms': off_residual},
            'sub1_level': {'inferred_factory_minimum_db': -18, 'inferred_factory_maximum_db': 6,
                'inference': 'Measured 24 dB endpoint span within the documented minimum/maximum choices.',
                'raw_unity_deadband': [124, 131], 'raw_endpoint_clamps': [3, 252],
                'interpolation': 'linear amplitude on each side of the centre', 'cases': level_rows},
            'held_out_positions': held, 'interpolated_poles_stable': stable,
            'limitations': ['The original random generator is not reproduced.',
                'Absolute gain assumes a uniform source; estimated from variance, with finite-window uncertainty.',
                'Static default Width/Sub2 only, at 48 kHz; this is not full Noise or device conformance.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session', required=True, type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--header', type=Path)
    p.add_argument('--capture', action='store_true')
    p.add_argument('--host', type=Path)
    p.add_argument('--plugin', type=Path)
    args = p.parse_args()
    if args.capture:
        if not args.host or not args.plugin:
            p.error('--capture requires --host and --plugin')
        capture_matrix(args)
        return
    if not args.report:
        p.error('Identification requires --report')
    result = identify(args.session)
    save_json(args.report, result)
    if args.header:
        lines = ['#pragma once', '#include <array>', '', 'namespace rmx {',
            '// Fitted public output measurements; no vendor audio or random generator.',
            '// See research/audio/measurements/2026-10-26-noise-filter.json.',
            'struct NoiseCalibrationPoint { float raw,a1,a2,a3,b0; };',
            f'inline constexpr std::array<NoiseCalibrationPoint,{len(result["table"])}> noiseCalibration {{{{']
        for row in result['table']:
            lines.append('    {' + ','.join(f'{v:.9e}f' for v in row) + '},')
        lines += ['}};', '}', '']
        with args.header.open('x') as output:
            output.write('\n'.join(lines))
    print(json.dumps({'held_out': result['held_out_positions'], 'echo': result['echo'],
                      'excitation_checks': result['excitation_checks']}, indent=2))


if __name__ == '__main__':
    main()
