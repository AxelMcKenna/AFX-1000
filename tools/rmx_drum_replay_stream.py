#!/usr/bin/env python3
"""Transfer published drum gates through bounded whole-WAV byte replays.

The Original audio was pruned at the user's request. This verifies archived
metadata and exact equality to qualified candidate output, without claiming to
reread deleted reference audio or calling these existing programs new holdouts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
import subprocess

import numpy as np

from tools import rmx_drum_combos as combos
from tools import rmx_drum_performance as performance
from tools import rmx_drum_user_match as user
from tools import rmx_drum_gestures as gestures
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import require
from tools.rmx_noise_stream import RenderSpace


class MetadataArchive:
    def __init__(self, path):
        self.file = zipfile.ZipFile(path)
        index = json.loads(self.file.read('index.json'))
        self.paths = {r['source']: r for r in index['paths']}
        self.objects = index['objects']

    def read(self, path, expected=None):
        row = self.paths[str(path)]
        data = self.file.read(self.objects[row['sha256']]['member'])
        require(hashlib.sha256(data).hexdigest() == row['sha256'] and (expected is None or row['sha256'] == expected), 'Archived metadata digest differs')
        return data

    def document(self, path, expected=None): return json.loads(self.read(path, expected))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['archive', 'performance', 'user', 'sanitizer-performance', 'sanitizer-user', 'output']: p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--gesture-parent', type=Path)
    p.add_argument('--temp-root', type=Path, default=Path('/private/tmp')); a = p.parse_args()
    require(not a.output.exists(), 'Report already exists'); a.output.parent.mkdir(parents=True, exist_ok=True)
    bound = performance.bindings() | user.bindings() | gestures.bindings() | {'tools/rmx_drum_replay_stream.py': sha256(Path(__file__))}
    binary_hashes = {k: sha256(getattr(a, k)) for k in ['performance', 'user', 'sanitizer_performance', 'sanitizer_user']}
    for k in binary_hashes:
        symbols = subprocess.check_output(['nm', '-C', str(getattr(a, k))], text=True)
        require('rmx::Engine::process(' in symbols and (not k.startswith('sanitizer') or '___asan_init' in symbols and '___ubsan_handle_' in symbols), 'Fixture lacks actual Engine/sanitizers')
    archive = MetadataArchive(a.archive); base = Path('/Users/axelmckrnna/dev/rmx-publish/build/artifacts/research')
    matrices = []
    for path in archive.paths:
        item = Path(path)
        if item.name == 'matrix.json' and item.parent.parent == base and item.parent.name.startswith(('rmx-drum-', 'rmx-gesture-')):
            data = archive.document(path)
            if isinstance(data, dict) and data.get('cases'): matrices.append((item.parent, data))
    jobs = []; parents = {}
    for filename, combined in [('2026-10-30-drum-performance-validation.json', False), ('2026-10-30-drum-combo-validation.json', True)]:
        path = Path('research/audio/measurements')/filename; parent = json.loads(path.read_text()); require(parent['passed'], 'Parent checkpoint failed'); parents[filename] = sha256(path)
        for label, info in parent['reports'].items():
            selected = (label.startswith('native-') or label.startswith('fresh-') and label != 'fresh-proof') if combined else (label.startswith('native-') or label in ['user-profiles', 'user-fresh', 'user-fresh2'])
            if not selected: continue
            report_path = info['source_path'] if combined else info['original_report_path']
            report_hash = info['source_sha256'] if combined else info['original_report_sha256']
            report = archive.document(report_path, report_hash); require(report['passed'], 'Parent report failed')
            matches = [(directory, data) for directory, data in matrices if [c['name'] for c in data['cases']] == [c['case'] for c in report['cases']] and all(c['receipt_sha256'] == r['receipt_sha256'] for c, r in zip(data['cases'], report['cases'], strict=True))]
            require(len(matches) == 1, 'Missing/ambiguous archived Original matrix'); directory, matrix = matches[0]
            module = combos if combined else user if label.startswith('user-') else performance
            for c, row in zip(matrix['cases'], report['cases'], strict=True):
                jobs.append((label, module, directory, {k: v for k, v in c.items() if k != 'receipt_sha256'}, row, report_hash, report_path))
    require(len(jobs) == 708, 'Published parent program count differs')
    if a.gesture_parent:
        parent = json.loads(a.gesture_parent.read_text()); parent_hash = sha256(a.gesture_parent)
        require(parent_hash in archive.objects and parent['verification_passed'] and parent['audio_passed'] and parent['programs'] == 240,
                'Gesture audit differs from verified retained metadata')
        parents['gesture-audit'] = parent_hash
        for report_path, report_hash in parent['comparisons_sha256'].items():
            report = archive.document(report_path, report_hash); require(report['passed'], 'Gesture comparison failed')
            matches = [(directory, data) for directory, data in matrices if [c['name'] for c in data['cases']] == [c['case'] for c in report['cases']] and all(c['receipt_sha256'] == r['receipt_sha256'] for c, r in zip(data['cases'], report['cases'], strict=True))]
            require(len(matches) == 1, 'Missing/ambiguous gesture matrix'); directory, matrix = matches[0]
            for c, row in zip(matrix['cases'], report['cases'], strict=True):
                jobs.append(('gesture-'+report['stage'], gestures, directory, {k: v for k, v in c.items() if k != 'receipt_sha256'}, row, report_hash, report_path))
        require(len(jobs) == 948, 'Gesture coverage differs')
    rows = []; peak = 0
    with tempfile.TemporaryDirectory(prefix='rmx-bounded-drums-', dir=a.temp_root) as temporary:
        root = Path(temporary); space = RenderSpace(root); write_wav(root/'silence.wav', 48000, np.zeros(480000*2)); silence_hash = sha256(root/'silence.wav')
        for i, (label, module, directory, c, old, report_hash, report_path) in enumerate(jobs):
            require(old['passed'] and old['input_sha256'] == silence_hash, 'Parent input/verdict differs')
            program = module.schedule(c)
            require(hashlib.sha256(program.encode()).hexdigest() == old['schedule_sha256'], 'Recreated schedule differs')
            require(archive.read(Path(report_path).parent/(c['name']+'.tsv')).decode() == program, 'Archived schedule differs')
            receipt = archive.document(directory/c['name']/'receipt.json', old['receipt_sha256'])
            require(receipt['complete'] and all(receipt[k] == old[key] for k, key in [('output_sha256', 'output_sha256'), ('input_sha256', 'input_sha256'), ('plan_sha256', 'plan_sha256')]), 'Archived Original provenance differs')
            with tempfile.TemporaryDirectory(prefix='case-', dir=root) as folder:
                folder = Path(folder); schedule = folder/'program.tsv'; schedule.write_text(program)
                native = a.user if module is user else a.performance; sanitized = a.sanitizer_user if module is user else a.sanitizer_performance
                for name, binary in [('native', native), ('sanitized', sanitized)]:
                    wave = folder/(name+'.wav'); dry = folder/(name+'-dry.wav')
                    space.run([binary, root/'silence.wav', wave, schedule, dry], sanitized=name == 'sanitized')
                    require(sha256(wave) == old['candidate_sha256'] and sha256(dry) == old['dry_sha256'], 'Current output differs from qualified parent: '+c['name'])
                    wave.unlink(); dry.unlink()
                peak = max(peak, space.peak)
            rows.append(dict(case=c['name'], group=label, candidate_sha256=old['candidate_sha256'], dry_sha256=old['dry_sha256'],
                parent_report_sha256=report_hash, original_receipt_sha256=old['receipt_sha256'], complete_native_sanitizer_parent_wav_identity=True, passed=True))
            if i % 25 == 0 or i+1 == len(jobs): print('UNCHANGED', i+1, '/', len(jobs), c['name'], 'peakMiB', round(peak/1024**2, 1), flush=True)
    require(not root.exists() and bound == performance.bindings() | user.bindings() | gestures.bindings() | {'tools/rmx_drum_replay_stream.py': sha256(Path(__file__))}, 'Replay inputs changed or audio retained')
    require(all(sha256(getattr(a, k)) == h for k, h in binary_hashes.items()), 'Replay binary changed')
    save_json(a.output, dict(kind='rmx220-bounded-published-drum-byte-preservation', passed=True, programs=len(rows), cases=rows,
        source_sha256=bound, binaries_sha256=binary_hashes, parent_validations_sha256=parents, metadata_archive_sha256=sha256(a.archive),
        peak_temporary_bytes=peak, raw_audio_retained=False, all_temporary_directories_removed=True,
        scope='All declared previously qualified drum/profile/pattern/FX/gesture programs. Complete current optimized and ASAN audio/dry WAV bytes equal qualified parent digests. '
        'Archived recipes, schedules, receipts and prior reports verified by hash. Original WAVs were removed at user request and are not revalidated here. '
        'Prior window verdicts transfer through exact qualified candidate byte identity; no new holdout or broader-effect/hardware claim.'))
    archive.file.close()


if __name__ == '__main__': main()
