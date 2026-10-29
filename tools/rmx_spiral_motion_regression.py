#!/usr/bin/env python3
"""Recheck existing Spiral motion references without relabeling them prospective."""
import argparse, json, os, subprocess
from pathlib import Path
from tools import rmx_spiral_motion_match as match
from tools.rmx_spiral_prospective import score
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory, run
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256


def bindings():
    return match.bindings() | {n:sha256(Path(n)) for n in ['tools/rmx_spiral_motion_regression.py','tools/rmx_spiral_prospective.py']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['session', 'host', 'renderer', 'sanitizer', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--engine',action='store_true')
    a = p.parse_args(); root = new_directory(a.output); bound = bindings()
    own = sha256(Path(__file__)); binaries = {str(b): sha256(b) for b in [a.renderer, a.sanitizer]}
    frozen = json.loads((a.session/'prediction.json').read_text()); source = a.session/'program.wav'
    require(sha256(source) == frozen['input_sha256'], 'Input changed'); _, expected = float_wav(source)
    symbols = subprocess.check_output(['nm', '-C', str(a.sanitizer)], text=True)
    require('___asan_init' in symbols and '___ubsan_handle_' in symbols, 'Missing sanitizers')
    if a.engine:
        require('rmx::Engine::process(' in symbols and 'rmx::Engine::process(' in subprocess.check_output(['nm','-C',str(a.renderer)],text=True),'Replay is not the live Engine')
    rows = []
    for c in frozen['cases']:
        receipt, x, input_audio = match.original(a, c, expected)
        schedule = root/(c['name']+'.tsv'); schedule.write_text(match.schedule(c))
        native = schedule.with_suffix('.wav'); sanitized = root/(c['name']+'-sanitized.wav')
        run([a.renderer, source, native, schedule])
        r = subprocess.run([str(a.sanitizer), str(source), str(sanitized), str(schedule)], capture_output=True, text=True,
             env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), timeout=120)
        require(r.returncode == 0 and not r.stderr, 'Sanitizer failure: '+r.stderr)
        require(sha256(native) == sha256(sanitized), 'Sanitizer WAV bytes differ')
        rate, y = float_wav(native); require(rate == 48000 and x.shape == y.shape, 'Extent differs')
        dry = match.transport(input_audio, c['block'], c['changes'])[32:]; x = x[32:]; y = y[32:]
        intervals = [(0, len(x), 'complete')] + [(s, min(s+48000, len(x)), 'second') for s in range(0, len(x), 48000)]
        intervals += [(max(0,e['frame']-64), min(len(x),e['frame']+2048), 'event') for e in c['changes']]
        windows = [dict(start=s, stop=t, kind=k, whole=score(x[s:t],y[s:t]),
                   wet=score(x[s:t].astype(float)-dry[s:t],y[s:t].astype(float)-dry[s:t])) for s,t,k in intervals]
        passed = all(w['whole']['passed'] and w['wet']['passed'] for w in windows)
        rows.append(dict(case=c['name'], passed=passed, windows=windows, sanitizer_byte_identical=True,
                         receipt_sha256=sha256(a.session/c['name']/'receipt.json'), candidate_sha256=sha256(native)))
        print('REGRESSION',c['name'],passed,flush=True)
    require(bound == bindings() and own == sha256(Path(__file__)) and
            all(sha256(Path(b)) == h for b,h in binaries.items()), 'Candidate changed')
    save_json(root/'verification.json',dict(kind='spiral-motion-independent-regression-audit',live_engine=a.engine,passed=all(r['passed'] for r in rows),
             cases=rows, source_sha256=bound, verifier_sha256=own, binaries_sha256=binaries,
             previous_prediction_sha256=sha256(a.session/'prediction.json'),
             scope='Existing original programs in their recorded recipes. Whole/wet, one-second and event windows1%perchannel; complete optimized/sanitized WAV byte identity. No new prospective capture, broader-profile, live-wrapper or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__': raise SystemExit(main())
