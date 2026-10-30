#!/usr/bin/env python3
"""Recompute every drum window independently, including retained failed predictions."""
import argparse
import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tools import rmx_drum_combos as combos
from tools import rmx_drum_performance as performance
from tools import rmx_drum_user_match as user
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory


def independent(reference, candidate):
    a = np.asarray(reference, dtype=np.float64); b = np.asarray(candidate, dtype=np.float64)
    require(a.shape == b.shape and len(a) and np.isfinite(a).all() and np.isfinite(b).all(), 'Invalid audit audio')
    rows = []
    for channel in range(2):
        energy = float(np.dot(a[:, channel], a[:, channel])); delta = b[:, channel] - a[:, channel]
        error = float(np.dot(delta, delta)); absolute = float(np.sqrt(error / len(a)))
        relative = float(np.sqrt(error / energy)) if energy > 1e-20 else None
        passed = relative <= .01 if relative is not None else absolute <= 1e-8
        rows.append(dict(relative_rms_error=relative, absolute_error_rms=absolute, passed=passed))
    return dict(passed=all(c['passed'] for c in rows), channels=rows)


def read_retained(path, digest):
    if path.exists():
        require(sha256(path) == digest, 'Retained WAV changed'); return float_wav(path)
    archive = path.with_suffix('.wav.gz')
    with gzip.open(archive, 'rb') as stream: data = stream.read()
    require(hashlib.sha256(data).hexdigest() == digest, 'Lossless WAV changed')
    with tempfile.TemporaryDirectory(prefix='rmx-drum-audit-') as folder:
        plain = Path(folder) / 'audio.wav'; plain.write_bytes(data); return float_wav(plain)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, action='append', required=True)
    parser.add_argument('--original-root', type=Path, required=True)
    parser.add_argument('--host', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args(); root = new_directory(a.output); rows = []; reports = {}
    for report_path in a.report:
        report = json.loads(report_path.read_text()); reports[str(report_path.resolve())] = sha256(report_path)
        custom = report['kind'] == 'rmx220-drum-user-settings-comparison'
        combined = report['kind'] == 'rmx220-drum-combo-comparison'
        # The comparison stores the capture location in Original provenance only
        # indirectly. Match the immutable matrix via its exact case names and receipt.
        original_root = a.original_root
        matches = []
        wanted = [c['case'] for c in report['cases']]
        for path in original_root.glob('*/matrix.json'):
            matrix = json.loads(path.read_text())
            if not isinstance(matrix, dict) or not isinstance(matrix.get('cases'), list) or not matrix['cases']:
                continue
            if not all(isinstance(c, dict) and 'name' in c and 'receipt_sha256' in c for c in matrix['cases']):
                continue
            if [c['name'] for c in matrix['cases']] == wanted and all(c['receipt_sha256'] == r['receipt_sha256'] for c, r in zip(matrix['cases'], report['cases'], strict=True)):
                matches.append((path.parent, matrix))
        require(len(matches) == 1, 'Missing/ambiguous Original matrix')
        session, matrix = matches[0]
        module = combos if combined else user if custom else performance
        cases = [{k: v for k, v in c.items() if k != 'receipt_sha256'} for c in matrix['cases']] if custom or combined else performance.recipe(matrix['stage'])
        for case, previous in zip(cases, report['cases'], strict=True):
            original, provenance = module.original(SimpleNamespace(session=session, host=a.host), case)
            require(all(previous[k] == value for k, value in provenance.items()), 'Original provenance differs')
            path = report_path.parent / (case['name'] + '.wav'); rate, candidate = read_retained(path, previous['candidate_sha256'])
            require(rate == 48000 and candidate.shape == original.shape, 'Candidate extent differs')
            asan_path = report_path.parent / (case['name'] + '-asan.wav')
            asan_rate, sanitized = read_retained(asan_path, previous['candidate_sha256'])
            require(asan_rate == rate and np.array_equal(candidate.view('u4'), sanitized.view('u4')) and previous['sanitizer_byte_identical'], 'Sanitizer audio differs')
            x, y = original[32:], candidate[32:]; windows = []
            for window in previous['windows']:
                start, stop = window['start'], window['stop']; score = independent(x[start:stop], y[start:stop]); old = window['score']
                require(score['passed'] == old['passed'], 'Independent window verdict differs')
                for new_channel, old_channel in zip(score['channels'], old['channels'], strict=True):
                    for key in ['relative_rms_error', 'absolute_error_rms']:
                        left, right = new_channel[key], old_channel[key]
                        require((left is None and right is None) or (left is not None and right is not None and abs(left - right) <= 1e-11 * max(1, abs(right))), 'Independent arithmetic differs')
                windows.append(dict(start=start, stop=stop, kind=window['kind'], score=score))
            wet_windows = []
            if previous.get('wet_windows'):
                baseline = next(row for row in report['cases'] if row['case'] == previous['baseline'])
                baseline_case = next(c for c in cases if c['name'] == baseline['case'])
                reference_dry, _ = module.original(SimpleNamespace(session=session, host=a.host), baseline_case)
                dry_rate, candidate_dry = read_retained(report_path.parent / (baseline['case'] + '.wav'), baseline['candidate_sha256'])
                require(dry_rate == rate, 'Wet baseline rate differs')
                reference_wet = x.astype(float) - reference_dry[32:]
                candidate_wet = y.astype(float) - candidate_dry[32:]
                for window in previous['wet_windows']:
                    start, stop = window['start'], window['stop']; score = independent(reference_wet[start:stop], candidate_wet[start:stop])
                    require(score['passed'] == window['score']['passed'], 'Independent wet verdict differs')
                    for new_channel, old_channel in zip(score['channels'], window['score']['channels'], strict=True):
                        for key in ['relative_rms_error', 'absolute_error_rms']:
                            left, right = new_channel[key], old_channel[key]
                            require((left is None and right is None) or (left is not None and right is not None and abs(left - right) <= 1e-11 * max(1, abs(right))), 'Independent wet arithmetic differs')
                    wet_windows.append(dict(start=start, stop=stop, kind=window['kind'], score=score))
            require(all(w['score']['passed'] for w in windows + wet_windows) == previous['passed'], 'Aggregate verdict differs')
            negatives = {'silence': np.zeros_like(x), 'polarity': -x, 'right-channel-silence': np.column_stack((x[:, 0], np.zeros(len(x)))),
                '32-frame-shift': np.vstack((np.zeros((32, 2)), x[:-32])), '2-percent-gain': x.astype(float) * 1.02}
            rejected = {name: not independent(x, audio)['passed'] for name, audio in negatives.items()}
            require(all(rejected.values()), 'Independent gate accepted a negative control')
            rows.append(dict(case=case['name'], comparison_sha256=reports[str(report_path.resolve())], passed=previous['passed'], windows=windows, wet_windows=wet_windows,
                negative_controls_rejected=rejected, complete_sanitizer_wav_byte_identity=True, original_receipt_sha256=provenance['receipt_sha256']))
            print('AUDITED', case['name'], previous['passed'], flush=True)
    require(all(sha256(Path(path)) == h for path, h in reports.items()), 'Comparison changed during audit')
    save_json(root / 'verification.json', dict(kind='rmx220-drum-independent-window-audit', verification_passed=True,
        audio_passed=all(r['passed'] for r in rows), programs=len(rows), passing_programs=sum(r['passed'] for r in rows), cases=rows,
        comparisons_sha256=reports, verifier_sha256=sha256(Path(__file__)), host_sha256=sha256(a.host),
        scope='Independent float64 dot-product arithmetic, every declared native reference window, exact Original provenance and complete native/sanitizer WAV identity. Five whole-output negative controls per program. A verified failed prediction remains failed.'))


if __name__ == '__main__': main()
