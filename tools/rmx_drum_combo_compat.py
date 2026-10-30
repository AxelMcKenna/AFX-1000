#!/usr/bin/env python3
"""Transfer earlier drum gates only after complete current native/ASAN byte identity."""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from tools import rmx_drum_performance as performance
from tools import rmx_drum_user_match as user
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory


def retain(old, destination, digest):
    if old.exists():
        require(sha256(old) == digest, 'Parent WAV changed')
        with old.open('rb') as source, destination.open('xb') as file:
            with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0, compresslevel=2) as compressed:
                shutil.copyfileobj(source, compressed)
    else:
        archive = old.with_suffix('.wav.gz')
        with gzip.open(archive, 'rb') as file: require(hashlib.file_digest(file, 'sha256').hexdigest() == digest, 'Parent compressed WAV changed')
        if os.uname().sysname == 'Darwin': subprocess.run(['/bin/cp', '-c', str(archive), str(destination)], check=True)
        else: shutil.copyfile(archive, destination)
    with gzip.open(destination, 'rb') as file: require(hashlib.file_digest(file, 'sha256').hexdigest() == digest, 'Retained current WAV changed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['parent', 'original-root', 'host', 'performance', 'user', 'sanitizer-performance', 'sanitizer-user', 'output']: p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--workers', type=int, default=2); a = p.parse_args(); require(1 <= a.workers <= 4, 'Invalid workers')
    bound = performance.bindings() | user.bindings(); own = sha256(Path(__file__)); parent_hash = sha256(a.parent)
    parent = json.loads(a.parent.read_text()); root = new_directory(a.output); binaries = {name: sha256(getattr(a, name)) for name in ['performance', 'user', 'sanitizer_performance', 'sanitizer_user']}
    for name in binaries:
        symbols = subprocess.check_output(['nm', '-C', str(getattr(a, name))], text=True)
        require('rmx::Engine::process(' in symbols, 'Fixture lacks actual Engine')
        if name.startswith('sanitizer'): require('___asan_init' in symbols and '___ubsan_handle_' in symbols, 'Missing sanitizers')
    jobs = []; reports = {}; labels = [k for k in parent['reports'] if k.startswith('native-') or k in ['user-profiles', 'user-fresh', 'user-fresh2']]
    for label in labels:
        info = parent['reports'][label]; path = Path(info['original_report_path']); require(sha256(path) == info['original_report_sha256'], 'Published parent changed')
        report = json.loads(path.read_text()); require(report['passed'], 'Parent failed'); reports[label] = sha256(path)
        matches = []
        for matrix in a.original_root.glob('rmx-drum-*/matrix.json'):
            data = json.loads(matrix.read_text())
            if [c['name'] for c in data['cases']] == [c['case'] for c in report['cases']] and all(c['receipt_sha256'] == r['receipt_sha256'] for c, r in zip(data['cases'], report['cases'], strict=True)): matches.append((matrix.parent, data))
        require(len(matches) == 1, 'Missing/ambiguous Original matrix'); session, matrix = matches[0]
        for c, old in zip(matrix['cases'], report['cases'], strict=True): jobs.append((label, path, session, {k: v for k, v in c.items() if k != 'receipt_sha256'}, old))
    require(len(jobs) == 504, 'Prior coverage changed')
    def one(job):
        label, path, session, c, old = job; custom = label.startswith('user-'); module = user if custom else performance
        _, provenance = module.original(SimpleNamespace(session=session, host=a.host), c)
        require(all(old[k] == value for k, value in provenance.items()), 'Parent provenance differs')
        native = a.user if custom else a.performance; sanitized = a.sanitizer_user if custom else a.sanitizer_performance
        schedule = module.schedule(c); old_schedule = path.parent / (c['name'] + '.tsv')
        require(schedule == old_schedule.read_text() and sha256(old_schedule) == old['schedule_sha256'], 'Schedule changed')
        with tempfile.TemporaryDirectory(prefix='rmx-drum-compat-') as temp:
            temp = Path(temp); program = temp / 'schedule.tsv'; program.write_text(schedule)
            outputs = []
            for name, binary in [('native', native), ('asan', sanitized)]:
                output = temp / (name + '.wav'); dry = temp / (name + '-dry.wav')
                result = subprocess.run([str(binary), str(session / 'silence.wav'), str(output), str(program), str(dry)], capture_output=True, text=True,
                    env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), timeout=120)
                require(result.returncode == 0 and not result.stderr, 'Replay failure: ' + result.stderr)
                require(sha256(output) == old['candidate_sha256'] and sha256(dry) == old['dry_sha256'], 'Current audio differs from parent: ' + c['name']); outputs += [output, dry]
            folder = root / label; folder.mkdir(exist_ok=True)
            retain(path.parent / (c['name'] + '.wav'), folder / (c['name'] + '.wav.gz'), old['candidate_sha256'])
            retain(path.parent / (c['name'] + '-dry.wav'), folder / (c['name'] + '-dry.wav.gz'), old['dry_sha256'])
        print('UNCHANGED', label, c['name'], flush=True)
        return provenance | dict(group=label, passed=True, parent_report_sha256=reports[label], candidate_sha256=old['candidate_sha256'], dry_sha256=old['dry_sha256'], complete_native_parent_wav_byte_identity=True, complete_sanitizer_wav_byte_identity=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool: rows = list(pool.map(one, jobs))
    require(bound == performance.bindings() | user.bindings() and own == sha256(Path(__file__)) and parent_hash == sha256(a.parent), 'Compatibility inputs changed')
    require(all(sha256(getattr(a, name)) == digest for name, digest in binaries.items()), 'Compatibility binaries changed')
    save_json(root / 'verification.json', dict(kind='rmx220-drum-combo-prior-drum-byte-preservation', passed=True, programs=504, cases=rows,
        source_sha256=bound, verifier_sha256=own, parent_validation_sha256=parent_hash, parent_reports_sha256=reports, binaries_sha256=binaries,
        scope='All504 earlier drum/profile/performance programs. Current actual Engine and ASAN complete WAVs and dry traces equal qualified parent bytes. Original provenance is rechecked. Current outputs retained losslessly with decompressed SHA256 checks. Existing gates transfer; no new capture or broader FX/hardware claim.'))


if __name__ == '__main__': main()
