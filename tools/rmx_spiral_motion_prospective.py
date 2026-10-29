#!/usr/bin/env python3
"""Freeze fresh Spiral gestures before capture, then independently verify them."""
import argparse, concurrent.futures, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion as motion
from tools import rmx_spiral_motion_match as match
from tools.rmx_spiral_prospective import score
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_drums import require
from tools.reference_audio import save_json, sha256, write_wav
from tools.noise_statistics import float_wav


def bindings():
    return match.bindings() | {str(Path(__file__).relative_to(Path.cwd())): sha256(Path(__file__)),
                              'tools/rmx_spiral_prospective.py': sha256(Path('tools/rmx_spiral_prospective.py'))}


def source():
    rng = np.random.default_rng(0x53504d4631)
    x = np.zeros((576000, 2), dtype='<f4')
    t = np.arange(144000) / 48000
    x[48000:192000] = rng.normal(0, .009, (len(t), 2)) + np.column_stack((
        .023 * np.sin(2*np.pi*(61*t+107*t*t)), .027 * np.cos(2*np.pi*(137*t+233*t*t))))
    x[73019:89113] *= .07
    x[123113:129517] = 0
    for frame in [48017, 96131, 145007, 193013, 217001, 241019]:
        x[frame] += rng.uniform(-.23, .23, 2)
    return x


def recipe():
    rng = np.random.default_rng(0x53504d4632)
    boundary = [0, 1, 3, 4, 5, 8, 9, 16, 28, 29, 63, 64, 65, 66, 127, 128, 129, 130, 131, 192, 254, 255]
    rows = []
    for i in range(64):
        changes = []
        for j, frame in enumerate([69713, 96127, 120019, 144311, 168193, 192277, 216419, 240607, 288113, 336319]):
            controls = ['main', 'time', 'pitch', 'enabled'] if i >= 32 else [['main'], ['time'], ['pitch'], ['enabled']][(i//2) % 4]
            for control in controls:
                raw = int(j % 2 == 1) if control == 'enabled' else int(rng.choice(boundary)) if j < 6 else int(rng.integers(256))
                changes.append(dict(frame=frame, control=control, raw=raw))
        rows.append(dict(name=f'spiral-motion-fresh1-{i:03d}', direction=['up', 'down'][i % 2],
                         main=128 if i < 32 else boundary[(i-32) % len(boundary)],
                         time=0 if i < 32 else int(rng.integers(256)),
                         pitch=0 if i < 32 else int(rng.integers(256)), source='program',
                         block=[8, 17, 31, 32, 79, 127, 263, 1021, 4093, 4096][i % 10], changes=changes))
    return rows


def predict(a):
    root = new_directory(a.session); (root/'predictions').mkdir()
    bound = bindings(); binary = sha256(a.renderer)
    write_wav(root/'program.wav', 48000, source().ravel())
    outputs = {}; schedules = {}
    for c in recipe():
        plan = root/'predictions'/(c['name']+'.tsv'); plan.write_text(match.schedule(c))
        out = plan.with_suffix('.wav'); run([a.renderer, root/'program.wav', out, plan])
        outputs[c['name']] = sha256(out); schedules[c['name']] = sha256(plan)
    require(bound == bindings() and binary == sha256(a.renderer), 'Candidate changed')
    save_json(root/'prediction.json', dict(kind='spiral-motion-fresh-pre-capture-prediction', created_utc=datetime.now(timezone.utc).isoformat(),
              cases=recipe(), source_sha256=bound, renderer=str(a.renderer.resolve()), renderer_sha256=binary,
              input_sha256=sha256(root/'program.wav'), output_sha256=outputs, schedule_sha256=schedules))
    save_json(root/'prediction-chronology.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
              prediction_sha256=sha256(root/'prediction.json'), source_sha256=bound,
              originals_absent=all(not (root/c['name']).exists() for c in recipe())))


def frozen(a):
    f = json.loads((a.session/'prediction.json').read_text()); seal = json.loads((a.session/'prediction-chronology.json').read_text())
    require(f['source_sha256'] == seal['source_sha256'] == bindings() and f['cases'] == recipe() and
            sha256(Path(f['renderer'])) == f['renderer_sha256'] and sha256(a.session/'program.wav') == f['input_sha256'] and
            seal['prediction_sha256'] == sha256(a.session/'prediction.json') and seal['originals_absent'], 'Frozen prediction changed')
    for c in recipe():
        for extension, key in [('wav', 'output_sha256'), ('tsv', 'schedule_sha256')]:
            require(sha256(a.session/'predictions'/(c['name']+'.'+extension)) == f[key][c['name']], 'Frozen artifact changed')
    return f, seal


def capture(a):
    f, seal = frozen(a)
    require(all(not (a.session/c['name']).exists() for c in recipe()), 'Original already exists')
    inventory = json.loads(run([a.host, 'inventory', a.plugin])); require(all(inventory[k] == v for k,v in IDENTITY.items()), 'Wrong original')
    save_json(a.session/'inventory.json', inventory)
    def one(c):
        plan = a.session/(c['name']+'.json'); save_json(plan, motion.plan_for(c, inventory))
        run([a.host, 'render', a.plugin, a.session/'program.wav', plan, a.session/c['name'], c['block']])
        print('CAPTURED', c['name'], flush=True)
        return c | dict(receipt_sha256=sha256(a.session/c['name']/'receipt.json'))
    with concurrent.futures.ThreadPoolExecutor(4) as pool: rows = list(pool.map(one, recipe()))
    frozen(a)
    save_json(a.session/'matrix.json', dict(kind='spiral-motion-prospective-original', cases=rows, prediction_sha256=seal['prediction_sha256']))


def audit(a):
    f, seal = frozen(a); root = new_directory(a.output); bound = bindings(); san_hash = sha256(a.sanitizer)
    symbols = subprocess.check_output(['nm', '-C', str(a.sanitizer)], text=True)
    require('___asan_init' in symbols and '___ubsan_handle_' in symbols, 'Missing sanitizers')
    matrix = json.loads((a.session/'matrix.json').read_text())
    require(matrix['prediction_sha256'] == seal['prediction_sha256'] and
            [c['name'] for c in matrix['cases']] == [c['name'] for c in recipe()], 'Capture coverage differs')
    rows = []
    for c in recipe():
        receipt, x, dry_input = match.original(a, c, source())
        require(datetime.fromisoformat(seal['created_utc']) < datetime.fromisoformat(receipt['created_at_utc']), 'Original predates seal')
        path = a.session/'predictions'/(c['name']+'.tsv'); candidate = path.with_suffix('.wav')
        native = root/(c['name']+'-native.wav'); run([Path(f['renderer']), a.session/'program.wav', native, path])
        sanitized = root/(c['name']+'-sanitized.wav')
        result = subprocess.run([str(a.sanitizer), str(a.session/'program.wav'), str(sanitized), str(path)], capture_output=True, text=True,
                   env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), timeout=120)
        require(result.returncode == 0 and not result.stderr, 'Sanitizer failure: '+result.stderr)
        require(sha256(candidate) == sha256(native) == sha256(sanitized), 'Prediction/native/sanitizer WAV bytes differ')
        rate, y = float_wav(candidate); require(rate == 48000 and y.shape == x.shape, 'Candidate extent differs')
        dry = match.transport(dry_input, c['block'], c['changes'])[32:]; x = x[32:]; y = y[32:]
        windows = []
        intervals = [(0, len(x), 'complete')] + [(s, min(s+48000, len(x)), 'second') for s in range(0, len(x), 48000)]
        intervals += [(max(0, e['frame']-64), min(e['frame']+2048, len(x)), 'event') for e in c['changes']]
        for start, stop, kind in intervals:
            windows.append(dict(start=start, stop=stop, kind=kind, whole=score(x[start:stop], y[start:stop]),
                    wet=score(x[start:stop].astype(float)-dry[start:stop], y[start:stop].astype(float)-dry[start:stop])))
        passed = all(w['whole']['passed'] and w['wet']['passed'] for w in windows)
        rows.append(dict(case=c['name'], passed=passed, windows=windows, sanitizer_byte_identical=True,
                         candidate_sha256=sha256(candidate), receipt_sha256=sha256(a.session/c['name']/'receipt.json')))
        print('AUDITED', c['name'], passed, flush=True)
    require(bound == bindings() and san_hash == sha256(a.sanitizer), 'Audit inputs changed'); frozen(a)
    save_json(root/'verification.json', dict(kind='spiral-motion-prospective-independent-audit', passed=all(r['passed'] for r in rows),
              cases=rows, source_sha256=bound, renderer_sha256=f['renderer_sha256'], sanitizer_sha256=san_hash,
              prediction_sha256=seal['prediction_sha256'], scope='Default48k/120BPM input-only, one-second silent preamble; AutoButton1. Whole/wet, one-second and event windows. No cold, live-wrapper, other-profile or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    for name in ['predict', 'capture', 'audit']:
        q = sub.add_parser(name); q.add_argument('--session', type=Path, required=True)
        if name == 'predict': q.add_argument('--renderer', type=Path, required=True)
        else:
            q.add_argument('--host', type=Path, required=True)
            if name == 'capture': q.add_argument('--plugin', type=Path, required=True)
            else:
                q.add_argument('--sanitizer', type=Path, required=True); q.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); return globals()[a.command](a)


if __name__ == '__main__': raise SystemExit(main())
