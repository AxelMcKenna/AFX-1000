"""Continuous Noise statistics from bounded, overlapping capture windows."""
import subprocess

import numpy as np

from tools import noise_motion_statistics as motion
from tools import noise_random_statistics as random_stats
from tools import noise_reference_trajectory_statistics as trajectory
from tools.noise_statistics import float_wav, powers
from tools.rmx_noise_stream import drift, screen

RATE = 48000
WARMUP = 4 * RATE
OVERLAP = 128


def analyze(path, start, seconds, pattern, raw, probe=None):
    """Keep the original epoch/window boundaries, including boundary FFTs.

    ``start`` is the global start of retained stationary data. A later WAV
    includes 128 preceding frames; the first includes four seconds of warmup.
    Neither prefix is counted twice in powers or correlation.
    """
    rate, source = float_wav(path)
    if rate != RATE or start < WARMUP or start % RATE or seconds % 10:
        raise ValueError('Invalid continuous-window extent')
    prefix = WARMUP if start == WARMUP else OVERLAP
    if source.shape != (prefix + seconds * RATE, 2):
        raise ValueError('Capture window extent differs')
    audio = source.copy()
    if pattern is not None:
        for first in range(0, len(audio), RATE):
            indices = start - prefix + np.arange(first, min(first + RATE, len(audio))) - 32
            dry = pattern[indices % RATE].copy()
            dry[indices < 0] = 0
            audio[first:first + len(dry)] -= dry
    stationary = audio[prefix:]
    bands, total = powers(stationary, RATE)
    sums = np.sum(stationary, axis=0, dtype=np.float64)
    squares = np.einsum('ij,ij->j', stationary, stationary, dtype=np.float64)
    cross = np.einsum('i,i->', stationary[:, 0], stationary[:, 1], dtype=np.float64)
    moments = np.r_[len(stationary), sums, squares, cross]
    epoch_seconds = 10 if probe is not None else 2
    per_epoch = epoch_seconds * RATE // OVERLAP
    epochs = seconds // epoch_seconds
    first_index = 0 if start == WARMUP else -1
    positions = np.arange(first_index, epochs * per_epoch - 1) * OVERLAP
    if probe is None:
        labels = ((start + positions + OVERLAP) % RATE) // 12000
    else:
        request = [probe, '--bins', str(raw), 'own', str(start + int(positions[0]) + OVERLAP - 4864), str(OVERLAP), str(len(positions))]
        result = subprocess.run(list(map(str, request)), check=True, capture_output=True)
        labels = np.frombuffer(result.stdout, dtype=np.uint8)
        if result.stderr or len(labels) != len(positions) or np.any(labels > 3):
            raise ValueError('Random window labels differ')
    size = 256
    window = np.hanning(size)
    norm = np.sum(window * window)
    frequencies = np.fft.rfftfreq(size, 1 / RATE)
    masks = [(frequencies >= a) & (frequencies < b) for a, b in zip(motion.EDGES[:-1], motion.EDGES[1:])]
    pb = np.empty((epochs, 4, 6, 2))
    pt = np.empty((epochs, 4, 2))
    exposure = np.empty((epochs, 4), dtype=np.int32)
    for epoch in range(epochs):
        first = max(first_index, epoch * per_epoch - 1)
        end = (epoch + 1) * per_epoch - 1
        where = np.arange(first, end) * OVERLAP + prefix
        weighted = np.stack([audio[i:i + size] for i in where]) * window[None, :, None]
        spectrum = np.abs(np.fft.rfft(weighted, axis=1)) ** 2 * (2 / (size * norm))
        spectrum[:, 0] *= .5
        spectrum[:, -1] *= .5
        bp = np.stack([np.sum(spectrum[:, mask], axis=1) for mask in masks], axis=1)
        tp = np.sum(weighted * weighted, axis=1) / norm
        current = labels[first - first_index:end - first_index]
        for bin_index in range(4):
            keep = current == bin_index
            exposure[epoch, bin_index] = np.sum(keep)
            if not np.any(keep):
                raise ValueError('Empty control bin')
            pb[epoch, bin_index] = np.mean(bp[keep], axis=0)
            pt[epoch, bin_index] = np.mean(tp[keep], axis=0)
    return dict(bands=bands, total=total, moments=moments), dict(bands=pb, total=pt, exposure=exposure)


def combine(segments):
    moments = np.sum([s['moments'] for s, _ in segments], axis=0)
    count, left, right, ll, rr, cross = moments
    variance = np.array([ll, rr]) - np.array([left, right]) ** 2 / count
    correlation = float((cross - left * right / count) / np.sqrt(variance.prod()))
    overall = {k: np.concatenate([s[k] for s, _ in segments]) for k in ['bands', 'total']}
    overall['correlation'] = correlation
    profile = {k: np.concatenate([s[k] for _, s in segments]) for k in ['bands', 'total', 'exposure']}
    return overall, profile


def score(reference, candidate, random=False):
    r, rp = reference
    c, cp = candidate
    measure = trajectory.measure if random else screen
    profile_measure = random_stats.measure if random else motion.measure
    overall = measure(r, c)
    profile = profile_measure(rp, cp)
    n = len(rp['total']) // 3
    thirds = {label: profile_measure({k: v[first:last] for k, v in rp.items()}, {k: v[first:last] for k, v in cp.items()})['verdict']
              for label, first, last in [('early', 0, n), ('late', -n, None)]}
    no = len(r['total']) // 3
    whole = {label: measure({k: (v[first:last] if k in ['bands', 'total'] else v) for k, v in r.items()},
                            {k: (v[first:last] if k in ['bands', 'total'] else v) for k, v in c.items()})['verdict']
             for label, first, last in [('early', 0, no), ('late', -no, None)]}
    stability = dict(reference=drift(r), candidate=drift(c))
    stereo = abs(r['correlation'] - c['correlation']) <= .02
    gain = measure(r, r | dict(bands=r['bands'] * 10 ** .3, total=r['total'] * 10 ** .3))['verdict']
    pg = profile_measure(rp, rp | dict(bands=rp['bands'] * 10 ** .3, total=rp['total'] * 10 ** .3))['verdict']
    if gain != 'different' or pg != 'different':
        raise ValueError('A gain negative passed')
    passed = overall['verdict'] == profile['verdict'] == 'pass' and stereo and all(v == 'pass' for v in thirds.values())
    passed &= all(v == 'pass' for v in (whole if random else stability).values())
    return dict(passed=passed, statistics=overall, profile=profile, profile_thirds=thirds, overall_thirds=whole,
                stationarity=stability, stereo_correlation_passed=stereo, required_gain_negatives_rejected=True,
                stationarity_is_gate=not random)
