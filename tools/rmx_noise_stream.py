#!/usr/bin/env python3
"""Validate Noise with bounded temporary audio and retained power summaries only."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from tools import rmx_noise_user as noise
from tools.noise_statistics import float_wav, powers, stereo_correlation, measure_powers
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import require
from tools.rmx_factory_match import IDENTITY

BUDGET = 512 * 1024 * 1024


class RenderSpace:
    def __init__(self, root):
        self.root = root
        self.peak = 0

    def check(self):
        extent = sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
        self.peak = max(self.peak, extent)
        require(extent <= BUDGET, 'Temporary audio budget exceeded')
        return extent

    def run(self, args, *, sanitized=False):
        env = os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        self.check()
        with subprocess.Popen(list(map(str, args)), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) as process:
            try:
                while True:
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                        break
                    except subprocess.TimeoutExpired:
                        self.check()
                self.check()
                require(process.returncode == 0 and (not sanitized or not stderr), 'Renderer failed: '+stderr[-4000:])
                return stdout
            except BaseException:
                process.terminate()
                try: process.communicate(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.communicate()
                raise


def summary(path):
    rate, audio = float_wav(path)
    require(rate == 48000 and len(audio) >= 44*rate, 'Noise summary requires48k and40 stationary seconds')
    stationary = audio[4*rate:]
    bands, total = powers(stationary, rate)
    return dict(bands=bands, total=total, correlation=stereo_correlation(stationary))


def screen(a, b):
    return measure_powers(a['bands'], a['total'], b['bands'], b['total'], 48000, a['correlation'], b['correlation'])


def drift(a):
    count = len(a['total']) // 3
    return measure_powers(a['bands'][:count], a['total'][:count], a['bands'][-count:], a['total'][-count:],
                          48000, a['correlation'], a['correlation'])['verdict']


def verify_original(root, c, expected, host):
    folder = root/'original'; receipt = json.loads((folder/'receipt.json').read_text())
    require(receipt['complete'] and receipt['role'] == 'reference' and receipt['host_sha256'] == sha256(host), 'Wrong/incomplete Original receipt')
    require(all(receipt['plugin'][k] == v for k, v in IDENTITY.items()), 'Wrong Original identity')
    require(receipt['maximum_block_size'] == c['block'] and receipt['frames'] == c['frames'] and receipt['sample_rate'] == 48000,
            'Original extent/callback differs')
    require(json.loads((folder/'plan.json').read_text()) == expected, 'Original plan differs')
    for name, key in [('audio.wav', 'output_sha256'), ('plan.json', 'plan_sha256'), ('state-before.bin', 'initial_state_sha256'),
                      ('state-after.bin', 'final_state_sha256'), ('parameter-log.json', 'parameter_log_sha256'), ('inventory-after.json', 'final_inventory_sha256')]:
        require(sha256(folder/name) == receipt[key], 'Original auxiliary changed: '+name)
    require(receipt['input_sha256'] == sha256(root/'silence.wav'), 'Original input changed')
    for member in receipt['plugin']['binary_files']:
        require(sha256(Path(receipt['plugin']['bundle'])/member['path']) == member['sha256'], 'Original executable changed')
    parameter_log = json.loads((folder/'parameter-log.json').read_text())
    noise.check_readbacks(expected, parameter_log['entries'], json.loads((folder/'inventory-after.json').read_text()))
    if c['user']:
        require(noise.loader.chunks((folder/'state-before.bin').read_bytes())[b'cstm'] ==
                noise.loader.chunks((root/(c['name']+'.bin')).read_bytes())[b'cstm'], 'Original lost User customization')
    return receipt, parameter_log


def bindings():
    return noise.bindings() | {n: sha256(Path(n)) for n in ['tools/rmx_noise_stream.py', 'tools/reference_audio.py', 'tools/rmx_factory_match.py']}


def validate(a):
    require(a.duration in [180, 600], 'Use180 or600 stationary seconds')
    require(a.output.suffix == '.json' and not a.output.exists(), 'Choose a new JSON report')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    require(shutil.disk_usage(a.temp_root).free > BUDGET*2, 'Insufficient free space for bounded render')
    bound = bindings(); native_hash = sha256(a.renderer); san_hash = sha256(a.sanitizer); host_hash = sha256(a.host)
    template = a.template.read_bytes(); noise.loader.chunks(template)
    recipe = noise.recipe()
    if a.fresh:
        recipe = [noise.recipe()[0]] + [dict(name=name, user=1, main=main, amount=amount, width=width,
            minimum=minimum, maximum=maximum, block=block) for name, main, amount, width, minimum, maximum, block in [
                ('noise-fresh-normal', 89, 117, 1, 0, 3, 131),
                ('noise-fresh-mild', 157, 139, 0, 2, 1, 257),
                ('noise-fresh-wild', 181, 211, 2, 3, 2, 1021)]]
    cases = [c | dict(frames=(a.duration+4)*48000) for c in recipe if not a.case or c['name'] in a.case]
    require(cases and (not a.case or {c['name'] for c in cases} == set(a.case)), 'Unknown Noise case')
    rows = []; peaks = []; summary_files = []
    partial = a.output.with_suffix('.partial.json')
    require(not partial.exists(), 'Partial report already exists')
    with tempfile.TemporaryDirectory(prefix='rmx-bounded-noise-', dir=a.temp_root) as session:
        session = Path(session)
        for c in cases:
            print('START', c['name'], a.duration, 'seconds; temporary budget512MiB', flush=True)
            with tempfile.TemporaryDirectory(prefix=c['name']+'-', dir=session) as directory:
                root = Path(directory); space = RenderSpace(root)
                write_wav(root/'silence.wav', 48000, np.zeros(96000))
                program = root/'program.tsv'; program.write_text(noise.schedule(c)); wave = root/'candidate.wav'; sanitized = root/'sanitized.wav'
                space.run([a.renderer, root/'silence.wav', wave, program]); prediction = sha256(wave)
                prediction_time = datetime.now(timezone.utc).isoformat()
                space.run([a.sanitizer, root/'silence.wav', sanitized, program], sanitized=True)
                require(sha256(sanitized) == prediction, 'Complete native/sanitizer WAV bytes differ')
                sanitized.unlink()
                candidate = summary(wave); wave.unlink()
                inventory = json.loads(space.run([a.host, 'inventory', a.plugin]))
                require(all(inventory[k] == v for k, v in IDENTITY.items()), 'Wrong Original inventory')
                if c['user']:
                    rsd = root/(c['name']+'.RSD'); rsd.write_text(noise.xml(c))
                    (root/(c['name']+'.bin')).write_bytes(noise.state(template, noise.xml(c), str(rsd), str(root)+'/'))
                plan = noise.plan(c, inventory, root); plan_path = root/'plan.json'; save_json(plan_path, plan)
                space.run([a.host, 'render', a.plugin, root/'silence.wav', plan_path, root/'original', c['block']])
                receipt, parameter_log = verify_original(root, c, plan, a.host)
                require(datetime.fromisoformat(prediction_time) < datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')), 'Prediction did not precede Original')
                reference = summary(root/'original/audio.wav'); result = screen(reference, candidate)
                correlation_passed = abs(reference['correlation']-candidate['correlation']) <= .02
                stationarity = dict(reference=drift(reference), candidate=drift(candidate))
                gain_control = reference | dict(bands=reference['bands']*10**.3, total=reference['total']*10**.3)
                negative = screen(reference, gain_control)['verdict']; require(negative == 'different', 'Noise gate accepted3dB gain error')
                # Small sufficient statistics remain auditable after WAV cleanup.
                stats_path = a.output.with_name(a.output.stem+'-'+c['name']+'.npz')
                require(not stats_path.exists(), 'Power summary already exists')
                np.savez_compressed(stats_path, reference_bands=reference['bands'], reference_total=reference['total'],
                    candidate_bands=candidate['bands'], candidate_total=candidate['total'],
                    reference_correlation=reference['correlation'], candidate_correlation=candidate['correlation'])
                summary_files.append(dict(path=str(stats_path.resolve()), sha256=sha256(stats_path)))
                passed = result['verdict'] == 'pass' and correlation_passed and all(v == 'pass' for v in stationarity.values())
                peaks.append(space.peak)
                row = c | dict(passed=passed, statistics=result, stereo_correlation_passed=correlation_passed, stationarity=stationarity,
                    negative_control_gain3db=negative, prediction_sha256=prediction, prediction_created_utc=prediction_time,
                    complete_native_sanitizer_wav_byte_identity=True, original_receipt_sha256=sha256(root/'original/receipt.json'),
                    original_receipt=receipt, parameter_log=parameter_log, original_plan=plan, summary=summary_files[-1],
                    peak_temporary_bytes=space.peak)
                rows.append(row)
                checkpoint = partial.with_suffix('.writing')
                save_json(checkpoint, dict(kind='rmx220-bounded-user-noise-partial', complete=False, cases=rows,
                                          source_sha256=bound, raw_audio_retained=False))
                checkpoint.replace(partial)
                print('RESULT', c['name'], result['verdict'], 'stationarity', stationarity, 'peakMiB', round(space.peak/1024**2,1), flush=True)
            require(not root.exists(), 'Case render directory was retained')
    require(not session.exists(), 'Session render directory was retained')
    require(bound == bindings() and native_hash == sha256(a.renderer) and san_hash == sha256(a.sanitizer) and host_hash == sha256(a.host), 'Frozen campaign inputs changed')
    save_json(a.output, dict(kind='rmx220-bounded-user-noise-statistical-validation', passed=all(c['passed'] for c in rows), cases=rows,
        source_sha256=bound, renderer_sha256=native_hash, sanitizer_sha256=san_hash, host_sha256=host_hash,
        template_sha256=sha256(a.template), storage_budget_bytes=BUDGET, peak_temporary_bytes=max(peaks), raw_audio_retained=False,
        all_temporary_directories_removed=True, stationary_seconds=a.duration,
        scope='Declared Default/User Noise at48k/120BPM. Candidate frozen before each Original capture; complete native/ASAN WAV identity. '
        'Two-second spectral/total powers and stereo correlation retained for independent statistical audit;180/600 stationary seconds after4-second warmup. '
        'Pass requires whole stationary equivalence, stereo correlation and early/late-third equivalence. No waveform-null, transient, perceptual99%, broader-settings or hardware claim.'))
    partial.unlink()
    print('SAVED', a.output, 'raw audio retained:0', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['renderer', 'sanitizer', 'host', 'plugin', 'template', 'output']: p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--temp-root', type=Path, default=Path(tempfile.gettempdir()))
    p.add_argument('--duration', type=int, default=180); p.add_argument('--case', action='append')
    p.add_argument('--fresh', action='store_true')
    validate(p.parse_args())


if __name__ == '__main__': main()
