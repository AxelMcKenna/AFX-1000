#!/usr/bin/env python3
"""Bounded User Noise validation; statistical verdicts are never waveform matches."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess

import numpy as np

from tools import rmx_drums as drums
from tools import rmx_drum_user_settings as loader
from tools.noise_statistics import float_wav, measure, stereo_correlation
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums_fx import source_hashes
from tools.rmx_factory_match import IDENTITY, new_directory, run

FRAMES = 184 * 48000


def bindings():
    return source_hashes() | {n: sha256(Path(n)) for n in ['tools/rmx_noise_user.py', 'tools/noise_user_probe.cpp', 'tools/noise_statistics.py', 'tools/rmx_drum_user_settings.py', 'tools/audio_plugin_render.cpp', 'tools/audio_plugin_host.h', 'tools/legacy_vst2_host.h']}


def recipe():
    return [dict(name=name, user=user, main=main, amount=amount, width=width, minimum=minimum, maximum=maximum, block=block)
        for name, user, main, amount, width, minimum, maximum, block in [
            ('noise-default-control', 0, 81, 64, 1, 1, 2, 127),
            ('noise-user-wide-levels', 1, 81, 97, 1, 0, 3, 509),
            ('noise-user-narrow-levels', 1, 233, 191, 1, 3, 0, 43),
            ('noise-user-width0', 1, 147, 128, 0, 1, 2, 1021)]]


def schedule(c):
    return 'RMX_NOISE_USER 1\n' + ' '.join(map(str, [c.get('frames', FRAMES)] + [c[k] for k in ['block', 'user', 'main', 'amount', 'width', 'minimum', 'maximum']])) + '\n'


def xml(c):
    noise = '<SceneFx><Lock>0</Lock><Noise>' + ''.join(f'<{name}>{value}</{name}>' for name, value in [
        # Original popup order: Default/Mild/Wild. Project: Mild/Default/Wild.
        ('CenterFilterTypeCb', [1, 0, 2][c['width']]), ('Sub1MinSld', c['minimum']), ('Sub1MaxSld', c['maximum']),
        ('Sub2ModResSelectBtn', 0), ('Sub2ModTypeCb', 0), ('Sub2ResTypeCb', 0)]) + '</Noise></SceneFx>'
    return loader.xml({}).replace('</RMX-1000>', noise + '</RMX-1000>')


def state(template, text, filename, directory):
    chunks = loader.chunks(template)
    values = [filename.encode(), directory.encode(), text.encode()]
    chunks[b'cstm'] = b''.join(struct.pack('<I', len(v)) + v for v in values)
    body = b''.join(tag + struct.pack('<I', len(data)) + data for tag, data in chunks.items())
    return struct.pack('<I', len(body)) + body


def plan(c, inventory, root):
    def setting(name, value):
        p = next(p for p in inventory['parameters'] if p['name'] == name)
        return {k: p[k] for k in ['name', 'id', 'index']} | dict(value=value)
    values = drums.parameters(dict(drum='kick', level=128, pitch=128, position=153))
    values.update(DefaultSwitch=1-c['user'], UserSwitch=c['user'],
        SceneVolume=c['main']/255, Sub1Volume=c['amount']/255, Sub2Volume=0, NoiseButton=0)
    result = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference', expected_plugin=IDENTITY,
        sample_rate=48000, bpm=120, tail_seconds=c.get('frames', FRAMES)/48000-1, parameters=[setting(k, v) for k, v in values.items()],
        events=[setting('NoiseButton', 1) | dict(frame=4800, type='parameter')])
    if c['user']: result['initial_state'] = dict(path=c['name']+'.bin', sha256=sha256(root/(c['name']+'.bin')))
    return result


def check_readbacks(expected, log, inventory_after):
    requested = [p | dict(frame=-1) for p in expected['parameters']] + expected['events']
    drums.require(len(log) == len(requested), 'Noise request log extent differs')
    final = {}
    for req, actual in zip(requested, log, strict=True):
        value = float(np.float32(req['value']))
        # The host logs the requested JSON double, then delivers a float32.
        # Its decimal serialization can also round the readback's last digit.
        drums.require(all(actual[k] == req[k] for k in ['frame', 'name', 'id', 'index'])
            and np.float32(actual['requested_value']) == np.float32(req['value'])
            and abs(actual['immediate_readback']-value) <= 1e-14, 'Noise readback differs')
        final[req['name']] = value
    readbacks = {p['name']: p['value'] for p in inventory_after['parameters']}
    drums.require(all(abs(readbacks[k]-v) <= 1e-14 for k, v in final.items()), 'Noise final controls differ')


def predict(a):
    root = new_directory(a.session); (root/'predictions').mkdir(); bound = bindings(); binary = sha256(a.renderer); outputs = {}
    write_wav(root/'silence.wav', 48000, np.zeros(48000*2))
    for c in recipe():
        path = root/'predictions'/(c['name']+'.tsv'); path.write_text(schedule(c)); out = path.with_suffix('.wav')
        run([a.renderer, root/'silence.wav', out, path]); outputs[c['name']] = sha256(out)
    drums.require(bound == bindings() and binary == sha256(a.renderer), 'Noise prediction changed')
    save_json(root/'prediction.json', dict(kind='noise-user-frozen-statistical-prediction', cases=recipe(), source_sha256=bound,
        renderer=str(a.renderer.resolve()), renderer_sha256=binary, output_sha256=outputs, sample_rate=48000, frames=FRAMES,
        screen=dict(start_seconds=4, duration_seconds=180, band_margin_db=.5, level_margin_db=.1, stereo_correlation_margin=.02)))


def capture(a):
    root = a.session; prediction = json.loads((root/'prediction.json').read_text()); bound = bindings()
    drums.require(prediction['source_sha256'] == bound and prediction['cases'] == recipe(), 'Noise candidate changed')
    drums.require(sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Noise renderer changed')
    for c in recipe(): drums.require(sha256(root/'predictions'/(c['name']+'.wav')) == prediction['output_sha256'][c['name']], 'Noise prediction WAV changed')
    inventory = json.loads(run([a.host, 'inventory', a.plugin])); drums.require(all(inventory[k] == v for k, v in IDENTITY.items()), 'Wrong Original')
    save_json(root/'inventory.json', inventory); template = a.template.read_bytes(); rows = []
    for c in recipe():
        if c['user']:
            path = root/(c['name']+'.RSD'); path.write_text(xml(c))
            (root/(c['name']+'.bin')).write_bytes(state(template, xml(c), str(path.resolve()), str(root.resolve())+'/'))
        path = root/(c['name']+'.json'); save_json(path, plan(c, inventory, root))
        run([a.host, 'render', a.plugin, root/'silence.wav', path, root/c['name'], c['block']])
        rows.append(c | dict(receipt_sha256=sha256(root/c['name']/'receipt.json'))); print('CAPTURED', c['name'], flush=True)
    drums.require(bound == bindings(), 'Noise capture sources changed')
    save_json(root/'matrix.json', dict(kind='noise-user-reference-captures', cases=rows, prediction_sha256=sha256(root/'prediction.json'), host_sha256=sha256(a.host)))


def compare(a):
    root = a.session; output = new_directory(a.output); bound = bindings(); native = sha256(a.renderer); san = sha256(a.sanitizer)
    prediction = json.loads((root/'prediction.json').read_text()); matrix = json.loads((root/'matrix.json').read_text()); inventory = json.loads((root/'inventory.json').read_text()); rows = []
    drums.require(prediction['source_sha256'] == bound and native == prediction['renderer_sha256'] and matrix['prediction_sha256'] == sha256(root/'prediction.json'), 'Noise prediction binding differs')
    drums.require(matrix['host_sha256'] == sha256(a.host) and [r['name'] for r in matrix['cases']] == [r['name'] for r in recipe()], 'Noise matrix/host differs')
    for c, stored in zip(recipe(), matrix['cases'], strict=True):
        folder = root/c['name']; receipt = json.loads((folder/'receipt.json').read_text()); expected = plan(c, inventory, root)
        drums.require(receipt['complete'] and stored == c | dict(receipt_sha256=sha256(folder/'receipt.json')), 'Incomplete/changed Noise receipt')
        drums.require(all(receipt['plugin'][k] == v for k, v in IDENTITY.items()) and receipt['maximum_block_size'] == c['block'] and json.loads((folder/'plan.json').read_text()) == expected, 'Noise reference plan differs')
        for name, key in [('audio.wav', 'output_sha256'), ('plan.json', 'plan_sha256'), ('state-before.bin', 'initial_state_sha256'), ('state-after.bin', 'final_state_sha256'), ('parameter-log.json', 'parameter_log_sha256'), ('inventory-after.json', 'final_inventory_sha256')]:
            drums.require(sha256(folder/name) == receipt[key], 'Noise auxiliary changed')
        drums.require(receipt['input_sha256'] == sha256(root/'silence.wav') and receipt['frames'] == FRAMES and receipt['sample_rate'] == 48000, 'Noise input/extent differs')
        for member in receipt['plugin']['binary_files']: drums.require(sha256(Path(receipt['plugin']['bundle'])/member['path']) == member['sha256'], 'Original changed')
        check_readbacks(expected, json.loads((folder/'parameter-log.json').read_text())['entries'], json.loads((folder/'inventory-after.json').read_text()))
        if c['user']:
            drums.require((root/(c['name']+'.RSD')).read_text() == xml(c) and loader.chunks((folder/'state-before.bin').read_bytes())[b'cstm'] == loader.chunks((root/(c['name']+'.bin')).read_bytes())[b'cstm'], 'Noise User customization lost')
        path = output/(c['name']+'.tsv'); path.write_text(schedule(c)); wave = path.with_suffix('.wav'); sanitized = output/(c['name']+'-asan.wav')
        run([a.renderer, root/'silence.wav', wave, path])
        result = subprocess.run([str(a.sanitizer), str(root/'silence.wav'), str(sanitized), str(path)], capture_output=True, text=True, env=os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), timeout=900)
        drums.require(result.returncode == 0 and not result.stderr, 'Noise sanitizer failure: '+result.stderr)
        digest = sha256(wave); drums.require(digest == sha256(sanitized) == prediction['output_sha256'][c['name']] and digest == sha256(root/'predictions'/(c['name']+'.wav')), 'Noise optimized/sanitizer/prediction identity differs')
        rate, x = float_wav(folder/'audio.wav'); other_rate, y = float_wav(wave); drums.require(rate == other_rate == 48000 and x.shape == y.shape == (FRAMES, 2), 'Noise WAV extent differs')
        x, y = x[4*48000:], y[4*48000:]; statistics = measure(x, y, rate); correlation_passed = abs(stereo_correlation(x)-stereo_correlation(y)) <= .02
        # Compare early/late thirds separately; a full-capture average can hide drift.
        stationarity = dict(reference=measure(x[:60*48000], x[-60*48000:], rate)['verdict'], candidate=measure(y[:60*48000], y[-60*48000:], rate)['verdict'])
        negatives = dict(gain3db=measure(x, x.astype(float)*10**(3/20), rate)['verdict'])
        drums.require(negatives['gain3db'] == 'different', 'Noise screen accepted gain negative control')
        passed = statistics['verdict'] == 'pass' and correlation_passed and 'different' not in stationarity.values()
        rows.append(c | dict(passed=passed, statistics=statistics, stereo_correlation_passed=correlation_passed, stationarity_screens=stationarity,
            negative_controls=negatives, receipt_sha256=stored['receipt_sha256'], original_wav_sha256=receipt['output_sha256'], candidate_sha256=digest, complete_prediction_native_sanitizer_wav_identity=True))
        print('NOISE', c['name'], statistics['verdict'], 'stationarity', stationarity, flush=True)
    drums.require(bound == bindings() and sha256(a.renderer) == native and sha256(a.sanitizer) == san, 'Noise comparison changed')
    save_json(output/'comparison.json', dict(kind='noise-user-statistical-comparison', passed=all(c['passed'] for c in rows), cases=rows, source_sha256=bound,
        prediction_sha256=sha256(root/'prediction.json'), matrix_sha256=sha256(root/'matrix.json'), renderer_sha256=native, sanitizer_sha256=san,
        scope='Four declared stationary Default/User Noise programs; 180 seconds after four-second warmup. Approximate confidence intervals, band/level equivalence and stereo correlation. A statistical pass is not a waveform-null, perceptual99% or full advanced-settings claim. Inconclusive and different results stay visible.'))


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('command', choices=['predict', 'capture', 'compare']); p.add_argument('--session', type=Path, required=True)
    for name in ['renderer', 'sanitizer', 'host', 'plugin', 'template', 'output']: p.add_argument('--'+name, type=Path)
    a = p.parse_args(); globals()[a.command](a)


if __name__ == '__main__': main()
