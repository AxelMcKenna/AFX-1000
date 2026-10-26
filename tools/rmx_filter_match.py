#!/usr/bin/env python3
"""Render and screen static filter captures without wet gain/delay fitting."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.fidelity import align, spectral_metrics
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import IDENTITY, new_directory, run


def screen(reference, candidate):
    channels = []
    for i, name in enumerate(('left', 'right')):
        a, b = reference[:, i].astype(float), candidate[:, i].astype(float)
        energy = a@a
        absolute = float(np.sqrt(np.mean((a-b)**2)))
        relative = float(np.linalg.norm(a-b)/np.sqrt(energy)) if energy > 1e-20 else None
        channels.append({'channel': name, 'relative_rms_error': relative,
                         'absolute_error_rms': absolute,
                         'passed': relative <= .01 if relative is not None else absolute <= 1e-8})
    return {'passed': all(c['passed'] for c in channels), 'channels': channels}


def match(args):
    calibration = json.loads(args.calibration.read_text())
    if (calibration.get('kind') != 'fractional-bypass-calibration'
            or calibration.get('verified') is not True or calibration.get('eligible_for_review') is not True
            or calibration.get('sample_rate') != 48000):
        raise ValueError('Requires a separately reviewed 48 kHz bypass calibration')
    root = new_directory(args.output)
    repo = Path(__file__).resolve().parents[1]
    sources = [*sorted((repo/'include/rmx').glob('*.h')), *sorted((repo/'src/core').glob('*.cpp')),
               repo/'tools/render.cpp', Path(__file__).resolve()]
    results, names, skipped = [], set(), []
    for session in args.session:
        for folder in sorted(session.iterdir()):
            if not folder.is_dir() or not (folder/'receipt.json').exists():
                continue
            effect = folder.name.split('-')[0]
            if effect not in ('bpf', 'hpf', 'lpf', 'crush') or ('-grid-' in folder.name and not args.include_grid):
                continue
            receipt = json.loads((folder/'receipt.json').read_text())
            plan = json.loads((folder/'plan.json').read_text())
            if (not receipt['complete'] or receipt['role'] != 'reference'
                    or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
                raise ValueError('Wrong reference: ' + str(folder))
            if plan.get('events'):
                skipped.append(folder.name+': event plan requires native-host validation')
                continue
            input_path = Path(receipt['input_path'])
            for path, key in ((folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                              (input_path, 'input_sha256')):
                if sha256(path) != receipt[key]:
                    raise ValueError('Modified capture: ' + str(path))
            controls = {p['name']: p['value'] for p in plan['parameters']}
            if (plan['sample_rate'] != 48000 or controls['Sub2Volume'] != 0
                    or controls['DefaultSwitch'] != 1 or controls['InputButton'] != 1
                    or controls['XpadButton'] != 0):
                raise ValueError('Outside static factory recipe')
            if folder.name in names:
                raise ValueError('Duplicate case name: ' + folder.name)
            names.add(folder.name)
            settings = {'input_gain': 0, 'output_gain': 0, 'bypass': 0, 'auto_tempo': 0, 'quantize': 0,
                        'tempo': plan['bpm'], 'scene_on': 1, 'scene_type': {'bpf': 0, 'hpf': 5, 'lpf': 6, 'crush': 7}[effect],
                        'scene_source': 0, 'scene_depth': controls['SceneVolume'],
                        'scene_time': controls['Sub1Volume']*7, 'scene_resonance': 0,
                        'sampler_mute': 1, 'isolate_on': 0}
            preset, output = root/(folder.name+'.rmx'), root/(folder.name+'.wav')
            preset.write_text('RMX_STATE 1\n'+''.join(f'param {k} {v:.9g}\n' for k, v in settings.items()))
            run([args.renderer, input_path, output, preset, plan['tail_seconds']])
            rate, reference = float_wav(folder/'audio.wav')
            candidate_rate, candidate = float_wav(output)
            if rate != 48000 or candidate_rate != rate or len(reference) != len(candidate):
                raise ValueError('Mismatched render extent/rate')
            a, b, alignment = align(reference, candidate, calibration['candidate_delay_frames'])
            input_rate, input_audio = float_wav(input_path)
            if input_rate != rate:
                raise ValueError('Unexpected input rate')
            item = {'case': folder.name, 'effect': effect, 'bpm': plan['bpm'],
                    'raw_controls': {k: round(controls[k]*255) for k in ('SceneVolume', 'Sub1Volume', 'Sub2Volume')},
                    'receipt_sha256': sha256(folder/'receipt.json'), 'candidate_sha256': sha256(output),
                    'preset_sha256': sha256(preset), 'alignment': alignment, 'whole': screen(a, b)}
            if len(a) > len(input_audio)+4800:
                # Input has ended: no strong dry path can mask an incorrect tail.
                item['tail'] = screen(a[len(input_audio):], b[len(input_audio):])
            if len(input_audio) in (96000, 240000):
                item['direct_left_impulse'] = screen(a[48000:54000], b[48000:54000])
            if len(input_audio) == 48000*6:
                item['spectral_diagnostics'] = spectral_metrics(a, b, rate)
            results.append(item)
            print('PASS' if all(item[k]['passed'] for k in ('whole', 'tail', 'direct_left_impulse') if k in item)
                  else 'FAIL', folder.name, flush=True)
    if not results:
        raise ValueError('No matching captures')
    passed = all(item[k]['passed'] for item in results for k in ('whole', 'tail', 'direct_left_impulse') if k in item)
    save_json(root/'comparison.json', {'kind': 'rmx220-static-filter-comparison', 'passed': passed,
        'sample_rate': 48000, 'physical_hardware': False, 'maximum_relative_rms_error': .01,
        'reference_identity': IDENTITY,
        'calibration_sha256': sha256(args.calibration), 'renderer_sha256': sha256(args.renderer),
        'source_sha256': {str(path.relative_to(repo)): sha256(path) for path in sources},
        'scope': 'Static factory Normal-width, Sub2 zero. Per-channel unscaled RMS; no perceived-similarity percentage.',
        'skipped': skipped, 'cases': results})
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, action='append', required=True)
    for name in ('renderer', 'calibration', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--include-grid', action='store_true')
    raise SystemExit(match(parser.parse_args()))


if __name__ == '__main__':
    main()
