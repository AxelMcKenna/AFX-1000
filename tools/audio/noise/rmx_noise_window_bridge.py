#!/usr/bin/env python3
"""Verify window/repeat captures against prior full-file hosts and renderers."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from tools.audio.noise import rmx_noise_user as noise
from tools.audio.noise.noise_window_batch import windows
from tools.audio.noise.rmx_noise_window_stream import cases, prepare, sources, verified
from tools.audio.noise.rmx_noise_sidechain_controls import stimulus
from tools.audio.noise.rmx_noise_stream import RenderSpace
from tools.audio.noise.noise_statistics import float_wav
from tools.audio.common.reference_audio import save_json, sha256, write_wav


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['renderer', 'sanitizer', 'before', 'host', 'before-host', 'plugin', 'template', 'output']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    bound = sources() | {'tools/audio/noise/rmx_noise_window_bridge.py': sha256(Path(__file__))}
    binary = {k: sha256(getattr(a, k)) for k in ['renderer', 'sanitizer', 'before', 'host', 'before_host']}
    rows = []
    for key, base in cases().items():
        c = base | dict(frames=8 * 48000)
        pattern = np.zeros((48000, 2), dtype='<f4') if key == 'random-wide' else stimulus(key.removeprefix('sidechain-'))
        with tempfile.TemporaryDirectory(prefix='rmx-noise-window-bridge-', dir='/private/tmp') as directory:
            root = Path(directory)
            space = RenderSpace(root)
            write_wav(root / 'silence.wav', 48000, np.tile(pattern, (8, 1)).reshape(-1))
            inv = json.loads(space.run([a.host, 'inventory', a.plugin]))
            prepare(root, c, a.template.read_bytes(), inv, 0, c['frames'], False)
            (root / 'plan.json').unlink()
            ordinary = noise.plan(c, inv, root) | dict(tail_seconds=0)
            save_json(root / 'plan.json', ordinary)
            legacy_program = noise.schedule(c).replace('RMX_NOISE_USER 2', 'RMX_NOISE_USER 3')
            (root / 'program.tsv').write_text(legacy_program)
            hashes = []
            for renderer in [a.before, a.renderer, a.sanitizer]:
                space.run([renderer, root / 'silence.wav', root / 'native.wav', root / 'program.tsv'], sanitized=renderer == a.sanitizer)
                hashes.append(sha256(root / 'native.wav'))
                native = float_wav(root / 'native.wav')[1].copy()
                (root / 'native.wav').unlink()
            if len(set(hashes)) != 1:
                raise ValueError('Legacy full native/sanitizer output changed')
            artifacts = ['audio.wav', 'plan.json', 'state-before.bin', 'state-after.bin', 'parameter-log.json', 'inventory-after.json']
            host_hashes = []
            for host in [a.before_host, a.host]:
                space.run([host, 'render', a.plugin, root / 'silence.wav', root / 'plan.json', root / 'ordinary', c['block']])
                host_hashes.append({name: sha256(root / 'ordinary' / name) for name in artifacts})
                full = float_wav(root / 'ordinary/audio.wav')[1].copy()
                shutil.rmtree(root / 'ordinary')
            if host_hashes[0] != host_hashes[1]:
                raise ValueError('Host bridge changed ordinary audio or auxiliaries')
            (root / 'plan.json').unlink()
            write_wav(root / 'silence.wav', 48000, pattern.reshape(-1))
            loop_plan = prepare(root, c, a.template.read_bytes(), inv, 0, c['frames'])
            space.run([a.renderer, root / 'silence.wav', root / 'native.wav', root / 'program.tsv'])
            if sha256(root / 'native.wav') != hashes[0]:
                raise ValueError('Native input repetition differs from unrolled input')
            (root / 'native.wav').unlink()
            space.run([a.host, 'render', a.plugin, root / 'silence.wav', root / 'plan.json', root / 'original', c['block']])
            verified(root, c, loop_plan, a.host)
            if sha256(root / 'original/audio.wav') != host_hashes[0]['audio.wav']:
                raise ValueError('Host input repetition differs from unrolled input')
            loop_aux = {name: sha256(root / 'original' / name) for name in artifacts if name not in ['audio.wav', 'plan.json']}
            if loop_aux != {name: host_hashes[0][name] for name in loop_aux}:
                raise ValueError('Input repetition changed state, logs or inventory')
            shutil.rmtree(root / 'original')
            (root / 'plan.json').unlink()
            start, count = 123457, 100777
            window_plan = prepare(root, c, a.template.read_bytes(), inv, start, count)
            for renderer in [a.renderer, a.sanitizer]:
                space.run([renderer, root / 'silence.wav', root / 'native.wav', root / 'program.tsv'], sanitized=renderer == a.sanitizer)
                if not np.array_equal(float_wav(root / 'native.wav')[1].view(np.uint32), native[start:start + count].view(np.uint32)):
                    raise ValueError('Native crop changes samples or callback clock')
                (root / 'native.wav').unlink()
            space.run([a.host, 'render', a.plugin, root / 'silence.wav', root / 'plan.json', root / 'original', c['block']])
            receipt = verified(root, c, window_plan, a.host)
            if not np.array_equal(float_wav(root / 'original/audio.wav')[1].view(np.uint32), full[start:start + count].view(np.uint32)):
                raise ValueError('Reference window differs from exact ordinary crop')
            if any(sha256(root / 'original' / name) != digest for name, digest in loop_aux.items()):
                raise ValueError('Saving a window changed state, logs or inventory')
            shutil.rmtree(root / 'original')
            (root / 'plan.json').unlink()
            batch_program = noise.schedule(c).replace('RMX_NOISE_USER 2', 'RMX_NOISE_USER 5') + f'1 {2 * 48000} {2 * 48000} 3\n'
            (root / 'batch.tsv').write_text(batch_program)
            for renderer, sanitized in [(a.renderer, False), (a.sanitizer, True)]:
                directory = root / ('batch-asan' if sanitized else 'batch-native')
                with closing(windows(space, renderer, root / 'silence.wav', directory, root / 'batch.tsv', 3, sanitized)) as producer:
                    for index, wave in producer:
                        first = 0 if index == 0 else (2 + index * 2) * 48000 - 128
                        stop = (4 + index * 2) * 48000
                        if not np.array_equal(float_wav(wave)[1].view(np.uint32), native[first:stop].view(np.uint32)):
                            raise ValueError('Uninterrupted native batch differs from ordinary full run')
                        wave.unlink()
                shutil.rmtree(directory)
            directory = root / 'bad-consumer'
            rejected = False
            with closing(windows(space, a.renderer, root / 'silence.wav', directory, root / 'batch.tsv', 3)) as producer:
                next(producer)
                try:
                    next(producer)
                except ValueError as error:
                    rejected = 'did not delete' in str(error)
            if not rejected:
                raise ValueError('Batch accepted a consumer that retained raw audio')
            shutil.rmtree(directory)
            prepare(root, c, a.template.read_bytes(), inv, c['frames'] - 1, 2)
            invalid_native = subprocess.run([a.renderer, root / 'silence.wav', root / 'bad.wav', root / 'program.tsv'], capture_output=True)
            invalid_host = subprocess.run([a.host, 'render', a.plugin, root / 'silence.wav', root / 'plan.json', root / 'bad', str(c['block'])], capture_output=True)
            if invalid_native.returncode == 0 or invalid_host.returncode == 0 or (root / 'bad/receipt.json').exists():
                raise ValueError('Invalid capture window accepted')
            rows.append(dict(case=key, passed=True, legacy_native_sanitizer_wav_sha256=hashes, ordinary_old_new_host_sha256=host_hashes,
                input_repetition_full_wav_and_auxiliary_identity=True, arbitrary_window_native_sanitizer_sample_bit_identity=True,
                arbitrary_window_Original_sample_bit_identity=True, window_preserves_final_state_logs_inventory=True,
                window_receipt=receipt, invalid_windows_rejected=True, continuous_native_sanitizer_batch_sample_bit_identity=True, batch_consumer_retention_rejected=True, peak_temporary_bytes=space.peak))
            print('WINDOW BRIDGE', key, 'passed', flush=True)
        if root.exists():
            raise ValueError('Bridge retained audio')
    if sources() | {'tools/audio/noise/rmx_noise_window_bridge.py': sha256(Path(__file__))} != bound or any(sha256(getattr(a, k)) != digest for k, digest in binary.items()):
        raise ValueError('Bridge inputs changed')
    save_json(a.output, dict(kind='noise-window-host-and-native-bridge', verification_passed=True, passed=True, cases=rows,
        source_sha256=bound, binary_sha256=binary, raw_audio_retained=False, all_temporary_directories_removed=True,
        scope='Three eight-second declared Noise presets. Old/new ordinary capture artifacts, explicit input unrolling/repetition, non-block-aligned saved-window crops and invalid-window guards. This verifies capture semantics, not long-run Noise fidelity.'))


if __name__ == '__main__':
    main()
