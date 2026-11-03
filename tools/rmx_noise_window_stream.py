#!/usr/bin/env python3
"""Predeclared continuous Noise study, retaining bounded windows and powers."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from tools import rmx_noise_user as noise
from tools import noise_window_statistics as stats
from tools.noise_window_batch import windows
from tools.rmx_noise_sidechain_controls import stimulus
from tools.rmx_noise_sidechain_stream import residual
from tools.rmx_noise_stream import RenderSpace, bindings, verify_original
from tools.reference_audio import save_json, sha256, write_wav

EXTRA = ['tools/rmx_noise_window_stream.py', 'tools/noise_window_statistics.py',
         'tools/noise_random_probe.cpp', 'tools/noise_window_batch.py', 'tools/rmx_noise_sidechain_controls.py',
         'research/audio/experiments/noise_random_observer.py']


def sources():
    return bindings() | {n: sha256(Path(n)) for n in EXTRA}


def snapshot_template(path):
    data = path.read_bytes()
    noise.loader.chunks(data)
    return data, hashlib.sha256(data).hexdigest()


def cases():
    prior = Path('research/audio/measurements/2026-11-01-noise-random-reference-1190.json')
    old = json.loads(prior.read_text())['cases'][2]
    keys = ['user', 'width', 'main', 'amount', 'mode', 'wave', 'resonance', 'sub2', 'minimum', 'maximum', 'block']
    result = {'random-wide': {k: old[k] for k in keys} | dict(name='noise-random-wide-continuous')}
    for name, width, main, raw, block in [('low', 0, 73, 29, 113), ('asymmetric', 1, 149, 117, 509)]:
        result['sidechain-' + name] = dict(name='noise-sidechain-' + name + '-continuous', user=1, width=width,
            main=main, amount=163, mode=0, wave=4, resonance=0, sub2=raw, minimum=0, maximum=2, block=block)
    return result


def program(c, start, frames, repeat=True):
    return noise.schedule(c).replace('RMX_NOISE_USER 2', 'RMX_NOISE_USER 4') + f'{int(repeat)} {start} {frames}\n'


def prepare(root, c, template, inventory, start, frames, repeat=True):
    rsd = root / (c['name'] + '.RSD')
    rsd.write_text(noise.xml(c))
    (root / (c['name'] + '.bin')).write_bytes(noise.state(template, noise.xml(c), str(rsd), str(root) + '/'))
    plan = noise.plan(c, inventory, root)
    plan['tail_seconds'] = 0
    plan['render_window'] = dict(processing_frames=c['frames'], start_frame=start, frames=frames, repeat_input=repeat)
    save_json(root / 'plan.json', plan)
    (root / 'program.tsv').write_text(program(c, start, frames, repeat))
    return plan


def verified(root, c, plan, host, folder='original'):
    if folder != 'original':
        raise ValueError('Unexpected verification folder')
    window = plan['render_window']
    receipt, _ = verify_original(root, c | dict(frames=window['frames']), plan, host)
    if receipt['processing_frames'] != c['frames'] or receipt['capture_start_frame'] != window['start_frame'] or receipt['input_repeated'] != window['repeat_input']:
        raise ValueError('Reference window/repetition receipt differs')
    return receipt


def observe_targets(a, root, space, c, ordinary):
    names = ['audio.wav', 'plan.json', 'state-before.bin', 'state-after.bin', 'parameter-log.json', 'inventory-after.json']
    hashes = {name: ordinary['output_sha256'] if name == 'audio.wav' else sha256(root / 'original' / name) for name in names}
    observer = Path('research/audio/experiments/noise_random_observer.py').resolve()
    args = ['render', str(a.plugin.resolve()), str(root / 'silence.wav'), str(root / 'plan.json'), str(root / 'observed'), str(c['block']), '1800']
    commands = root / 'observe.lldb'
    commands.write_text('target create ' + json.dumps(str(a.host.resolve())) + '\nsettings set target.run-args ' + ' '.join(map(json.dumps, args))
        + '\ncommand script import ' + json.dumps(str(observer)) + '\nrun\nscript noise_random_observer.finish()\nquit\n')
    space.run(['env', 'RMX_RANDOM_COMPACT=1', 'RMX_RANDOM_TRACE=' + str(root / 'targets.f32'), 'lldb', '--batch', '-s', commands])
    observed = json.loads((root / 'observed/receipt.json').read_text())
    if not observed['complete'] or any(sha256(root / 'observed' / name) != digest for name, digest in hashes.items()):
        raise ValueError('Observer changed audio or auxiliary capture artifacts')
    targets = (root / 'targets.f32').read_bytes()
    blocks = (c['frames'] - 4832) // 32
    for probe in [a.probe, a.sanitizer_probe]:
        result = subprocess.run([str(probe), str(c['sub2']), str(blocks), 'own', 'targets'], capture_output=True, check=True,
            env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        if result.stderr or result.stdout != targets:
            raise ValueError('Long default target trajectory differs')
    return np.frombuffer(targets, dtype='<f4').copy(), dict(ordinary_and_observed_sha256=hashes,
        full_default_native_sanitizer_target_identity=True, draws=len(targets) // 4, target_sha256=sha256(root / 'targets.f32'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['renderer', 'sanitizer', 'probe', 'sanitizer-probe', 'host', 'plugin', 'template', 'output']:
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--case', choices=list(cases()), action='append')
    p.add_argument('--seconds', type=int, choices=[7140], default=7140)
    p.add_argument('--window-seconds', type=int, choices=[1190], default=1190)
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.plan.json').exists():
        raise ValueError('Choose a new output')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    template, template_digest = snapshot_template(a.template)
    bound = sources()
    binary = {key: sha256(getattr(a, key)) for key in ['renderer', 'sanitizer', 'probe', 'sanitizer_probe', 'host']}
    selected = [cases()[name] | dict(stimulus=name) for name in a.case or cases()]
    declared = dict(kind='fixed-horizon-continuous-noise-plan', cases=selected, stationary_seconds=a.seconds, window_seconds=a.window_seconds,
        source_sha256=bound, binary_sha256=binary, template_sha256=template_digest, created_utc=datetime.now(timezone.utc).isoformat(),
        limits=dict(band_db=.5, level_db=.1, correlation=.02, confidence_multiplier=3, meaningful_floor_db=-40),
        scope='Fixed horizon, no early acceptance or repeated extensions. Six adjacent windows cover a single declared continuous trajectory. Earlier shorter captures are not pooled. Gates/estimands unchanged.')
    save_json(a.output.with_suffix('.plan.json'), declared)
    rows = []
    for base in selected:
        random = base['wave'] == 3
        pattern = np.zeros((48000, 2), dtype='<f4') if random else stimulus(base['stimulus'].removeprefix('sidechain-'))
        candidate_parts, reference_parts, segments = [], [], []
        with tempfile.TemporaryDirectory(prefix='rmx-noise-continuous-', dir='/private/tmp') as directory:
            root = Path(directory)
            space = RenderSpace(root)
            write_wav(root / 'silence.wav', 48000, pattern.reshape(-1))
            inventory = json.loads(space.run([a.host, 'inventory', a.plugin]))
            # Independent dry subtraction control with the same input repeat.
            dry = base | dict(amount=0, minimum=0, frames=8 * 48000)
            dry_plan = prepare(root, dry, template, inventory, 0, dry['frames'])
            space.run([a.renderer, root / 'silence.wav', root / 'native.wav', root / 'program.tsv'])
            candidate_dry = float(np.max(np.abs(residual(root / 'native.wav', pattern)[4 * 48000:])))
            (root / 'native.wav').unlink()
            space.run([a.host, 'render', a.plugin, root / 'silence.wav', root / 'plan.json', root / 'original', dry['block'], '1800'])
            dry_receipt = verified(root, dry, dry_plan, a.host)
            reference_dry = float(np.max(np.abs(residual(root / 'original/audio.wav', pattern)[4 * 48000:])))
            if max(candidate_dry, reference_dry) > 1e-6:
                raise ValueError(f'Dry subtraction failed: native={candidate_dry}, Original={reference_dry}')
            shutil.rmtree(root / 'original')
            (root / 'plan.json').unlink()
            count = a.seconds // a.window_seconds
            batch_case = base | dict(frames=(4 + a.seconds) * 48000)
            batch_program = noise.schedule(batch_case).replace('RMX_NOISE_USER 2', 'RMX_NOISE_USER 5') + f'1 {4 * 48000} {a.window_seconds * 48000} {count}\n'
            (root / 'batch.tsv').write_text(batch_program)
            predictions, prediction_times = [], []
            for renderer, sanitized in [(a.renderer, False), (a.sanitizer, True)]:
                directory = root / ('sanitizer-batch' if sanitized else 'native-batch')
                print('CONTINUOUS PASS', base['stimulus'], 'sanitizer' if sanitized else 'native', flush=True)
                with closing(windows(space, renderer, root / 'silence.wav', directory, root / 'batch.tsv', count, sanitized)) as producer:
                    for index, wave in producer:
                        digest = sha256(wave)
                        if sanitized:
                            if digest != predictions[index]:
                                raise ValueError('Continuous native/sanitizer retained window differs')
                        else:
                            predictions.append(digest)
                            prediction_times.append(datetime.now(timezone.utc).isoformat())
                            start = (4 + index * a.window_seconds) * 48000
                            candidate_parts.append(stats.analyze(wave, start, a.window_seconds, None if random else pattern, base['sub2'], a.probe if random else None))
                        wave.unlink()
                        print('CONTINUOUS WINDOW', base['stimulus'], index, 'sanitizer' if sanitized else 'native', 'verified', flush=True)
                shutil.rmtree(directory)
            for index in range(count):
                start = (4 + index * a.window_seconds) * 48000
                prefix = 4 * 48000 if index == 0 else 128
                capture_start = start - prefix
                frames = prefix + a.window_seconds * 48000
                c = base | dict(frames=start + a.window_seconds * 48000)
                plan = prepare(root, c, template, inventory, capture_start, frames)
                digest, frozen = predictions[index], prediction_times[index]
                print('WINDOW', base['stimulus'], index, 'Original', flush=True)
                space.run([a.host, 'render', a.plugin, root / 'silence.wav', root / 'plan.json', root / 'original', c['block'], '1800'])
                receipt = verified(root, c, plan, a.host)
                if datetime.fromisoformat(frozen) >= datetime.fromisoformat(receipt['created_at_utc'].replace('Z', '+00:00')):
                    raise ValueError('Prediction followed reference')
                reference_parts.append(stats.analyze(root / 'original/audio.wav', start, a.window_seconds, None if random else pattern, c['sub2'], a.probe if random else None))
                (root / 'original/audio.wav').unlink()
                segments.append(dict(stationary_start_frame=start, stationary_frames=a.window_seconds * 48000, captured_start_frame=capture_start,
                    captured_frames=frames, processing_frames=c['frames'], plan=plan, schedule_sha256=sha256(root / 'program.tsv'), prediction_sha256=digest,
                    prediction_created_utc=frozen, complete_retained_native_sanitizer_wav_identity=True, original_receipt=receipt,
                    original_receipt_sha256=sha256(root / 'original/receipt.json')))
                if random and index == a.seconds // a.window_seconds - 1:
                    print('OBSERVE long Random target trajectory', flush=True)
                    targets, control = observe_targets(a, root, space, c, receipt)
                    shutil.rmtree(root / 'observed')
                    (root / 'targets.f32').unlink()
                shutil.rmtree(root / 'original')
                (root / 'plan.json').unlink()
            candidate, reference = stats.combine(candidate_parts), stats.combine(reference_parts)
            result = stats.score(reference, candidate, random)
            data = {f'{role}_{key}': value for role, pair in [('reference', reference), ('candidate', candidate)] for key, value in pair[0].items()}
            data |= {f'{role}_profile_{key}': value for role, pair in [('reference', reference), ('candidate', candidate)] for key, value in pair[1].items()}
            if random:
                data['default_targets'] = targets
            summary = a.output.with_name(a.output.stem + '-' + base['stimulus'] + '.npz')
            if summary.exists():
                raise ValueError('Power summary exists')
            np.savez_compressed(summary, **data)
            row = base | result | dict(segments=segments, stationary_seconds=a.seconds, native_continuous_single_pass=True, native_batch_schedule_sha256=sha256(root / 'batch.tsv'), summary=dict(path=str(summary.resolve()), sha256=sha256(summary)),
                dry_subtraction_control=dict(candidate_maximum_residual=candidate_dry, reference_maximum_residual=reference_dry, receipt=dry_receipt),
                control_observation=control if random else None, peak_temporary_bytes=space.peak)
        row['all_temporary_directories_removed'] = not root.exists()
        rows.append(row)
        print('CONTINUOUS RESULT', base['stimulus'], row['passed'], row['statistics']['verdict'], row['profile']['verdict'], row['profile_thirds'], row['stationarity'], flush=True)
        checkpoint = a.output.with_suffix('.partial.json')
        checkpoint.write_text(json.dumps(dict(complete=False, cases=rows), indent=2) + '\n')
    if sources() != bound or any(sha256(getattr(a, key)) != digest for key, digest in binary.items()):
        raise ValueError('Frozen study inputs changed')
    save_json(a.output, dict(kind='bounded-continuous-noise-validation', verification_passed=True, passed=all(r['passed'] for r in rows), cases=rows,
        source_sha256=bound, binary_sha256=binary, declared_plan_sha256=sha256(a.output.with_suffix('.plan.json')), raw_audio_retained=False,
        all_temporary_directories_removed=all(r['all_temporary_directories_removed'] for r in rows), peak_temporary_bytes=max(r['peak_temporary_bytes'] for r in rows),
        scope=declared['scope'] + ' Exact target observations required for Random covariance. Independent white excitation retained. No waveform-null, listening, arbitrary gestures or hardware qualification.'))
    a.output.with_suffix('.partial.json').unlink()


if __name__ == '__main__':
    main()
