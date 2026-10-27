#!/usr/bin/env python3
"""Freeze, capture and verify the live factory Up Engine at stereo48k/120BPM."""
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
from tools.rmx_reverb_up_production import recipe as production_recipe
from tools.rmx_reverb_up_motion_audit import ACCEPTANCE, schedule


def require(value, message):
    if not value:
        raise ValueError(message)


def source_hashes():
    repo = Path(__file__).resolve().parents[1]
    names = [
        'tools/rmx_reverb_up_engine.py', 'tools/reverb_up_probe.cpp', 'CMakeLists.txt',
        'tools/rmx_reverb_up_production.py', 'tools/rmx_reverb_up_motion.py',
        'tools/rmx_reverb_characterize.py', 'tools/rmx_reverb_up_model.py',
        'tools/rmx_reverb_up_model_audit.py', 'tools/rmx_reverb_up_motion_audit.py',
        'tools/rmx_reverb_motion.py', 'tools/rmx_filter_match.py', 'tools/reference_audio.py',
        'firmware/daisy/Makefile', 'hardware/firmware/full_engine/Makefile', 'tools/check_firmware.py',
    ]
    names += [str(p.relative_to(repo)) for p in sorted((repo/'include/rmx').glob('*.h'))]
    names += [str(p.relative_to(repo)) for p in sorted((repo/'src/core').glob('*.cpp'))]
    return {name: sha256(Path(name)) for name in names}



def recipe():
    rng = np.random.default_rng(0x75701032)
    t = np.arange(480000)/48000
    program = rng.normal(0, .014, (len(t), 2))
    program += .009*np.column_stack((np.sin(2*np.pi*(347*t+53*t*t)), np.cos(2*np.pi*2063*t)))
    gap = program.copy(); gap[168000:252000] = 0
    pulses = np.zeros_like(program)
    locations = [0, 13, 19, 53, 149, 211, 1049, 4057, 11939, 12451, 12611, 24151, 48193, 96221, 192277, 288307, 384311, 432341]
    pulses[locations] = np.random.default_rng(0x75701033).uniform(-.027, .027, (len(locations), 2))
    specs = [
        (2, 249, 1, 1, 'program', 8, [(11,'main',0),(107,'main',4),(241,'main',9),(12011,'main',3),(96263,'main',1),(192313,'main',251)]),
        (253, 3, 4, 0, 'program', 17, [(19,'enabled',1),(59,'enabled',0),(181,'enabled',1),(12097,'main',7),(12619,'main',247),(48257,'amount',251),(96269,'cutoff',249)]),
        (196, 251, 248, 1, 'pulses', 31, [(41,'main',199),(12071,'main',194),(12647,'main',198),(48263,'main',203),(96281,'main',195)]),
        (105, 139, 73, 1, 'program', 128, [(31,'main',104),(12073,'main',109),(12659,'main',101),(48281,'amount',2),(96289,'cutoff',253),(192319,'main',239)]),
        (39, 19, 249, 1, 'pulses', 511, [(37,'cutoff',3),(179,'amount',253),(12077,'main',2),(12671,'main',131),(48299,'cutoff',1),(96293,'main',254)]),
        (191, 253, 4, 1, 'gap', 1024, [(53,'main',3),(12083,'main',251),(12673,'main',5),(48311,'amount',1),(96307,'amount',254),(192323,'main',243)]),
        (133, 254, 130, 0, 'program', 2048, [(13,'enabled',1),(47,'enabled',0),(97,'enabled',1),(193,'enabled',0),(257,'enabled',1),(12089,'main',241),(12689,'amount',4),(96323,'cutoff',253)]),
        (245, 81, 34, 1, 'program', 4096, [(29,'main',5),(29,'amount',247),(29,'cutoff',243),(12091,'main',1),(12703,'main',233),(48313,'amount',2),(96329,'main',105),(192347,'cutoff',3)]),
    ]
    cases = []
    for i, (main, amount, cutoff, enabled, source, block, changes) in enumerate(specs):
        high = max([amount]+[v for _, k, v in changes if k == 'amount'])
        cases.append(dict(name=f'up-engine-holdout-{i}', source=source, direction='up', main=main,
                          amount=amount, cutoff=cutoff, enabled=enabled, block=block,
                          tail=90 if high >= 192 else 18, baseline=None,
                          events=[dict(frame=f, control=k, value=v) for f, k, v in changes]))
    return dict(program=program, gap=gap, pulses=pulses), cases


def payload(args):
    model_checked(args)
    waves, cases = recipe()
    return dict(kind='rmx220-reverb-up-engine-prediction', cases=cases, source_sha256=source_hashes(),
                source_samples_sha256={name: hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for name, x in waves.items()},
                model_sha256=sha256(args.model), calibration_sha256=sha256(args.calibration),
                renderer_path=str(args.renderer.resolve()), renderer_sha256=sha256(args.renderer), acceptance=ACCEPTANCE)


def predict(args):
    save_json(args.report, payload(args) | dict(expected='All eight complete renders pass the fixed per-channel screens.',
              scope='Factory Up, integer controls, stereo48k/120BPM. Complete Engine; no MCU deadline, combined-effect or hardware claim.'))
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
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-up-engine-captures', cases=cases,
              prediction_sha256=sha256(args.prediction), role='Fresh recordings after a frozen live Engine candidate.'))
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
    save_json(root/'comparison.json', payload(args) | dict(kind='rmx220-reverb-up-engine-fresh-comparison',
              passed=all(r['passed'] for r in rows), cases=rows, prediction_sha256=sha256(args.prediction),
              full_reverb_match=False, physical_hardware=False))
    return 0 if all(r['passed'] for r in rows) else 1


def regress(args):
    model_checked(args); binding = source_hashes(); binary = sha256(args.renderer); root = new_directory(args.output)
    audit = json.loads(args.previous_audit.read_text())
    prior = json.loads(args.previous_regressions.read_text()); fresh = json.loads(args.previous_fresh.read_text())
    require(audit['passed'] and audit['regressions_sha256'] == sha256(args.previous_regressions)
            and audit['comparison_sha256'] == sha256(args.previous_fresh), 'Previous production audit binding differs')
    require(all(d['passed'] and d['acceptance'] == ACCEPTANCE and d['model_sha256'] == sha256(args.model)
                and d['calibration_sha256'] == sha256(args.calibration) for d in (prior,fresh)), 'Previous acceptance/model differs')
    old = {(r.get('stage','production'),r['case']):r for report in (prior,fresh) for r in report['cases']}
    require(len(old) == 1313, 'Wrong previous coverage')
    rows = []; seen = set(); bundles = {}; hosts = set()
    for stage,directory in args.session:
        dynamic = stage in ('button','steps','ramps','blocks','cold','holdout','holdout-v2','production')
        waves,cases = production_recipe() if stage == 'production' else motion_recipe(stage) if dynamic else session_recipe(stage)
        for c in cases:
            key = stage,c['name']; require(key not in seen,'Duplicate regression'); seen.add(key)
            if dynamic:
                receipt,raw_a,x,provenance = checked(directory,c,waves[c['source']]); a = raw_a[32:]
            else:
                receipt,a,x,provenance = checked_static(directory,c,waves[c['source']]); auxiliary(directory/c['name'],receipt)
            require(all(old[key][k] == v for k,v in provenance.items()), 'Previous capture binding differs')
            hosts.add(receipt['host_sha256']); bundles[receipt['plugin']['bundle']] = receipt['plugin']['binary_files']
            prefix = stage+'-'+c['name']; plan = root/(prefix+'.tsv'); output = root/(prefix+'.wav'); dry_path = root/(prefix+'-dry.wav')
            plan.write_text(schedule(c if dynamic else c | dict(enabled=1,block=128,events=[])))
            require(sha256(plan) == old[key]['schedule_sha256'], 'Previous schedule differs')
            run([args.renderer,receipt['input_path'],output,plan,dry_path])
            rate,raw_b = float_wav(output); dry_rate,raw_d = float_wav(dry_path)
            require(rate == dry_rate == 48000 and len(raw_b) == len(a)+32 and raw_b.shape == raw_d.shape, 'Candidate extent/rate differs')
            b,d = raw_b[32:].astype(float),raw_d[32:].astype(float); wa,wb = a-d,b-d
            row = provenance | dict(stage=stage,role='prior_regression',candidate_sha256=sha256(output),
                    dry_trace_sha256=sha256(dry_path),schedule_sha256=sha256(plan),whole=screen(a,b),wet=screen(wa,wb),
                    post_input_tail=screen(a[len(x):],b[len(x):]),event_windows=[],startup_windows=[])
            for name,positions in ([('event_windows',sorted({e['frame'] for e in c['events']})),
                    ('startup_windows',sorted(({0,12416} if c['enabled'] else set()) |
                        {(e['frame']//32+1)*32+12416 for e in c['events'] if e['control']=='enabled' and e['value']}))] if dynamic else []):
                for at in positions:
                    left,right = max(0,at-64),min(len(a),at+4096)
                    if right > left: row[name].append(dict(frame=at,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
            old_prefix = c['name'] if stage == 'production' else prefix
            parent = args.previous_fresh.parent if stage == 'production' else args.previous_regressions.parent
            old_audio = parent/(old_prefix+'.wav'); old_dry = parent/(old_prefix+'-dry.wav')
            require(sha256(old_audio) == old[key]['candidate_sha256'] and sha256(old_dry) == old[key]['dry_trace_sha256'], 'Previous WAV changed')
            row['audio_byte_identical'] = row['candidate_sha256'] == old[key]['candidate_sha256']
            row['audio_sample_values_identical'] = bool(np.array_equal(raw_b,float_wav(old_audio)[1]))
            row['dry_byte_identical'] = row['dry_trace_sha256'] == old[key]['dry_trace_sha256']
            row['passed'] = row['audio_sample_values_identical'] and row['dry_byte_identical'] and all(
                row[k]['passed'] for k in ('whole','wet','post_input_tail')) and all(
                w[k]['passed'] for group in ('event_windows','startup_windows') for w in row[group] for k in ('whole','wet'))
            rows.append(row); print('PASS' if row['passed'] else 'FAIL',stage,c['name'],flush=True)
    require(seen == set(old) and len(hosts) == 1, 'Coverage/reference host differs')
    for directory,members in bundles.items():
        for member in members:
            p = Path(directory)/member['path']; require(sha256(p) == member['sha256'] and p.stat().st_size == member['bytes'], 'Installed original changed')
    require(source_hashes() == binding and sha256(args.renderer) == binary, 'Candidate changed during regressions')
    save_json(root/'comparison.json',dict(kind='rmx220-reverb-up-engine-regressions',passed=all(r['passed'] for r in rows),
              source_sha256=binding,renderer_sha256=binary,model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),
              previous_audit_sha256=sha256(args.previous_audit),previous_regressions_sha256=sha256(args.previous_regressions),
              previous_fresh_sha256=sha256(args.previous_fresh),acceptance=ACCEPTANCE,cases=rows,
              full_reverb_match=False,physical_hardware=False,
              scope='1313 previous original captures, independent Engine waveform/window screens and prior sample-value/dry parity; not new original recordings.'))
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
            for name in ('previous-audit','previous-regressions','previous-fresh'): q.add_argument('--'+name,type=Path,required=True)
            q.add_argument('--session',nargs=2,action='append',required=True)
    args = parser.parse_args()
    if args.command == 'regress':
        args.session = [(s,Path(d)) for s,d in args.session]
    raise SystemExit(globals()[args.command](args))


if __name__ == '__main__':
    main()
