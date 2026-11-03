#!/usr/bin/env python3
"""Independent arithmetic and coverage audit for continuous Noise windows."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import IDENTITY
from tools.rmx_noise_power_audit import verdict
from tools.rmx_noise_motion_power_audit import phase
from tools.rmx_noise_random_reference_audit import paired
from tools import rmx_noise_user as noise


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['report', 'plan', 'probe', 'sanitizer-probe', 'output']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    report, declared = load(a.report), load(a.plan)
    if report['kind'] != 'bounded-continuous-noise-validation' or not report['verification_passed'] or report['raw_audio_retained'] or not report['all_temporary_directories_removed'] or report['peak_temporary_bytes'] > 512 * 1024 ** 2:
        raise ValueError('Invalid continuous campaign')
    if sha256(a.plan) != report['declared_plan_sha256'] or declared['stationary_seconds'] != 7140 or declared['window_seconds'] != 1190 or declared['source_sha256'] != report['source_sha256'] or declared['binary_sha256'] != report['binary_sha256']:
        raise ValueError('Predeclared source, binaries or horizon differ')
    for key, margin in dict(band_db=.5, level_db=.1, correlation=.02, confidence_multiplier=3, meaningful_floor_db=-40).items():
        if declared['limits'][key] != margin:
            raise ValueError('Statistical margin changed')
    if [c['name'] for c in declared['cases']] != [c['name'] for c in report['cases']]:
        raise ValueError('Declared cases differ')
    rows = []
    for c in report['cases']:
        random = c['wave'] == 3
        batch_program = noise.schedule(c | dict(frames=7144 * 48000)).replace('RMX_NOISE_USER 2', 'RMX_NOISE_USER 5') + f'1 {4 * 48000} {1190 * 48000} 6\n'
        if not c['native_continuous_single_pass'] or hashlib.sha256(batch_program.encode()).hexdigest() != c['native_batch_schedule_sha256']:
            raise ValueError('Native continuous-run schedule differs')
        position = 4 * 48000
        if len(c['segments']) != 6 or c['stationary_seconds'] != 7140:
            raise ValueError('Continuous horizon is incomplete')
        for index, segment in enumerate(c['segments']):
            prefix = 4 * 48000 if index == 0 else 128
            frames = 1190 * 48000
            receipt, plan = segment['original_receipt'], segment['plan']
            if segment['stationary_start_frame'] != position or segment['stationary_frames'] != frames or segment['captured_start_frame'] != position - prefix or segment['captured_frames'] != frames + prefix or segment['processing_frames'] != position + frames or not segment['complete_retained_native_sanitizer_wav_identity']:
                raise ValueError('Windows have a gap, excess overlap or parity failure')
            window = plan['render_window']
            if window != dict(processing_frames=position + frames, start_frame=position - prefix, frames=frames + prefix, repeat_input=True) or plan['tail_seconds'] != 0:
                raise ValueError('Actual render plan differs from declared extent')
            plan_digest = hashlib.sha256((json.dumps(plan, indent=2, allow_nan=False) + '\n').encode()).hexdigest()
            if receipt['plan_sha256'] != plan_digest or not receipt['complete'] or receipt['role'] != 'reference' or not receipt['offline'] or receipt['host_sha256'] != report['binary_sha256']['host'] or receipt['frames'] != frames + prefix or receipt['processing_frames'] != position + frames or receipt['capture_start_frame'] != position - prefix or not receipt['input_repeated'] or receipt['sample_rate'] != 48000 or receipt['maximum_block_size'] != c['block']:
                raise ValueError('Original receipt/plan binding differs')
            if any(receipt['plugin'][k] != value for k, value in IDENTITY.items()) or not any(member['sha256'] == 'dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced' for member in receipt['plugin']['binary_files']):
                raise ValueError('Original identity or executable differs')
            position += frames
        path = Path(c['summary']['path'])
        if not path.is_absolute():
            path = a.report.parent / path
        if sha256(path) != c['summary']['sha256']:
            raise ValueError('Power summary changed')
        with np.load(path, allow_pickle=False) as z:
            rb, rt, cb, ct = [z[k] for k in ['reference_bands', 'reference_total', 'candidate_bands', 'candidate_total']]
            x, tx, y, ty = [z[k] for k in ['reference_profile_bands', 'reference_profile_total', 'candidate_profile_bands', 'candidate_profile_total']]
            epochs = 714 if random else 3570
            if rb.shape != cb.shape or rb.shape != (3570, 30, 2) or rt.shape != ct.shape or rt.shape != (3570, 2) or x.shape != y.shape or x.shape != (epochs, 4, 6, 2) or tx.shape != ty.shape or tx.shape != (epochs, 4, 2):
                raise ValueError('Continuous power dimensions differ')
            if any(not np.isfinite(v).all() or np.min(v) < 0 for v in [rb, rt, cb, ct, x, tx, y, ty]):
                raise ValueError('Invalid retained powers')
            exposure = z['reference_profile_exposure']
            expected = np.full(epochs, 3750 if random else 750)
            expected[0] -= 1
            if exposure.shape != (epochs, 4) or not np.array_equal(exposure, z['candidate_profile_exposure']) or np.any(exposure <= 0) or not np.array_equal(exposure.sum(axis=1), expected):
                raise ValueError('FFT boundary windows are missing or counted twice')
            compare = paired if random else verdict
            result = compare(rb, rt, cb, ct)
            ov, delta, half, level, lh = result[:5]
            if ov != c['statistics']['verdict']:
                raise ValueError('Overall verdict differs')
            errors = []
            if random:
                for value, key in [(delta, 'mean_power_ratio_db'), (half, 'band_interval_half_db'), (level, 'whole_level_ratio_db'), (lh, 'whole_level_interval_half_db')]:
                    errors.append(float(np.max(np.abs(value - np.asarray(c['statistics'][key])))))
                if not np.array_equal(result[5], c['statistics']['meaningful_bands']):
                    raise ValueError('Random band mask differs')
            else:
                for band, old in enumerate(c['statistics']['bands']):
                    for ch, value in enumerate(old['channels']):
                        errors.append(max(abs(value['candidate_minus_reference_db'] - delta[band, ch]), float(np.max(np.abs(np.asarray(value['approximate_99pct_interval_db']) - [delta[band, ch] - half[band, ch], delta[band, ch] + half[band, ch]])))))
                for ch, value in enumerate(c['statistics']['whole_level']):
                    errors.append(max(abs(value['candidate_minus_reference_db'] - level[ch]), float(np.max(np.abs(np.asarray(value['approximate_99pct_interval_db']) - [level[ch] - lh[ch], level[ch] + lh[ch]])))))
            pv, pd, ph, pl, plh, mask = phase(x, tx, y, ty)
            for value, key in [(pd, 'mean_paired_band_log_ratio_db'), (ph, 'band_interval_half_db'), (pl, 'mean_paired_level_log_ratio_db'), (plh, 'level_interval_half_db')]:
                errors.append(float(np.max(np.abs(value - np.asarray(c['profile'][key])))))
            if max(errors) > 1e-10 or pv != c['profile']['verdict'] or not np.array_equal(mask, c['profile']['meaningful_bands']):
                raise ValueError('Profile/interval arithmetic differs')
            n, no = epochs // 3, len(rt) // 3
            thirds = dict(early=phase(x[:n], tx[:n], y[:n], ty[:n])[0], late=phase(x[-n:], tx[-n:], y[-n:], ty[-n:])[0])
            whole = dict(early=compare(rb[:no], rt[:no], cb[:no], ct[:no])[0], late=compare(rb[-no:], rt[-no:], cb[-no:], ct[-no:])[0])
            stability = {name: verdict(b[:no], t[:no], b[-no:], t[-no:])[0] for name, b, t in [('reference', rb, rt), ('candidate', cb, ct)]}
            stereo = abs(float(z['reference_correlation']) - float(z['candidate_correlation'])) <= .02
            qualified = ov == pv == 'pass' and stereo and all(value == 'pass' for value in thirds.values()) and all(value == 'pass' for value in (whole if random else stability).values())
            if thirds != c['profile_thirds'] or whole != c['overall_thirds'] or stability != c['stationarity'] or stereo != c['stereo_correlation_passed'] or qualified != c['passed'] or c['stationarity_is_gate'] == random:
                raise ValueError('Aggregate or subwindow verdict differs')
            if compare(rb, rt, rb * 10 ** .3, rt * 10 ** .3)[0] != 'different' or phase(x, tx, x * 10 ** .3, tx * 10 ** .3)[0] != 'different' or not c['required_gain_negatives_rejected']:
                raise ValueError('Gain negatives were not rejected')
            if random:
                observation = c['control_observation']
                targets = z['default_targets'].astype('<f4').tobytes()
                if not observation['full_default_native_sanitizer_target_identity'] or observation['draws'] != len(targets) // 4 or hashlib.sha256(targets).hexdigest() != observation['target_sha256'] or observation['ordinary_and_observed_sha256']['audio.wav'] != c['segments'][-1]['original_receipt']['output_sha256']:
                    raise ValueError('Shared Random trajectory prerequisite differs')
                blocks = (position - 4832) // 32
                for key, probe in [('probe', a.probe), ('sanitizer_probe', a.sanitizer_probe)]:
                    if sha256(probe) != report['binary_sha256'][key]:
                        raise ValueError('Control probe changed')
                    result = subprocess.run([str(probe), str(c['sub2']), str(blocks), 'own', 'targets'], check=True, capture_output=True)
                    if result.stderr or result.stdout != targets:
                        raise ValueError('Observed long target trajectory does not replay')
            rows.append(dict(case=c['name'], qualified=qualified, overall=ov, profile=pv, profile_thirds=thirds, overall_thirds=whole,
                stationarity=stability, maximum_arithmetic_difference=max(errors), continuous_seconds=7140, exact_FFT_boundary_coverage=True,
                unchanged_gain_negatives_rejected=True, summary_sha256=sha256(path)))
    if report['passed'] != all(r['qualified'] for r in rows):
        raise ValueError('Campaign verdict differs')
    save_json(a.output, dict(kind='independent-continuous-noise-power-audit', verification_passed=True, cases=rows,
        report_sha256=sha256(a.report), declared_plan_sha256=sha256(a.plan), auditor_sha256=sha256(Path(__file__)),
        scope='Independent sums/einsum HAC, ratio/conditional-profile intervals, masks, unchanged gates and negatives; all6 capture spans, receipts, FFT exposure coverage and full observed Random targets. No deleted audio is reread or new reference claim created.'))


if __name__ == '__main__':
    main()
