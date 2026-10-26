#!/usr/bin/env python3
"""Isolated-pulse probes for slow Reverb Down parameter/state transitions."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_motion import checked, event_values, parameters, recipe
from tools.rmx_spiral_core import calibration


def wait_recipe():
    waves, cases = {}, []
    event = 192037
    for wait in (12000, 96000, 384000):
        name = f'pulse-{wait}'
        source = np.zeros((864000, 2))
        source[event+wait, 0] = .02
        waves[name] = source
        for control, start, end in (('main', 0, 128), ('main', 128, 192),
                                    ('amount', 128, 255), ('amount', 255, 0)):
            values = dict(main=128, amount=128, cutoff=0)
            values[control] = start
            cases.append(dict(name=f'down-wait-{control}-{start}-{end}-{wait}', source=name,
                direction='down', **values, enabled=1, block=128,
                tail=90 if max(values['amount'], end if control=='amount' else 0)>=224 else 18,
                events=[dict(frame=event, control=control, value=end)], baseline=None))
        for main in (128, 255):
            cases.append(dict(name=f'down-wait-on-{main}-{wait}', source=name,
                direction='down', main=main, amount=128, cutoff=0, enabled=0, block=128,
                tail=18, events=[dict(frame=event, control='enabled', value=1)], baseline=None))
    return waves, cases


def capture(args):
    calibration(args.calibration)
    root = new_directory(args.session)
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json', inventory)
    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous parameter')
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | dict(value=value)
    waves, cases = wait_recipe()
    for name, source in waves.items():
        write_wav(root/(name+'.wav'), 48000, source.ravel())
    for case in cases:
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference',
            expected_plugin=IDENTITY, sample_rate=48000, bpm=120, tail_seconds=case['tail'],
            parameters=[setting(k,v) for k,v in parameters(case).items()],
            events=[setting(e['name'],e['value']) | dict(frame=e['frame'],type='parameter') for e in event_values(case)])
        save_json(root/(case['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/(case['source']+'.wav'), root/(case['name']+'.json'), root/case['name'], case['block']])
        case['receipt_sha256'] = sha256(root/case['name']/'receipt.json')
        print(case['name'], flush=True)
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-down-state-wait-captures', cases=cases,
        calibration_sha256=sha256(args.calibration), capture_script_sha256=sha256(Path(__file__))))


def analyze(args):
    calibration(args.calibration)
    rows = []
    for stage, session, (waves, cases) in (('state-probes', args.probes, recipe('state-probes')),
                                         ('state-wait', args.wait, wait_recipe())):
        records = {}
        for case in cases:
            audio, source, provenance = checked(session, case, waves[case['source']])
            folder = session/case['name']
            receipt = json.loads((folder/'receipt.json').read_text())
            for name, field in (('state-before.bin','initial_state_sha256'), ('state-after.bin','final_state_sha256'),
                                ('parameter-log.json','parameter_log_sha256'), ('inventory-after.json','final_inventory_sha256')):
                if sha256(folder/name) != receipt[field]:
                    raise ValueError('Modified auxiliary capture file')
            plan = json.loads((folder/'plan.json').read_text())
            expected = [p | dict(frame=-1) for p in plan['parameters']] + plan['events']
            log = json.loads((folder/'parameter-log.json').read_text())['entries']
            if len(log) != len(expected):
                raise ValueError('Parameter log extent differs')
            for actual, requested in zip(log, expected):
                if (any(actual[k] != requested[k] for k in ('frame','index','id','name'))
                        or np.float32(actual['requested_value']) != np.float32(requested['value'])
                        or abs(actual['immediate_readback']-float(np.float32(requested['value'])))>1e-14):
                    raise ValueError('Parameter request/readback differs')
            final = {p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
            target = {p['name']:p['value'] for p in expected}
            if any(abs(final[k]-float(np.float32(v)))>1e-14 for k,v in target.items()):
                raise ValueError('Final parameter readback differs')
            row = provenance | dict(stage=stage, initial=parameters(case), events=case['events'],
                parameter_log_sha256=receipt['parameter_log_sha256'], readbacks_verified=True)
            pulses = np.flatnonzero(np.any(source!=0, axis=1))
            if len(pulses) == 1:
                pulse = int(pulses[0])
                # The bypass offset is frozen; this reports observed onset, not alignment fitting.
                wet = audio.copy()
                wet[pulse+32] = 0
                changed = np.flatnonzero(np.any(np.abs(wet)>1e-10, axis=1))
                row.update(pulse_input_frame=pulse, pulse_after_event_frames=pulse-case['events'][0]['frame'] if case['events'] else None,
                    wet_onset_frame=int(changed[0]) if len(changed) else None,
                    wet_onset_after_input_and_bypass_frames=int(changed[0])-pulse-32 if len(changed) else None,
                    maximum_wet_absolute_sample=float(np.abs(wet).max()))
                if len(changed):
                    row['first_wet_sample'] = audio[int(changed[0])].tolist()
            if case['name'].startswith('down-dry-main-'):
                at=case['events'][0]['frame']
                # Input starts 128 samples before the event, ahead of every wet path in this window.
                direct=audio[at+32:at+32+250]
                x=source[at:at+250].astype(float)
                gains=np.sum(direct*x,axis=1)/np.sum(x*x,axis=1)
                row['dry_gain_samples']=[dict(after_event_frames=i, gain=float(gains[i])) for i in (0,1,27,28,31,32,63,64,127,128,191,192,249)]
                row['dry_gain_linear_projection_relative_error']=float(np.linalg.norm(direct-gains[:,None]*x)/np.linalg.norm(direct))
            if case['baseline']:
                before = records[case['baseline']]
                length = min(len(before),len(audio))
                row['settled_vs_original_target_baseline'] = screen(before[:length],audio[:length])
                row['baseline_case'] = case['baseline']
            if not case['events']:
                records[case['name']] = audio
            rows.append(row)
    save_json(args.report, dict(kind='rmx220-reverb-down-state-horizon-characterization', cases=rows,
        calibration_sha256=sha256(args.calibration), identifier_sha256=sha256(Path(__file__)),
        motion_recipe_sha256=sha256(Path(__file__).with_name('rmx_reverb_motion.py')),
        full_reverb_match=False, physical_hardware=False,
        limitations=['Original-versus-original observations, not clone acceptance.',
            'A changed impulse onset after a settled host control does not uniquely identify the smoothing or delay implementation.',
            'Dry projections apply only to the short pre-wet window; no gain fit enters waveform acceptance.']))
    print('Verified and characterized', len(rows), 'state captures')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('capture-wait')
    for name in ('host','plugin','session','calibration'):
        p.add_argument('--'+name,type=Path,required=True)
    p=commands.add_parser('analyze')
    for name in ('probes','wait','calibration','report'):
        p.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    {'capture-wait':capture,'analyze':analyze}[args.command](args)


if __name__=='__main__':
    main()
