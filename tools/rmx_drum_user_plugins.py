#!/usr/bin/env python3
"""Check custom drum profiles through explicit project AU/VST3 MIDI delivery."""
import argparse
import concurrent.futures
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tools import rmx_drum_user_match as native
from tools import rmx_drum_user_settings as loader
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import DRUMS, require
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['host', 'reference-host', 'plugin', 'session', 'native-report', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--workers', type=int, default=2)
    a = parser.parse_args(); require(1 <= a.workers <= 4, 'Invalid worker count')
    bound = native.bindings(); own = sha256(Path(__file__)); host_hash = sha256(a.host)
    report_hash = sha256(a.native_report); report = json.loads(a.native_report.read_text())
    require(report['passed'] and report['acceptance'] == ACCEPTANCE and report['source_sha256'] == bound, 'Native evidence differs')
    matrix = json.loads((a.session / 'matrix.json').read_text()); expected = loader.recipe(matrix['stage'])
    cases = [{k: v for k, v in row.items() if k != 'receipt_sha256'} for row in matrix['cases']]
    require([c['name'] for c in expected] == [c['name'] for c in cases] == [c['case'] for c in report['cases']], 'Native coverage differs')
    root = new_directory(a.output); inventory = json.loads(run([a.host, 'inventory', a.plugin])); save_json(root / 'inventory.json', inventory)
    identity = {k: inventory[k] for k in ['name', 'manufacturer', 'version']}
    require(identity == dict(name='RMX', manufacturer='Axel McKenna', version='0.1.0'), 'Wrong project plug-in')
    binaries = {b['path']: sha256(a.plugin / b['path']) for b in inventory['binary_files']}

    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if name == 'Bypass': matches = [p for p in matches if p['id'] == '773352680']
        require(len(matches) == 1, 'Ambiguous wrapper parameter: ' + name)
        return {k: matches[0][k] for k in ['name', 'id', 'index']} | dict(value=value)

    def one(pair):
        c, previous = pair
        original, provenance = native.original(SimpleNamespace(session=a.session, host=a.reference_host), c)
        require(all(previous[k] == value for k, value in provenance.items()), 'Original provenance differs')
        travel = (c['pitch'] - 128) * (24 / 127 if c['pitch'] >= 128 else 24 / 128)
        values = {'Auto BPM': 0, 'Quantize': 0, 'Scene FX': 1 / 9, 'Scene enabled': 0, 'Isolate enabled': 0,
            'Release lever': 0, 'Sample source': 0, 'Default / User settings': 1, 'Sampler level': c['level'] / 255,
            'Sampler pitch travel': (travel + 24) / 48, 'Sampler mute': 0, 'Bypass': 0, 'Send/return': 0,
            'Output gain': 2 / 3, 'Input gain': 2 / 3}
        for label, node in zip(['Kick', 'Snare', 'Clap', 'Hi-hat'], ['Kick', 'Snare', 'Clap', 'Hihat'], strict=True):
            profile = c['settings'].get(node, {})
            values[label + ' gain'] = (6 - profile.get('GainCb', 3)) / 6
            values[label + ' decay'] = profile.get('DecayCb', 1) / 2
            values[label + ' envelope'] = profile.get('EnvelopeCb', 0)
        events = []
        for frame in c['hits']:
            note = 36 + list(DRUMS).index(c['drum'])
            events += [dict(frame=frame, type='midi', bytes=[0x90, note, 127]), dict(frame=frame + 32, type='midi', bytes=[0x80, note, 0])]
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='candidate', expected_plugin=identity,
            sample_rate=48000, bpm=120, tail_seconds=0, post_render_message_pump_ms=100,
            parameters=[setting(k, v) for k, v in values.items()], events=sorted(events, key=lambda e: e['frame']))
        path = root / (c['name'] + '.json'); save_json(path, plan); folder = root / c['name']
        run([a.host, 'render', a.plugin, a.session / 'silence.wav', path, folder, c['block']])
        receipt = json.loads((folder / 'receipt.json').read_text())
        require(receipt['complete'] and receipt['role'] == 'candidate' and receipt['host_sha256'] == host_hash
            and receipt['sample_rate'] == 48000 and receipt['frames'] == 480000 and receipt['maximum_block_size'] == c['block']
            and receipt['input_sha256'] == provenance['input_sha256'] and receipt['plugin']['format'] == inventory['format'], 'Wrapper receipt differs')
        require(json.loads((folder / 'plan.json').read_text()) == plan and receipt['plan_sha256'] == sha256(path) == sha256(folder / 'plan.json'), 'Wrapper plan differs')
        for file, field in [('audio.wav', 'output_sha256'), ('state-before.bin', 'initial_state_sha256'), ('state-after.bin', 'final_state_sha256'),
                            ('parameter-log.json', 'parameter_log_sha256'), ('inventory-after.json', 'final_inventory_sha256')]:
            require(sha256(folder / file) == receipt[field], 'Wrapper artifact differs')
        for member in receipt['plugin']['binary_files']:
            require(sha256(a.plugin / member['path']) == member['sha256'] == binaries[member['path']], 'Wrapper binary changed')
        entries = json.loads((folder / 'parameter-log.json').read_text())['entries']
        require(len(entries) == len(plan['parameters']), 'Wrapper readback count differs')
        for request, actual in zip(plan['parameters'], entries, strict=True):
            require(actual['frame'] == -1 and all(actual[k] == request[k] for k in ['name', 'id', 'index'])
                and np.float32(actual['requested_value']) == np.float32(request['value'])
                and abs(actual['immediate_readback'] - request['value']) <= 1e-6, 'Wrapper parameter delivery differs')
        candidate_path = a.native_report.parent / (c['name'] + '.wav')
        require(sha256(candidate_path) == previous['candidate_sha256'], 'Native audio changed')
        rate, rendered = float_wav(folder / 'audio.wav'); native_rate, engine = float_wav(candidate_path)
        require(rate == native_rate == 48000 and rendered.shape == engine.shape == original.shape, 'Wrapper extent differs')
        delta = rendered.astype(float) - engine.astype(float); energy = float(np.sum(engine.astype(float) ** 2))
        peak = float(np.max(np.abs(delta))); relative = float(np.linalg.norm(delta) / np.sqrt(energy)) if energy > 1e-20 else 0
        windows = [dict(start=w['start'], stop=w['stop'], kind=w['kind'], score=screen(original[32:][w['start']:w['stop']], rendered[32:][w['start']:w['stop']])) for w in previous['windows']]
        delivery = peak <= 1e-5 and relative <= 1e-5 and receipt['reported_latency_frames'] == 32
        passed = delivery and all(w['score']['passed'] for w in windows)
        print('PASS' if passed else 'FAIL', inventory['format'], c['name'], flush=True)
        return provenance | dict(passed=passed, windows=windows, native_sha256=sha256(candidate_path), wrapper_sha256=receipt['output_sha256'],
            wrapper_receipt_sha256=sha256(folder / 'receipt.json'), reported_latency=receipt['reported_latency_frames'],
            delivery_passed=delivery, max_wrapper_native_difference=peak, relative_wrapper_native_error=relative)

    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool: rows = list(pool.map(one, zip(cases, report['cases'], strict=True)))
    require(bound == native.bindings() and own == sha256(Path(__file__)) and report_hash == sha256(a.native_report)
        and host_hash == sha256(a.host) and all(sha256(a.plugin / path) == h for path, h in binaries.items()), 'Wrapper inputs changed')
    save_json(root / 'verification.json', dict(kind='rmx220-user-drum-wrapper-validation', passed=all(r['passed'] for r in rows),
        format=inventory['format'], programs=len(rows), cases=rows, source_sha256=bound, verifier_sha256=own, native_report_sha256=report_hash,
        host_sha256=host_hash, plugin_binaries_sha256=binaries, acceptance=ACCEPTANCE,
        scope='Existing original-reference User drum programs through explicit AU/VST3 MIDI and normalized controls. All native reference windows, separate1e-5 delivery limits and latency32. No additional fresh Original, DAW, controller or hardware claim.'))
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__': raise SystemExit(main())
