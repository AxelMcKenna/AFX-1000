#!/usr/bin/env python3
"""Measure audio differences with explicit bypass calibration and no fitted wet alignment."""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.reference_audio import read_wav, save_json, sha256  # noqa: E402


def stereo(samples):
    result = np.asarray(samples, dtype=np.float64)
    if result.ndim == 1 and result.size % 2 == 0:
        result = result.reshape(-1, 2)
    if result.ndim != 2 or result.shape[1] != 2 or not result.size or not np.isfinite(result).all():
        raise ValueError('Expected nonempty finite stereo audio')
    return result


def db(amplitude):
    return 20 * math.log10(max(float(amplitude), 1e-15))


def calibrate(reference, candidate, rate, maximum_delay_seconds=.1):
    """Estimate a pure route delay from bypass only; review remains mandatory.

    Integer correlation locates the lag. A weighted cross-spectrum phase slope
    then estimates its fractional part. Phase residual and channel disagreement
    expose responses that cannot be represented adequately by one pure delay.
    """
    reference, candidate = stereo(reference), stereo(candidate)
    if not 8000 <= rate <= 192000 or min(len(reference), len(candidate)) < rate // 10:
        raise ValueError('Calibration needs at least 100 ms at 8..192 kHz')
    if not 0 < maximum_delay_seconds <= 2:
        raise ValueError('Maximum route delay must be 0..2 seconds')
    n = 1 << (len(reference) + len(candidate) - 2).bit_length()
    maximum = min(round(rate * maximum_delay_seconds), n // 2 - 1)
    omega = 2 * np.pi * np.fft.rfftfreq(n)
    useful = (omega >= 2 * np.pi * 100 / rate) & (omega <= 2 * np.pi * min(16000, rate * .4) / rate)
    channels = []
    for channel in range(2):
        x, y = reference[:, channel], candidate[:, channel]
        energy_x, energy_y = np.dot(x, x), np.dot(y, y)
        if min(energy_x, energy_y) <= 1e-20:
            raise ValueError('Both bypass channels must contain a calibration signal')
        a, b = np.fft.rfft(x, n), np.fft.rfft(y, n)
        cross = b * a.conj()
        correlation = np.fft.irfft(cross, n)
        lags = np.arange(-maximum, maximum + 1)
        values = correlation[lags % n]
        index = int(np.argmax(np.abs(values)))
        coarse = int(lags[index])
        polarity = 1 if values[index] >= 0 else -1
        normalized_peak = float(abs(values[index]) / math.sqrt(energy_x * energy_y))
        valid = useful & (np.abs(a) > np.max(np.abs(a)) * 1e-4) & (np.abs(cross) > np.max(np.abs(cross)) * 1e-8)
        power = np.abs(a[useful]) ** 2
        effective_bins = float(power.sum() ** 2 / max(float(power @ power), 1e-30))
        if valid.sum() < 100 or np.ptp(omega[valid]) < .25 or effective_bins < 100:
            raise ValueError('Calibration signal has insufficient excited bandwidth; use broadband bypass audio')
        phase = np.unwrap(np.angle(cross[valid] * polarity * np.exp(1j * omega[valid] * coarse)))
        weight = np.sqrt(np.abs(cross[valid]) / np.max(np.abs(cross[valid])))
        design = np.column_stack((omega[valid], np.ones(valid.sum())))
        slope, intercept = np.linalg.lstsq(design * weight[:, None], phase * weight, rcond=None)[0]
        error = phase - (design @ np.array([slope, intercept]))
        residual = float(np.sqrt(np.average(error ** 2, weights=weight ** 2)))
        channels.append({'delay_frames': float(coarse - slope), 'integer_delay_frames': coarse,
                         'polarity': polarity, 'normalized_correlation_peak': normalized_peak,
                         'effective_excited_bins': effective_bins,
                         'phase_fit_rms_radians': residual,
                         'fractional_fit_within_one_sample': bool(abs(slope) <= 1)})
    delays = [channel['delay_frames'] for channel in channels]
    disagreement = abs(delays[0] - delays[1])
    eligible = disagreement <= .1 and all(c['phase_fit_rms_radians'] <= .05
        and c['normalized_correlation_peak'] >= .5 and c['fractional_fit_within_one_sample']
        and c['polarity'] == 1 for c in channels)
    return {'schema_version': 1, 'kind': 'fractional-bypass-calibration', 'verified': False,
            'sample_rate': rate, 'candidate_delay_frames': float(np.mean(delays)), 'channels': channels,
            'channel_delay_disagreement_frames': disagreement, 'eligible_for_review': eligible,
            'limitations': ['Use bypass only; the tool cannot prove that effects were disabled.',
                           'This estimates one fixed delay, not clock drift or a complete converter response.',
                           'Review routing, channel order, gain, polarity and phase residual before setting verified=true.']}


def align(reference, candidate, delay_frames, half_width=64):
    """Apply only a separately measured route delay; retain every effect delay."""
    reference, candidate = stereo(reference), stereo(candidate)
    if not math.isfinite(delay_frames) or abs(delay_frames) > max(len(reference), len(candidate)):
        raise ValueError('Invalid route delay')
    integer_delay = math.floor(delay_frames)
    fraction = delay_frames - integer_delay
    fractional = abs(fraction) > 1e-10
    margin = half_width if fractional else 0
    start = max(0, -integer_delay) + margin
    candidate_start = start + integer_delay
    length = min(len(reference) - start - margin, len(candidate) - candidate_start - margin)
    if length <= 0:
        raise ValueError('No overlapping audio after route calibration')
    if fractional:
        taps = np.arange(-half_width, half_width + 1, dtype=np.float64)
        kernel = np.sinc(taps + fraction) * np.blackman(len(taps))
        kernel /= kernel.sum()
        shifted = np.column_stack([np.convolve(candidate[:, ch], kernel, mode='same') for ch in range(2)])
    else:
        shifted = candidate
    return reference[start:start + length], shifted[candidate_start:candidate_start + length], {
        'candidate_delay_frames': delay_frames, 'reference_start_frame': start,
        'candidate_start_frame': candidate_start, 'compared_frames': length,
        'fractional_interpolation': '129-tap Blackman sinc' if fractional else 'none',
        'discarded_reference_frames': len(reference) - length,
        'discarded_candidate_frames': len(candidate) - length}


def spectral_metrics(reference, candidate, rate, sizes=(512, 2048, 8192)):
    """STFT magnitude diagnostics; no inferred perceptual similarity score."""
    reference, candidate = stereo(reference), stereo(candidate)
    if reference.shape != candidate.shape:
        raise ValueError('Spectral comparison requires aligned, equal-length stereo audio')
    results = []
    for size in sizes:
        if size > len(reference):
            continue
        hop = size // 4
        window = np.hanning(size)
        accum = [np.zeros((size // 2 + 1, 2)), np.zeros((size // 2 + 1, 2))]
        numerator = denominator = log_error = 0.
        bins = 0
        frames = range(0, len(reference) - size + 1, hop)
        frequency = np.fft.rfftfreq(size, 1 / rate)
        keep = (frequency >= 20) & (frequency <= min(20000, rate * .45))
        count = 0
        for start in frames:
            a = np.abs(np.fft.rfft(reference[start:start + size] * window[:, None], axis=0))
            b = np.abs(np.fft.rfft(candidate[start:start + size] * window[:, None], axis=0))
            numerator += float(np.sum((a[keep] - b[keep]) ** 2))
            denominator += float(np.sum(a[keep] ** 2))
            floor = max(float(np.max(a)), 1e-10) * 1e-5
            log_error += float(np.sum(np.abs(20 * np.log10(np.maximum(a[keep], floor) / np.maximum(b[keep], floor)))))
            bins += int(keep.sum()) * 2
            accum[0] += a * a
            accum[1] += b * b
            count += 1
        bands = []
        for center in (31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400,
                       500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000,
                       5000, 6300, 8000, 10000, 12500, 16000):
            selected = (frequency >= center / 2 ** (1 / 6)) & (frequency < center * 2 ** (1 / 6)) & keep
            if not selected.any():
                continue
            a, b = (np.sum(power[selected], axis=0) / max(count, 1) for power in accum)
            meaningful = a > np.max(accum[0], axis=0) / max(count, 1) * 1e-8
            ratios = [10 * math.log10(max(float(b[ch]), 1e-30) / float(a[ch])) if meaningful[ch] else None
                      for ch in range(2)]
            bands.append({'center_hz': center, 'candidate_minus_reference_db': ratios})
        results.append({'fft_size': size, 'hop_frames': hop, 'windows': count,
                        'magnitude_relative_error': math.sqrt(numerator / denominator) if denominator > 1e-25 else None,
                        'mean_absolute_log_magnitude_db': log_error / bins if bins else None,
                        'third_octave_band_differences': bands})
    return results


def compare(reference, candidate, rate, calibration, maximum_relative_rms=.01, mode='deterministic'):
    if calibration.get('kind') != 'fractional-bypass-calibration' or calibration.get('schema_version') != 1:
        raise ValueError('Expected a version-1 fractional bypass calibration')
    if calibration.get('verified') is not True or calibration.get('eligible_for_review') is not True:
        raise ValueError('Route calibration must be eligible and explicitly reviewed before comparison')
    if calibration.get('sample_rate') != rate:
        raise ValueError('Calibration/capture sample rates differ')
    if not 0 < maximum_relative_rms <= 1 or mode not in ('deterministic', 'stochastic'):
        raise ValueError('Invalid waveform tolerance or comparison mode')
    delay = calibration.get('candidate_delay_frames')
    if isinstance(delay, bool) or not isinstance(delay, (float, int)):
        raise ValueError('Invalid calibrated route delay')
    reference, candidate, alignment = align(reference, candidate, delay)
    if len(reference) < rate // 10:
        raise ValueError('At least 100 ms of aligned audio is required')
    channels = []
    for ch in range(2):
        a, b = reference[:, ch], candidate[:, ch]
        rr, cc = float(a @ a), float(b @ b)
        error = float((a - b) @ (a - b))
        relative = math.sqrt(error / rr) if rr > 1e-20 else None
        channels.append({'channel': 'left' if ch == 0 else 'right',
                         'relative_rms_error': relative,
                         'error_relative_db': db(relative) if relative is not None else None,
                         'level_difference_db': db(math.sqrt(cc / rr)) if rr > 1e-20 and cc > 0 else None,
                         'absolute_error_rms': math.sqrt(error / len(a)),
                         'sample_correlation': float(a @ b) / math.sqrt(rr * cc) if rr * cc > 1e-30 else None,
                         'waveform_criterion_passed': relative <= maximum_relative_rms if relative is not None else None})
    statuses = [c['waveform_criterion_passed'] for c in channels]
    verdict = 'diagnostic_only' if mode == 'stochastic' else (
        'not_assessable' if any(v is None for v in statuses) else 'pass' if all(statuses) else 'fail')
    return {'schema_version': 1, 'kind': 'audio-fidelity-comparison', 'mode': mode,
            'waveform_verdict': verdict, 'maximum_relative_rms_error': maximum_relative_rms,
            'sample_rate': rate, 'alignment': alignment, 'channels': channels,
            'spectral_diagnostics': spectral_metrics(reference, candidate, rate),
            'limitations': ['Waveform acceptance is not a percentage of perceived similarity or full-device conformance.',
                           'No gain fitting, wet-output alignment search or drift correction is performed.',
                           'Stochastic comparisons require repeated-reference distributions and listening; no single-pair pass is assigned.',
                           'Fractional interpolation is finite-band; converter filtering remains in the measured difference.']}


def harmonics(samples, rate, fundamental, maximum_harmonic=10):
    samples = stereo(samples)
    if len(samples) > min(rate * 5, 262144):
        raise ValueError('Choose a stationary analysis interval of at most five seconds / 262144 frames')
    if not 20 <= fundamental < rate / 4 or len(samples) / rate * fundamental < 10:
        raise ValueError('Use a stationary tone with at least ten cycles and a fundamental below Nyquist/2')
    if not 2 <= maximum_harmonic <= 32:
        raise ValueError('Choose 2..32 harmonics')
    orders = [order for order in range(1, maximum_harmonic + 1) if order * fundamental < rate * .49]
    phase = np.arange(len(samples)) * (2 * np.pi * fundamental / rate)
    design = np.column_stack([np.ones(len(samples)), *[f(order * phase) for order in orders for f in (np.sin, np.cos)]])
    weight = np.sqrt(np.hanning(len(samples)))
    coefficients = np.linalg.lstsq(design * weight[:, None], samples * weight[:, None], rcond=None)[0]
    amplitude = np.hypot(coefficients[1::2], coefficients[2::2])
    result = []
    for ch in range(2):
        fundamental_peak = float(amplitude[0, ch])
        if fundamental_peak < 1e-10:
            raise ValueError('Fundamental tone is missing from a channel')
        result.append({'channel': 'left' if ch == 0 else 'right', 'fundamental_peak': fundamental_peak,
                       'dc': float(coefficients[0, ch]),
                       'thd_ratio': float(np.linalg.norm(amplitude[1:, ch]) / fundamental_peak),
                       'harmonics': [{'order': order, 'relative_db': db(amplitude[i, ch] / fundamental_peak)}
                                     for i, order in enumerate(orders)]})
    return {'kind': 'stationary-tone-harmonics', 'sample_rate': rate, 'fundamental_hz': fundamental,
            'channels': result, 'limitations': ['Stationary tone required; attack and release must be excluded.',
                'Reports fitted in-band harmonics only, not THD+N, alias rejection or arbitrary nonlinear-system behavior.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('calibrate', 'compare'):
        sub = commands.add_parser(command)
        sub.add_argument('reference')
        sub.add_argument('candidate')
        sub.add_argument('--report', required=True)
        if command == 'calibrate':
            sub.add_argument('--maximum-delay-seconds', type=float, default=.1)
        else:
            sub.add_argument('--calibration', required=True)
            sub.add_argument('--mode', required=True, choices=('deterministic', 'stochastic'))
            sub.add_argument('--maximum-relative-rms', type=float, default=.01)
    sub = commands.add_parser('harmonics')
    sub.add_argument('input')
    sub.add_argument('--fundamental', type=float, required=True)
    sub.add_argument('--start', type=float, default=0)
    sub.add_argument('--end', type=float)
    sub.add_argument('--report', required=True)
    args = parser.parse_args()
    try:
        if Path(args.report).exists():
            raise ValueError('Report already exists; choose a new path')
        if args.command == 'harmonics':
            rate, samples = read_wav(args.input)
            values = stereo(samples)
            end = len(values) if args.end is None else round(args.end * rate)
            if not 0 <= args.start * rate < end <= len(values):
                raise ValueError('Invalid stationary analysis interval')
            result = harmonics(values[round(args.start * rate):end], rate, args.fundamental)
            result['input'] = {'path': args.input, 'sha256': sha256(args.input)}
            result['interval_seconds'] = [args.start, end / rate]
        else:
            rate, a = read_wav(args.reference)
            rate_b, b = read_wav(args.candidate)
            if rate != rate_b:
                raise ValueError('Capture sample rates differ')
            if args.command == 'calibrate':
                result = calibrate(a, b, rate, args.maximum_delay_seconds)
            else:
                calibration = json.loads(Path(args.calibration).read_text())
                result = compare(a, b, rate, calibration, args.maximum_relative_rms, args.mode)
                result['calibration'] = {'path': args.calibration, 'sha256': sha256(args.calibration)}
            result['files'] = {role: {'path': path, 'sha256': sha256(path)}
                               for role, path in [('reference', args.reference), ('candidate', args.candidate)]}
        save_json(args.report, result)
        print(result.get('waveform_verdict', 'Diagnostic written; review required'))
        return 1 if result.get('waveform_verdict') == 'fail' else 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
