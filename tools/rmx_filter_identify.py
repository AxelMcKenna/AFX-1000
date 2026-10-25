#!/usr/bin/env python3
"""Identify static factory filter paths from public RMX-1000 2.2.0 I/O.

The supplied directories contain completed reference-host captures. No vendor
audio is emitted: the report and optional C++ header contain numerical fits.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import IDENTITY


CALIBRATION_RAW = (0, 1, 3, 4, 8, 16, 24, 32, 48, 64, 80, 96, 112,
                   128, 144, 160, 176, 192, 208, 224, 240, 255)


def checked_impulse(folder):
    receipt = json.loads((folder / 'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role'] != 'reference'
            or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
        raise ValueError('Incomplete or incorrect reference: ' + str(folder))
    for filename, key in (('audio.wav', 'output_sha256'), ('plan.json', 'plan_sha256')):
        if sha256(folder / filename) != receipt[key]:
            raise ValueError('Modified capture: ' + str(folder / filename))
    source = Path(receipt['input_path'])
    if sha256(source) != receipt['input_sha256']:
        raise ValueError('Modified capture input')
    source_rate, source_audio = float_wav(source)
    expected = np.zeros_like(source_audio)
    expected[48000, 0] = np.float32(.05)
    second = 72000 if len(source_audio) == 96000 else 144000
    expected[second, 1] = np.float32(-.04)
    if source_rate != 48000 or not np.array_equal(source_audio, expected):
        raise ValueError('Unexpected identification impulse recipe')
    rate, x = float_wav(folder / 'audio.wav')
    if rate != 48000 or len(x) < 66032:
        raise ValueError('Use the 48 kHz stereo impulse recipe')
    return x[48032:54032, 0].astype(float) / float(np.float32(.05))


def topology(log_t, resonance, gain, effect):
    """Butterworth biquad with delayed, first-order filtered BP feedback."""
    t = np.exp(log_t)
    w = 2 * np.arctan(t)
    alpha = np.sin(w) / np.sqrt(2)
    base = np.array([1, -2*np.cos(w)/(1+alpha), (1-alpha)/(1+alpha)])
    pole = (1-t)/(1+t)
    high = effect == 'hpf'
    c = (1+pole)/2 if high else (1-pole)/2
    band = (1-base[2])/2
    feedback = np.array([0, -1, 1, 1, -1] if high else [0, -1, -1, 1, 1])
    denominator = np.pad(np.convolve(base, [1, -pole]), (0, 1)) + resonance*band*c*feedback
    b0 = (1+(-1 if high else 1)*base[1]+base[2])/4
    numerator = np.pad(np.convolve(b0*np.array([1, -2, 1] if high else [1, 2, 1]), [1, -pole]), (0, 1))
    return denominator, (1-gain)*denominator+gain*numerator


def fit_topology(impulse, effect, raw):
    fc = (60*(10000/60)**(max(raw-4, 0)/251) if effect == 'hpf'
          else 96*(23500/96)**((255-max(raw, 4))/251))
    gain = 1-min(1, max(0, (66-raw)/63))**2
    parameters = np.array([np.log(np.tan(np.pi*fc/48000)),
                           .92 if effect == 'hpf' else .99, gain])
    if raw <= 3:
        parameters[1:] = 0
        return parameters

    def residual(p):
        d, b = topology(*p, effect)
        e = np.convolve(impulse, d)[:len(impulse)]
        e[:len(b)] -= b
        return e

    for _ in range(20):
        e = residual(parameters)
        jacobian = np.stack([(residual(parameters+np.eye(3)[i]*1e-5)-e)/1e-5
                             for i in range(2)], 1)
        step = np.linalg.lstsq(jacobian, -e, rcond=1e-10)[0]
        parameters[:2] += step
        if np.linalg.norm(step) < 1e-10:
            break
    if not np.isfinite(parameters).all():
        raise ValueError('Nonfinite topology fit')
    return parameters


def fit_band(impulse):
    h = impulse.copy()
    h[0] -= 1
    if np.linalg.norm(h) < 1e-10:
        return None
    shifted = [np.r_[np.zeros(i), h[:-i]] for i in (1, 2, 3)]
    delta = np.zeros(len(h))
    delta[0], delta[2] = 1, -1
    return np.linalg.lstsq(np.column_stack((*shifted, -delta)), -h, rcond=1e-12)[0]


def response_error(impulse, denominator, numerator):
    # Frequency-domain energy error includes the reconstructed impulse tail;
    # unlike equation residuals it does not hide near-unit-pole sensitivity.
    size = 32768
    predicted = np.fft.rfft(numerator, size)/np.fft.rfft(denominator, size)
    reference = np.fft.rfft(impulse, size)
    return float(np.linalg.norm(predicted-reference)/np.linalg.norm(reference))


def identify(args):
    if args.report.exists() or (args.header and args.header.exists()):
        raise ValueError('Output must be new')
    roots = [args.base, args.calibration, *args.extra_calibration]
    sources, bands, models = [], [], {}

    def record(folder, effect, raw):
        plan = json.loads((folder/'plan.json').read_text())
        controls = {p['name']: p['value'] for p in plan['parameters']}
        button = {'bpf': 'BpfEchoButton', 'hpf': 'HpfEchoButton', 'lpf': 'LpfEchoButton'}[effect]
        expected = {'SceneVolume': raw/255, 'Sub1Volume': 128/255, 'Sub2Volume': 0,
                    'AutoButton': 1, 'InputButton': 1, 'XpadButton': 0, 'DefaultSwitch': 1, button: 1}
        if (plan['sample_rate'] != 48000 or plan['bpm'] != 120 or plan.get('events')
                or any(abs(controls.get(k, -10)-v) > 1e-7 for k, v in expected.items())):
            raise ValueError('Incorrect identification plan: ' + str(folder))
        sources.append({'capture': folder.name, 'receipt_sha256': sha256(folder/'receipt.json'),
                        'output_sha256': sha256(folder/'audio.wav')})
        return checked_impulse(folder)

    for raw in range(256):
        folder = args.base/'bpf-main-0' if raw == 0 else args.grid/f'bpf-grid-{raw}'
        impulse = record(folder, 'bpf', raw)
        coefficient = fit_band(impulse)
        if coefficient is None:
            bands.append({'raw': raw, 'coefficients': None, 'relative_rms_error': 0.})
            continue
        a1, a2, a3, b0 = coefficient
        if np.max(np.abs(np.roots([1, a1, a2, a3]))) >= 1:
            raise ValueError('Unstable BPF model at ' + str(raw))
        error = response_error(impulse, [1, a1, a2, a3],
                               [1+b0, a1, a2-b0, a3])
        bands.append({'raw': raw, 'coefficients': coefficient.tolist(), 'relative_rms_error': error})
    first = next(p['coefficients'] for p in bands if p['coefficients'])
    for point in bands:
        if point['coefficients'] is None:
            point['coefficients'] = first[:3]+[0.]

    for effect in ('hpf', 'lpf'):
        rows = []
        raw_values = sorted(set(CALIBRATION_RAW) | ({220, 228, 236, 244, 248, 252, 254} if effect == 'lpf' else set()))
        for raw in raw_values:
            folder = next((root/f'{effect}-main-{raw}' for root in roots
                           if (root/f'{effect}-main-{raw}'/'receipt.json').exists()), None)
            if folder is None and raw == 0:
                folder = args.base/f'{effect}-main-0'
            impulse = record(folder, effect, raw)
            parameters = fit_topology(impulse, effect, raw)
            d, b = topology(*parameters, effect)
            error = response_error(impulse, d, b)
            if np.max(np.abs(np.roots(d))) >= 1:
                raise ValueError('Unstable topology at ' + str(folder))
            nominal = (60*(10000/60)**(max(raw-4, 0)/251) if effect == 'hpf'
                       else 96*(23500/96)**((255-max(raw, 4))/251))
            ratio = 2*np.arctan(np.exp(parameters[0]))*48000/(2*np.pi)/nominal
            rows.append({'raw': raw, 'log_t': float(parameters[0]), 'cutoff_ratio': float(ratio), 'resonance': float(parameters[1]),
                         'gain': float(parameters[2]), 'relative_rms_error': error})
        models[effect] = rows
    report = {'kind': 'rmx220-factory-filter-identification', 'sample_rate': 48000,
              'identity': IDENTITY, 'physical_hardware': False,
              'scope': 'Static factory Normal-width filters; Sub2 zero. No gesture or other-rate claim.',
              'identifier_sha256': sha256(Path(__file__)), 'sources': sources,
              'bpf': bands, **models}
    save_json(args.report, report)
    if args.header:
        lines = ['#pragma once', '#include <array>', '', 'namespace rmx {',
                 '// Numerical fits to public I/O; no recorded reference audio.',
                 'struct BandEchoPoint { double a1,a2,a3,b0; };',
                 'inline constexpr std::array<BandEchoPoint,256> bandEchoCalibration {{']
        lines += ['    {'+','.join(f'{v:.16e}' for v in p['coefficients'])+'},' for p in bands]
        lines += ['}};', 'struct FilterEchoPoint { double raw,cutoffRatio,resonance,gain; };']
        for effect in ('hpf', 'lpf'):
            lines += [f'inline constexpr std::array<FilterEchoPoint,{len(models[effect])}> {effect}EchoCalibration {{{{']
            lines += ['    {'+','.join(f'{p[k]:.16e}' for k in ('raw', 'cutoff_ratio', 'resonance', 'gain'))+'},'
                      for p in models[effect]]
            lines += ['}};']
        lines += ['}', '']
        args.header.write_text('\n'.join(lines))
    print(json.dumps({effect: max(p['relative_rms_error'] for p in report[effect])
                      for effect in ('bpf', 'hpf', 'lpf')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'grid', 'calibration', 'report'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--header', type=Path)
    parser.add_argument('--extra-calibration', type=Path, action='append', default=[])
    identify(parser.parse_args())


if __name__ == '__main__':
    main()
