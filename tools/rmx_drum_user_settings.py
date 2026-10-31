#!/usr/bin/env python3
"""Load bounded drum customization XML through the Original's public state API."""
import argparse
import concurrent.futures
import json
import struct
from pathlib import Path

import numpy as np

from tools.rmx_drums import DRUMS, FRAMES, plan_for, require
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.reference_audio import save_json, sha256, write_wav


def chunks(data):
    require(len(data) >= 4 and struct.unpack_from('<I', data)[0] == len(data) - 4, 'Invalid native state extent')
    result = {}; offset = 4
    while offset < len(data):
        require(offset + 8 <= len(data), 'Truncated state header')
        tag = data[offset:offset + 4]; length = struct.unpack_from('<I', data, offset + 4)[0]; offset += 8
        require(tag not in result and length <= len(data) - offset, 'Duplicate/truncated native state chunk')
        result[tag] = data[offset:offset + length]; offset += length
    require(list(result) == [b'para', b'sett', b'cstm'] and len(result[b'para']) == 52 * 4 and len(result[b'sett']) == 9, 'Unsupported Original state schema')
    return result


def xml(settings):
    fields = []
    for drum in ['Kick', 'Snare', 'Clap', 'Hihat']:
        values = settings.get(drum, {})
        for field, default, maximum in [('GainCb', 3, 6), ('DecayCb', 1, 2), ('EnvelopeCb', 0, 1)]:
            value = values.get(field, default)
            require(isinstance(value, int) and 0 <= value <= maximum, 'Invalid drum setting')
            fields.append(f'<{drum}{field}>{value}</{drum}{field}>')
    extra = ''
    if 'Xpad' in settings:
        require(set(settings['Xpad']).issubset({f'Position{i}' for i in range(5)}), 'Unknown strip assignment')
        values = []
        for name, value in settings['Xpad'].items():
            require(isinstance(value, int) and 0 <= value <= 15, 'Invalid strip beat choice')
            values.append(f'<{name}>{value}</{name}>')
        extra = '<Xpad>' + ''.join(values) + '</Xpad>'
    return '<?xml version="1.0" encoding="UTF-8"?>\n<RMX-1000 version="1.0"><XpadFx><Osc>' + ''.join(fields) + '</Osc>' + extra + '</XpadFx></RMX-1000>'


def state(template, settings, filename='', directory=''):
    original = chunks(template); text = xml(settings).encode('utf-8')
    # Native customization payload: length-prefixed file name, directory, RSD text.
    values = [filename.encode('utf-8'), directory.encode('utf-8'), text]
    original[b'cstm'] = b''.join(struct.pack('<I', len(value)) + value for value in values)
    data = b''.join(tag + struct.pack('<I', len(value)) + value for tag, value in original.items())
    encoded = struct.pack('<I', len(data)) + data
    require(chunks(encoded) == original, 'Native state round trip differs')
    return encoded


def recipe(stage='loader'):
    if stage in ['fresh', 'fresh2']:
        rng = np.random.default_rng(0x44555031 if stage == 'fresh' else 0x44555032)
        rows = []
        for drum, node in zip(DRUMS, ['Kick', 'Snare', 'Clap', 'Hihat'], strict=True):
            for i in range(16):
                hits = [int(rng.integers(1, 128)), 48031 + i * 17, 48203 + i * 19, 96113 + i * 23, 192173 + i * 29, 336373 + i * 31]
                rows.append(dict(name=f'user-{stage}-{drum}-{i:02d}', drum=drum, variant=stage,
                    settings={node: dict(GainCb=int(rng.integers(7)), DecayCb=int(rng.integers(3)), EnvelopeCb=int(rng.integers(2)))},
                    level=int(rng.choice([3, 17, 39, 107, 121, 128, 133, 191, 239, 254])),
                    pitch=int(rng.choice([0, 3, 37, 117, 120, 121, 128, 135, 136, 139, 203, 255])),
                    block=[8, 31, 79, 257, 1021, 4093, 4096, 127][i % 8], hits=hits))
        return rows
    if stage == 'profiles':
        rows = []
        for drum, node in zip(DRUMS, ['Kick', 'Snare', 'Clap', 'Hihat'], strict=True):
            for gain in range(7):
                for decay in range(3):
                    for envelope in range(2):
                        rows.append(dict(name=f'user-{drum}-g{gain}-d{decay}-e{envelope}', drum=drum, variant='profiles',
                            settings={node: dict(GainCb=gain, DecayCb=decay, EnvelopeCb=envelope)},
                            level=128, pitch=128, block=128, hits=[48000, 192000, 336000]))
        return rows
    require(stage == 'loader', 'Unknown customization stage')
    rows = []
    for variant, settings in [('neutral', {}), ('gain0', {'Kick': {'GainCb': 0}}), ('gain6', {'Kick': {'GainCb': 6}}),
                              ('decay0', {'Kick': {'DecayCb': 0}}), ('decay2', {'Kick': {'DecayCb': 2}}),
                              ('envelope1', {'Kick': {'EnvelopeCb': 1}}), ('snare-decay0', {'Snare': {'DecayCb': 0}}),
                              ('hat-envelope1', {'Hihat': {'EnvelopeCb': 1}})]:
        drum = 'snare' if variant.startswith('snare') else 'hat' if variant.startswith('hat') else 'kick'
        rows.append(dict(name='user-loader-' + variant, drum=drum, variant=variant, settings=settings,
                         level=128, pitch=128, block=128, hits=[48000, 192000, 336000]))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['loader', 'profiles', 'fresh', 'fresh2'], default='loader')
    p.add_argument('--prediction', type=Path)
    for key in ['host', 'plugin', 'template', 'session']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); template_hash = sha256(a.template); template = a.template.read_bytes(); chunks(template)
    prediction = None
    if a.stage in ['fresh', 'fresh2']:
        from tools.rmx_drum_user_match import bindings
        require(a.prediction is not None, 'Fresh settings require sealed audio predictions')
        prediction = json.loads(a.prediction.read_text())
        require(prediction['source_sha256'] == bindings() and prediction['cases'] == recipe(a.stage), 'Prediction source/recipe changed')
        require(sha256(Path(prediction['renderer'])) == prediction['renderer_sha256'], 'Prediction binary changed')
        for name, h in prediction['output_sha256'].items():
            require(sha256(a.prediction.parent / 'predictions' / (name + '.wav')) == h, 'Prediction WAV changed')
    root = new_directory(a.session); inventory = json.loads(run([a.host, 'inventory', a.plugin]))
    require(all(inventory[k] == v for k, v in IDENTITY.items()), 'Wrong Original identity')
    save_json(root / 'inventory.json', inventory); write_wav(root / 'silence.wav', 48000, np.zeros(FRAMES * 2))
    if prediction: (root / 'prediction.json').write_bytes(a.prediction.read_bytes())
    own = sha256(Path(__file__)); binary = inventory['binary_files']; rows = []
    def one(c):
        rsd = root / (c['name'] + '.RSD'); rsd.write_text(xml(c['settings']))
        saved = root / (c['name'] + '.bin'); saved.write_bytes(state(template, c['settings'], str(rsd.resolve()), str(root.resolve()) + '/'))
        plan = plan_for(c, inventory)
        plan['parameters'] = [s | dict(value=0 if s['name'] == 'DefaultSwitch' else 1 if s['name'] == 'UserSwitch' else s['value']) for s in plan['parameters']]
        plan['initial_state'] = dict(path=saved.name, sha256=sha256(saved))
        path = root / (c['name'] + '.json'); save_json(path, plan)
        run([a.host, 'render', a.plugin, root / 'silence.wav', path, root / c['name'], c['block']])
        receipt = json.loads((root / c['name'] / 'receipt.json').read_text())
        require(receipt['complete'] and receipt['initial_state_sha256'] == sha256(root / c['name'] / 'state-before.bin'), 'Incomplete state capture')
        retained = chunks((root / c['name'] / 'state-before.bin').read_bytes())
        require(retained[b'cstm'] == chunks(saved.read_bytes())[b'cstm'], 'Original did not retain the requested customization XML')
        print('LOADED', c['name'], flush=True)
        return c | dict(receipt_sha256=sha256(root / c['name'] / 'receipt.json'), requested_state_sha256=sha256(saved), customization_retained=True)
    with concurrent.futures.ThreadPoolExecutor(2) as pool: rows = list(pool.map(one, recipe(a.stage)))
    require(sha256(a.template) == template_hash and sha256(Path(__file__)) == own, 'Loader inputs changed')
    save_json(root / 'matrix.json', dict(kind='original-drum-customization-loader-discovery', stage=a.stage, cases=rows, template_sha256=template_hash,
        prediction_sha256=sha256(a.prediction) if prediction else None,
        loader_sha256=own, original_binary_files=binary, scope='Public native-state load, generated drum-only RSD XML and User switches. '
        'Retention is checked; audio effects and neutral parity require a separate audit. No candidate fidelity claim.'))


if __name__ == '__main__':
    main()
