#!/usr/bin/env python3
"""Verify read-only settled Up scalar observations against capture and static I/O data."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import IDENTITY
from tools.rmx_reverb_characterize import controls
from tools.rmx_reverb_up_model import model_checked


def extract(args):
    model = model_checked(args)
    if args.report.exists() or args.header.exists():
        raise ValueError('Geometry report/header must be new')
    receipts = []
    for folder in (args.original, args.debugger):
        receipt = json.loads((folder/'receipt.json').read_text())
        if (not receipt['complete'] or receipt['role'] != 'reference' or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())
                or receipt['maximum_block_size'] != 128):
            raise ValueError('Wrong original scalar-capture identity/block')
        for path, field in [(folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                (Path(receipt['input_path']), 'input_sha256'), (folder/'state-before.bin', 'initial_state_sha256'),
                (folder/'state-after.bin', 'final_state_sha256'), (folder/'parameter-log.json', 'parameter_log_sha256'),
                (folder/'inventory-after.json', 'final_inventory_sha256')]:
            if sha256(path) != receipt[field]:
                raise ValueError('Modified scalar capture file')
        plan = json.loads((folder/'plan.json').read_text())
        expected_events = [dict(frame=32768+(raw-1)*4096, name='SceneVolume', value=raw/255) for raw in range(1, 256)]
        expected_controls = controls(dict(direction='up', main=0, amount=128, cutoff=0))
        if (plan['sample_rate'] != 48000 or plan['bpm'] != 120 or plan['tail_seconds'] != 1
                or {p['name']: p['value'] for p in plan['parameters']} != expected_controls
                or [{k: e[k] for k in ('frame', 'name', 'value')} for e in plan['events']] != expected_events
                or any(e['type'] != 'parameter' for e in plan['events'])):
            raise ValueError('Scalar sweep recipe differs')
        log = json.loads((folder/'parameter-log.json').read_text())['entries']
        requests = [p | dict(frame=-1) for p in plan['parameters']] + plan['events']
        if len(log) != len(requests):
            raise ValueError('Wrong scalar sweep log extent')
        for requested, actual in zip(requests, log):
            if (any(actual[k] != requested[k] for k in ('index', 'name', 'id', 'frame'))
                    or np.float32(actual['requested_value']) != np.float32(requested['value'])
                    or abs(actual['immediate_readback']-float(np.float32(requested['value']))) > 1e-14):
                raise ValueError('Scalar sweep immediate readback differs')
        final = expected_controls | dict(SceneVolume=1)
        inventory = {p['name']: p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
        if any(abs(inventory[k]-float(np.float32(v))) > 1e-14 for k, v in final.items()):
            raise ValueError('Scalar sweep final readback differs')
        rate, audio = float_wav(folder/'audio.wav'); source_rate, source = float_wav(Path(receipt['input_path']))
        if rate != 48000 or source_rate != rate or len(source) != 1081344 or len(audio) != len(source)+48000 or np.any(source) or np.any(audio):
            raise ValueError('Scalar sweep zero-input recipe differs')
        receipts.append(receipt)
    if (any(receipts[0][k] != receipts[1][k] for k in ('input_sha256', 'plan_sha256', 'output_sha256', 'host_sha256'))
            or receipts[0]['plugin']['binary_files'] != receipts[1]['plugin']['binary_files']):
        raise ValueError('Debugger capture differs from unchanged original')
    raw = [json.loads(line) for line in args.log.read_text().splitlines()]
    if [r['raw'] for r in raw] != list(range(256)):
        raise ValueError('Incomplete settled scalar observations')
    order = [1, 3, 2, 4, 0]; rows = []; fractional_errors = []; integer_checked = 0
    bases = np.array([[1032, 1146], [1060, 1856], [1145, 1961], [1916, 1115], [1992, 1190]], dtype=np.float32)
    for value, observed in enumerate(raw):
        if (any(observed[k] != value for k in ('main', 'fast_main', 'pending_main'))
                or observed['amount'] != 128 or observed['ramp_blocks'] != 0 or observed['network_call'] != 1023+value*128):
            raise ValueError('Unsettled or wrong scalar control')
        delays = np.zeros((5, 2)); gains = np.zeros((5, 2))
        for index, pair in enumerate(order):
            for ch, start in enumerate((0xb6e4, 0xb720)):
                delays[pair, ch] = observed['memory'][hex(start+index*4)]
            for ch, start in enumerate((0xb63c, 0xb650)):
                gains[pair, ch] = observed['memory'][hex(start+index*4)]
        if value >= 4:
            if delays.astype(int).tolist() != model['main_rows'][value]['delays']:
                raise ValueError('Observed integer geometry differs from independently measured I/O row '+str(value))
            integer_checked += 10
        if np.any(delays <= 0) or np.any(delays > 48000) or np.any(gains <= 0) or np.any(gains >= 1):
            raise ValueError('Invalid scalar delays/feedback')
        a = [1, observed['input_a1'], observed['input_a2']]
        if not 0 < observed['input_b'] <= 1 or np.any(abs(np.roots(a)) >= 1):
            raise ValueError('Invalid scalar input-bandpass coefficients')
        v = np.float32(1)-np.float32(max(0, value-3))*np.float32(1/252)
        proposed = (np.float32(.3)+np.float32(3)*((v*v)*(v*v)))*bases
        fractional_errors.extend(abs(delays-proposed.astype(float)).ravel().tolist())
        rows.append(dict(main_raw=value, delays=delays.tolist(), gain_left=gains[:, 0].tolist(), gain_right=gains[:, 1].tolist(),
                         bandpass_b=observed['input_b'], bandpass_a=a, return_level_sub1_128=observed['return_gain']))
    def number(value, suffix=''):
        text = format(float(value), '.17g')
        if '.' not in text and 'e' not in text:
            text += '.0'
        return text+suffix
    header = '// Own read-only settled Up scalar observations; see the numeric provenance report.\n#pragma once\n#include <array>\n'
    header += 'struct ReverbUpMotionRow {std::array<std::array<float,2>,5> delays;std::array<double,5> gainL,gainR;std::array<double,2> bandpassA;double bandpassB;};\n'
    header += 'constexpr std::array<ReverbUpMotionRow,256> reverbUpMotionControls{{\n'
    for row in rows:
        ds = '{{'+','.join('{{'+','.join(number(v, 'f') for v in pair)+'}}' for pair in row['delays'])+'}}'
        arrays = ['{{'+','.join(number(v) for v in values)+'}}' for values in (row['gain_left'], row['gain_right'], row['bandpass_a'][1:])]
        header += '{'+','.join([ds, *arrays, number(row['bandpass_b'])])+'},\n'
    header += '}};\n'; args.header.parent.mkdir(parents=True, exist_ok=True)
    with args.header.open('x') as stream:
        stream.write(header)
    save_json(args.report, dict(kind='rmx220-reverb-up-settled-fractional-scalar-calibration', passed=True,
        model_sha256=sha256(args.model), calibration_sha256=sha256(args.calibration), script_sha256=sha256(Path(__file__)),
        observation_script_sha256=sha256(args.script), scalar_log_sha256=sha256(args.log), header_sha256=sha256(args.header),
        original_receipt_sha256=sha256(args.original/'receipt.json'), debugger_receipt_sha256=sha256(args.debugger/'receipt.json'),
        audio_sha256=receipts[0]['output_sha256'], reference_host_sha256=receipts[0]['host_sha256'], original_binary_files=receipts[0]['plugin']['binary_files'],
        original_debugger_audio_byte_identical=True, source_audio_silent=True, all_control_readbacks_verified=True,
        independently_measured_integer_taps_agree=integer_checked,
        nominal_quartic_fractional_comparison=dict(taps=2560,unequal_taps=sum(error != 0 for error in fractional_errors), maximum_absolute_error_frames=max(fractional_errors)),
        cases=rows, scope='Read-only observed settled state across 256 Main controls after ascending from an initially silent Main0. The 2520 audible integer taps agree with prior independent I/O measurements; fractional/hidden states require separate moving-waveform validation. Main0..3 filter fields describe this initial history, not a validated general filter-reset rule. Identical zero-input audio is an interference check, not a sound-fidelity pass. No original instructions, binary or raw debugger output is distributed.'))
    print('Verified 256 settled rows and', integer_checked, 'independent integer taps; fractional formula differs at', sum(error != 0 for error in fractional_errors), 'taps')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'calibration', 'original', 'debugger', 'script', 'log', 'report', 'header'):
        p.add_argument('--'+name, type=Path, required=True)
    extract(p.parse_args())


if __name__ == '__main__':
    main()
