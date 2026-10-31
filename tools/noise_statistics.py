#!/usr/bin/env python3
"""Compare stationary stereo noise using block band-power confidence intervals.

Approximate 99% intervals use a conservative 3.0 multiplier and a short HAC
variance correction. This is an engineering screen, not a listening verdict.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from tools.reference_audio import save_json, sha256


CENTRES = (20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315,
           400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000,
           5000, 6300, 8000, 10000, 12500, 16000)


def float_wav(path):
    """Read large host float WAVs without millions of boxed Python floats."""
    raw = path.read_bytes()
    if raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
        raise ValueError('Expected RIFF WAVE')
    position, fmt, data = 12, None, None
    while position + 8 <= len(raw):
        tag, count = raw[position:position+4], struct.unpack_from('<I', raw, position+4)[0]
        start = position + 8
        if start+count > len(raw):
            raise ValueError('Truncated WAV chunk')
        if tag == b'fmt ' and count >= 16:
            fmt = struct.unpack_from('<HHIIHH', raw, start)
        if tag == b'data':
            data = (start, count)
        position = start + count + count % 2
    if not fmt or not data or fmt[0] != 3 or fmt[1] != 2 or fmt[4:] != (8, 32) or data[1] % 8:
        raise ValueError('Use stereo float32 host output')
    samples = np.frombuffer(raw, dtype='<f4', offset=data[0], count=data[1]//4).reshape(-1, 2)
    if not np.isfinite(samples).all():
        raise ValueError('Nonfinite audio')
    return fmt[2], samples


def powers(samples, rate, block_seconds=2):
    size = round(block_seconds * rate)
    blocks = len(samples) // size
    if blocks < 20:
        raise ValueError('Use at least twenty two-second stationary blocks')
    window = np.hanning(size)
    frequency = np.fft.rfftfreq(size, 1/rate)
    bands = [(frequency >= center/2**(1/6)) & (frequency < center*2**(1/6)) for center in CENTRES]
    result, total = [], []
    scale = 2 / (size * (window @ window))
    for start in range(0, blocks * size, size):
        x = samples[start:start+size] * window[:, None]
        spectrum = np.abs(np.fft.rfft(x, axis=0)) ** 2 * scale
        result.append([spectrum[keep].sum(axis=0) for keep in bands])
        total.append(np.sum(x*x, axis=0) / np.sum(window*window))
    return np.array(result), np.array(total)


def mean_variance(values):
    centered = values - values.mean(axis=0)
    count = len(values)
    ordinary = np.sum(centered*centered, axis=0) / (count-1)
    hac = ordinary.copy()
    for lag in (1, 2):
        covariance = np.sum(centered[:-lag]*centered[lag:], axis=0) / (count-lag)
        hac += 2*(1-lag/3)*covariance
    return np.maximum(ordinary, hac) / count


def interval(a, b, margin):
    ma, mb = a.mean(axis=0), b.mean(axis=0)
    difference = 10*np.log10(np.maximum(mb, 1e-30)/np.maximum(ma, 1e-30))
    variance = mean_variance(a)/np.maximum(ma, 1e-30)**2 + mean_variance(b)/np.maximum(mb, 1e-30)**2
    half = 3.0 * (10/np.log(10)) * np.sqrt(variance)
    return difference, half, np.abs(difference)+half <= margin


def stereo_correlation(samples):
    sums, squares, cross = np.zeros(2), np.zeros(2), 0.
    for start in range(0, len(samples), 96000):
        block = samples[start:start+96000]
        sums += block.sum(axis=0, dtype=np.float64)
        squares += np.einsum('ij,ij->j', block, block, dtype=np.float64)
        cross += np.einsum('i,i->', block[:, 0], block[:, 1], dtype=np.float64)
    variance = squares-sums*sums/len(samples)
    return float((cross-sums[0]*sums[1]/len(samples))/np.sqrt(variance.prod()))


def measure(reference, candidate, rate, band_margin=.5, level_margin=.1):
    a, ta = powers(reference, rate)
    b, tb = powers(candidate, rate)
    return measure_powers(a, ta, b, tb, rate, stereo_correlation(reference),
                          stereo_correlation(candidate), band_margin, level_margin)


def measure_powers(a, ta, b, tb, rate, reference_correlation, candidate_correlation,
                   band_margin=.5, level_margin=.1):
    """Apply the same screen to retained two-second power summaries.

    This permits one temporary render at a time without retaining long WAVs.
    The band powers, total powers and correlation are sufficient for this
    stationary screen; they do not preserve transient or waveform information.
    """
    for bands, total in [(a, ta), (b, tb)]:
        if bands.shape != (len(total), len(CENTRES), 2) or total.shape != (len(total), 2) or len(total) < 20:
            raise ValueError('Invalid power summary extent')
        if not np.isfinite(bands).all() or not np.isfinite(total).all() or np.any(bands < 0) or np.any(total < 0):
            raise ValueError('Invalid power summary values')
    if min(float(np.min(ta.mean(axis=0))), float(np.min(tb.mean(axis=0)))) <= 1e-20:
        raise ValueError('Both channels must contain non-silent noise')
    delta, half, passed = interval(a, b, band_margin)
    level, level_half, level_pass = interval(ta, tb, level_margin)
    meaningful = a.mean(axis=0) >= ta.mean(axis=0)[None, :] * 1e-4
    any_different = np.any((np.abs(delta)-half > band_margin)[meaningful]) or np.any(np.abs(level)-level_half > level_margin)
    verdict = 'pass' if np.all(passed[meaningful]) and np.all(level_pass) else 'different' if any_different else 'inconclusive'
    rows = []
    for i, center in enumerate(CENTRES):
        rows.append({'centre_hz': center, 'channels': [{'channel': channel,
            'meaningful': bool(meaningful[i, ch]), 'candidate_minus_reference_db': float(delta[i, ch]),
            'approximate_99pct_interval_db': [float(delta[i, ch]-half[i, ch]), float(delta[i, ch]+half[i, ch])],
            'equivalence_screen_passed': bool(passed[i, ch]) if meaningful[i, ch] else None}
            for ch, channel in enumerate(('left', 'right'))]})
    return {'kind': 'stationary-noise-statistical-screen', 'sample_rate': rate,
            'verdict': verdict,
            'block_seconds': 2, 'reference_blocks': len(a), 'candidate_blocks': len(b),
            'confidence_multiplier': 3.0,
            'band_equivalence_margin_db': band_margin, 'level_equivalence_margin_db': level_margin,
            'meaningful_band_floor_relative_to_total_power_db': -40,
            'whole_level': [{'channel': channel, 'candidate_minus_reference_db': float(level[ch]),
                'approximate_99pct_interval_db': [float(level[ch]-level_half[ch]), float(level[ch]+level_half[ch])],
                'equivalence_screen_passed': bool(level_pass[ch])} for ch, channel in enumerate(('left', 'right'))],
            'bands': rows, 'all_meaningful_bands_passed': bool(np.all(passed[meaningful])),
            'whole_level_passed': bool(np.all(level_pass)),
            'stereo_zero_lag_correlation': {'reference': reference_correlation,
                                          'candidate': candidate_correlation},
            'limitations': ['Approximate statistical intervals, not exact coverage guarantees.',
                'Stationarity and sufficient block independence must be checked separately.',
                'No sample-null or general similarity percentage is assigned.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('candidate', type=Path)
    p.add_argument('--start', type=float, default=2)
    p.add_argument('--duration', type=float, default=120)
    p.add_argument('--calibration', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    args = p.parse_args()
    rate, reference = float_wav(args.reference)
    other_rate, candidate = float_wav(args.candidate)
    cal = json.loads(args.calibration.read_text())
    if rate != other_rate or rate != cal['sample_rate'] or cal['verified'] is not True or cal['eligible_for_review'] is not True:
        raise ValueError('Reviewed calibration and matching sample rates required')
    delay = cal['candidate_delay_frames']
    if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not np.isfinite(delay) or delay != round(delay):
        raise ValueError('This statistical screen currently supports integer route delay only')
    start, count = round(args.start*rate), round(args.duration*rate)
    candidate_start = start + int(delay)
    if min(start, candidate_start) < 0 or start+count > len(reference) or candidate_start+count > len(candidate):
        raise ValueError('Stationary interval falls outside capture')
    result = measure(reference[start:start+count], candidate[candidate_start:candidate_start+count], rate)
    result |= {'reference_sha256': sha256(args.reference), 'candidate_sha256': sha256(args.candidate),
               'calibration_sha256': sha256(args.calibration), 'start_seconds': args.start,
               'duration_seconds': args.duration, 'candidate_delay_frames': delay}
    save_json(args.report, result)
    print(json.dumps({key: result[key] for key in ('all_meaningful_bands_passed', 'whole_level_passed', 'whole_level')}, indent=2))


if __name__ == '__main__':
    main()
