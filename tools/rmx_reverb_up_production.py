#!/usr/bin/env python3
"""Freeze, capture and verify the bounded factory Up processor at stereo48k/120BPM."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked as checked_static
from tools.rmx_reverb_up_model import model_checked, session_recipe
from tools.rmx_reverb_up_model_audit import auxiliary
from tools.rmx_reverb_up_motion import checked, events, parameters, recipe as motion_recipe
from tools.rmx_reverb_up_motion_audit import ACCEPTANCE, schedule


def require(value, message):
    if not value:
        raise ValueError(message)


def source_hashes():
    names = [
        'tools/rmx_reverb_up_production.py', 'tools/reverb_up_probe.cpp',
        'src/core/ReverbUp.cpp', 'include/rmx/CalibratedReverbUp.h',
        'include/rmx/ReverbUpMotionCalibration.h', 'include/rmx/ReverbUpControlCalibration.h',
        'src/core/Wav.cpp', 'include/rmx/Wav.h', 'include/rmx/Dsp.h', 'CMakeLists.txt',
        'tools/rmx_reverb_up_motion.py', 'tools/rmx_reverb_characterize.py',
        'tools/rmx_reverb_up_model.py', 'tools/rmx_reverb_up_model_audit.py',
        'tools/rmx_reverb_up_motion_audit.py', 'tools/rmx_reverb_motion.py',
        'tools/rmx_filter_match.py', 'tools/reference_audio.py',
    ]
    return {name: sha256(Path(name)) for name in names}


def recipe():
    rng = np.random.default_rng(0x75701030)
    t = np.arange(432000)/48000
    program = rng.normal(0, .014, (len(t), 2))
    program += .009*np.column_stack((np.sin(2*np.pi*(317*t+47*t*t)), np.cos(2*np.pi*1877*t)))
    gap = program.copy(); gap[144000:228000] = 0
    pulses = np.zeros_like(program)
    locations = [0, 5, 23, 41, 157, 191, 1039, 4079, 11923, 12431, 12583, 24133, 48157, 96173, 192223, 288239, 384251]
    pulses[locations] = np.random.default_rng(0x75701031).uniform(-.027, .027, (len(locations), 2))
    specs = [
        (0, 255, 3, 1, 'program', 4096, [(13,'main',2),(89,'main',3),(193,'main',4),(11959,'main',7),(96191,'main',0),(192239,'main',255)]),
        (255, 2, 1, 0, 'program', 2048, [(11,'enabled',1),(43,'enabled',0),(151,'enabled',1),(12149,'main',5),(12521,'main',249),(48179,'amount',253),(96199,'cutoff',247)]),
        (198, 253, 250, 1, 'pulses', 1024, [(29,'main',196),(12109,'main',201),(12509,'main',197),(48187,'main',194),(96211,'main',205)]),
        (104, 137, 71, 1, 'program', 511, [(19,'main',103),(11969,'main',107),(12601,'main',104),(48193,'amount',1),(96223,'cutoff',251),(192253,'main',241)]),
        (37, 17, 251, 1, 'pulses', 8, [(23,'cutoff',4),(157,'amount',254),(12043,'main',3),(12487,'main',128),(48209,'cutoff',0),(96227,'main',255)]),
        (189, 251, 5, 1, 'gap', 63, [(37,'main',1),(11981,'main',253),(12541,'main',4),(48221,'amount',2),(96233,'amount',255),(192263,'main',239)]),
        (131, 255, 128, 0, 'program', 33, [(7,'enabled',1),(31,'enabled',0),(79,'enabled',1),(167,'enabled',0),(227,'enabled',1),(12049,'main',244),(12607,'amount',3),(96247,'cutoff',255)]),
        (247, 83, 32, 1, 'program', 15, [(17,'main',4),(17,'amount',249),(17,'cutoff',245),(12119,'main',0),(12569,'main',231),(48233,'amount',1),(96257,'main',104),(192277,'cutoff',2)]),
    ]
    cases = []
    for i, (main, amount, cutoff, enabled, source, block, changes) in enumerate(specs):
        high = max([amount]+[v for _, k, v in changes if k == 'amount'])
        cases.append(dict(name=f'up-production-holdout-{i}', source=source, direction='up', main=main,
                          amount=amount, cutoff=cutoff, enabled=enabled, block=block,
                          tail=90 if high >= 192 else 18, baseline=None,
                          events=[dict(frame=f, control=k, value=v) for f, k, v in changes]))
    return dict(program=program, gap=gap, pulses=pulses), cases


def payload(args):
    model_checked(args)
    waves, cases = recipe()
    return dict(kind='rmx220-reverb-up-production-prediction', cases=cases, source_sha256=source_hashes(),
                source_samples_sha256={name: hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for name, x in waves.items()},
                model_sha256=sha256(args.model), calibration_sha256=sha256(args.calibration),
                renderer_path=str(args.renderer.resolve()), renderer_sha256=sha256(args.renderer), acceptance=ACCEPTANCE)


def predict(args):
    save_json(args.report, payload(args) | dict(expected='All eight complete renders pass the fixed per-channel screens.',
              scope='Factory Up, integer controls, stereo48k/120BPM. Bounded processor, not live Engine or hardware.'))
    return 0


def frozen(args):
    prediction = json.loads(args.prediction.read_text())
    require(all(prediction.get(k) == v for k, v in payload(args).items()), 'Frozen production prediction differs')
    return prediction


def capture(args):
    frozen(args); root = new_directory(args.session)
    (root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    require(all(inventory[k] == v for k, v in IDENTITY.items()), 'Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json', inventory)
    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        require(len(matches) == 1, 'Ambiguous original parameter: '+name)
        return {k: matches[0][k] for k in ('index','id','name')} | dict(value=value)
    waves, cases = recipe()
    for name, x in waves.items():
        write_wav(root/(name+'.wav'), 48000, x.ravel())
    for c in cases:
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference', expected_plugin=IDENTITY,
                    sample_rate=48000, bpm=120, tail_seconds=c['tail'],
                    parameters=[setting(k, v) for k, v in parameters(c).items()],
                    events=[setting(e['name'], e['value']) | dict(frame=e['frame'], type='parameter') for e in events(c)])
        save_json(root/(c['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/(c['source']+'.wav'), root/(c['name']+'.json'), root/c['name'], c['block']])
        c['receipt_sha256'] = sha256(root/c['name']/'receipt.json')
        print('Captured', c['name'], flush=True)
    frozen(args)
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-up-production-captures', cases=cases,
              prediction_sha256=sha256(args.prediction), role='Fresh recordings after a frozen bounded candidate.'))
    return 0


def compare(args):
    frozen(args); root = new_directory(args.output); waves, cases = recipe(); rows = []
    require(sha256(args.session/'predictions.json') == sha256(args.prediction), 'Capture prediction copy differs')
    manifest = json.loads((args.session/'matrix.json').read_text())
    require(manifest['prediction_sha256'] == sha256(args.prediction), 'Capture prediction binding differs')
    for c in cases:
        receipt, raw_a, x, provenance = checked(args.session, c, waves[c['source']])
        plan = root/(c['name']+'.tsv'); output = root/(c['name']+'.wav'); dry_path = root/(c['name']+'-dry.wav')
        plan.write_text(schedule(c)); run([args.renderer, receipt['input_path'], output, plan, dry_path])
        rate, raw_b = float_wav(output); dry_rate, raw_d = float_wav(dry_path)
        require(rate == dry_rate == 48000 and raw_b.shape == raw_a.shape == raw_d.shape, 'Candidate extent/rate differs')
        a, b, dry = raw_a[32:], raw_b[32:].astype(float), raw_d[32:].astype(float)
        wa, wb = a-dry, b-dry
        row = provenance | dict(role='fresh_prediction_bound', candidate_sha256=sha256(output),
                                dry_trace_sha256=sha256(dry_path), schedule_sha256=sha256(plan),
                                whole=screen(a,b), wet=screen(wa,wb), post_input_tail=screen(a[len(x):],b[len(x):]),
                                event_windows=[], startup_windows=[])
        anchors = {0, 12416} if c['enabled'] else set()
        anchors.update((e['frame']//32+1)*32+12416 for e in c['events'] if e['control']=='enabled' and e['value'])
        for key, positions in [('event_windows', sorted({e['frame'] for e in c['events']})), ('startup_windows', sorted(anchors))]:
            for at in positions:
                left, right = max(0,at-64), min(len(a),at+4096)
                if right > left:
                    row[key].append(dict(frame=at, whole=screen(a[left:right],b[left:right]), wet=screen(wa[left:right],wb[left:right])))
        row['passed'] = all(row[k]['passed'] for k in ('whole','wet','post_input_tail')) and all(
            w[k]['passed'] for group in ('event_windows','startup_windows') for w in row[group] for k in ('whole','wet'))
        rows.append(row); print('PASS' if row['passed'] else 'FAIL', c['name'], flush=True)
    frozen(args)
    save_json(root/'comparison.json', payload(args) | dict(kind='rmx220-reverb-up-production-fresh-comparison',
              passed=all(r['passed'] for r in rows), cases=rows, prediction_sha256=sha256(args.prediction),
              full_reverb_match=False, physical_hardware=False))
    return 0 if all(r['passed'] for r in rows) else 1


def regress(args):
    model_checked(args); binding = source_hashes(); binary = sha256(args.renderer); root = new_directory(args.output)
    audit = json.loads(args.audit.read_text()); old_motion = json.loads(args.motion_comparison.read_text()); old_static = json.loads(args.static_comparison.read_text())
    require(audit['passed'] and audit['provenance_verified'] and audit['waveform_acceptance_passed'], 'Previous audit not accepted')
    require(audit['comparison_sha256'] == sha256(args.motion_comparison) and audit['static_comparison_sha256'] == sha256(args.static_comparison), 'Previous report/audit binding differs')
    require(all(d['acceptance'] == ACCEPTANCE and d['passed'] and d['model_sha256'] == sha256(args.model)
                and d['calibration_sha256'] == sha256(args.calibration) for d in (old_motion, old_static)), 'Previous gates/model/calibration differ')
    old = {(r['stage'],r['case']): r for d in (old_motion,old_static) for r in d['cases']}
    verified = {(r['stage'],r['case']): r for r in audit['captures']}
    require(len(old_motion['cases']) == 101 and len(old_static['cases']) == 1204 and len(old) == len(verified) == 1305, 'Wrong previous coverage')
    rows = []; seen = set(); hosts = set(); bundles = {}
    for dynamic, sessions in ((True,args.motion_session),(False,args.static_session)):
        for stage, directory in sessions:
            waves, cases = motion_recipe(stage) if dynamic else session_recipe(stage)
            for c in cases:
                key = stage,c['name']; require(key not in seen, 'Duplicate regression'); seen.add(key)
                if dynamic:
                    receipt, _, _, provenance = checked(directory,c,waves[c['source']])
                else:
                    receipt, _, _, provenance = checked_static(directory,c,waves[c['source']]); auxiliary(directory/c['name'],receipt)
                require(all(old[key][k] == v and verified[key][k] == v for k,v in provenance.items()), 'Previous capture binding differs')
                hosts.add(receipt['host_sha256']); bundles[receipt['plugin']['bundle']] = receipt['plugin']['binary_files']
                plan = root/(stage+'-'+c['name']+'.tsv'); output = plan.with_suffix('.wav'); dry_path = root/(plan.stem+'-dry.wav')
                plan.write_text(schedule(c if dynamic else c | dict(enabled=1,block=128,events=[])))
                require(sha256(plan) == old[key]['schedule_sha256'], 'Previous schedule differs')
                run([args.renderer,receipt['input_path'],output,plan,dry_path])
                audio_equal = sha256(output) == old[key]['candidate_sha256']; dry_equal = sha256(dry_path) == old[key]['dry_trace_sha256']
                rows.append(provenance | dict(stage=stage, role='prior_regression', candidate_sha256=sha256(output),
                            dry_trace_sha256=sha256(dry_path), schedule_sha256=sha256(plan),
                            audio_byte_identical=audio_equal, dry_byte_identical=dry_equal, passed=audio_equal and dry_equal))
                print('PASS' if audio_equal and dry_equal else 'FAIL', stage, c['name'], flush=True)
    require(seen == set(old) and hosts == {audit['reference_host_sha256']}, 'Coverage/reference host differs')
    for directory,members in bundles.items():
        require(members == audit['original_binary_files'], 'Original bundle identity differs')
        for member in members:
            p = Path(directory)/member['path']; require(sha256(p) == member['sha256'] and p.stat().st_size == member['bytes'], 'Installed original changed')
    require(source_hashes() == binding and sha256(args.renderer) == binary, 'Candidate changed during regressions')
    save_json(root/'comparison.json', dict(kind='rmx220-reverb-up-production-regressions',passed=all(r['passed'] for r in rows),
              source_sha256=binding, renderer_sha256=binary, model_sha256=sha256(args.model), calibration_sha256=sha256(args.calibration),
              previous_audit_sha256=sha256(args.audit), previous_motion_comparison_sha256=sha256(args.motion_comparison),
              previous_static_comparison_sha256=sha256(args.static_comparison), acceptance=ACCEPTANCE, cases=rows,
              scope='1305 prior cases. Exact output and diagnostic dry WAV identity carries every accepted waveform/window result; no new original captures.',
              full_reverb_match=False, physical_hardware=False))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    for command in ('predict','capture','compare','regress'):
        q = commands.add_parser(command)
        for name in ('model','calibration','renderer'):
            q.add_argument('--'+name, type=Path, required=True)
        if command == 'predict': q.add_argument('--report', type=Path, required=True)
        if command in ('capture','compare'): q.add_argument('--prediction', type=Path, required=True); q.add_argument('--session', type=Path, required=True)
        if command == 'capture':
            for name in ('host','plugin'): q.add_argument('--'+name, type=Path, required=True)
        if command in ('compare','regress'): q.add_argument('--output', type=Path, required=True)
        if command == 'regress':
            for name in ('audit','motion-comparison','static-comparison'): q.add_argument('--'+name,type=Path,required=True)
            for name in ('motion-session','static-session'): q.add_argument('--'+name,nargs=2,action='append',required=True)
    args = parser.parse_args()
    if args.command == 'regress':
        args.motion_session = [(s,Path(d)) for s,d in args.motion_session]; args.static_session = [(s,Path(d)) for s,d in args.static_session]
    raise SystemExit(globals()[args.command](args))


if __name__ == '__main__':
    main()
