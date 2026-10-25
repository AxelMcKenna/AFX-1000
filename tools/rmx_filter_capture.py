#!/usr/bin/env python3
"""Capture static factory filter identification and independent validation cases.

Requires a separately obtained original RMX-1000 Plug-in 2.2.0. Outputs contain
reference recordings and belong outside Git. Each destination must be new.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, probe, run
from tools.rmx_filter_identify import CALIBRATION_RAW


BUTTONS = {'bpf': 'BpfEchoButton', 'hpf': 'HpfEchoButton', 'lpf': 'LpfEchoButton'}
TIMES = (0, 16, 32, 48, 64, 80, 96, 112, 124, 127, 128, 129, 131, 132,
         144, 160, 176, 192, 208, 224, 240, 255)


def capture(args):
    root = new_directory(args.output)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires the original RMX-1000 Plug-in 2.2.0')

    def parameter(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous control: ' + name)
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | {'value': value}

    short, impulses = np.zeros((96000, 2)), np.zeros((240000, 2))
    short[48000, 0], short[72000, 1] = .05, -.04
    impulses[48000, 0], impulses[144000, 1] = .05, -.04
    for name, x in (('short', short), ('impulses', impulses), ('probe', probe())):
        write_wav(root/(name+'.wav'), 48000, x.ravel())
    cases = []

    def add(name, effect, input_name, main=128, time=128, bpm=120, tail=0, off=False):
        cases.append({'name': name, 'effect': effect, 'input': input_name+'.wav',
                      'main': main, 'time': time, 'bpm': bpm, 'tail_seconds': tail, 'button_off': off})

    for raw in range(256):
        add('bpf-main-0' if raw == 0 else f'bpf-grid-{raw}', 'bpf', 'short', raw)
    for effect in ('hpf', 'lpf'):
        values = set(CALIBRATION_RAW) | {17, 81, 147, 233}
        if effect == 'lpf':
            values |= {220, 228, 236, 244, 248, 252, 254}
        for raw in sorted(values):
            add(f'{effect}-main-{raw}', effect, 'short', raw)
    for effect in BUTTONS:
        for raw in TIMES:
            add(f'{effect}-time-{raw}', effect, 'impulses', time=raw, tail=12)
        for raw in (17, 81, 147, 233, 249, 253):
            add(f'{effect}-probe-main-{raw}', effect, 'probe', raw, tail=12)
        for raw in (16, 96, 176, 255):
            add(f'{effect}-137-time-{raw}', effect, 'probe', 233, raw, 137, 12)
        add(effect+'-off', effect, 'impulses', off=True, tail=12)
    for n, case in enumerate(cases):
        controls = {'AutoButton': 1, 'QuantizeButton': 0, 'InputButton': 1, 'XpadButton': 0,
                    'IsolatorButton': 0, 'DefaultSwitch': 1, 'UserSwitch': 0,
                    'Sub1Volume': case['time']/255, 'Sub2Volume': 0,
                    'SceneVolume': case['main']/255, BUTTONS[case['effect']]: 1}
        plan = {'schema_version': 1, 'kind': 'audio-plugin-capture-plan', 'role': 'reference',
                'expected_plugin': IDENTITY, 'sample_rate': 48000, 'bpm': case['bpm'],
                'tail_seconds': case['tail_seconds'],
                'parameters': [parameter(k, v) for k, v in controls.items()], 'events': []}
        if case['button_off']:
            plan['events'] = [parameter(BUTTONS[case['effect']], 0) | {'type': 'parameter', 'frame': 52800}]
        save_json(root/(case['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/case['input'], root/(case['name']+'.json'),
             root/case['name'], 128])
        case['receipt_sha256'] = sha256(root/case['name']/'receipt.json')
        print(n+1, '/', len(cases), case['name'], flush=True)
    save_json(root/'matrix.json', {'kind': 'rmx220-filter-capture-matrix', 'cases': cases,
                                  'capture_script_sha256': sha256(Path(__file__))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host', 'plugin', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    capture(parser.parse_args())


if __name__ == '__main__':
    main()
