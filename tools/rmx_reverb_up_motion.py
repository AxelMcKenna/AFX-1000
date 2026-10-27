#!/usr/bin/env python3
"""Characterize and screen factory Up motion/startup without changing the live Engine."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import controls
from tools.rmx_reverb_motion import recipe as down_recipe
from tools.rmx_reverb_up_model import model_checked
from tools.rmx_spiral_core import calibration

STAGES = ('button', 'steps', 'ramps', 'blocks', 'cold', 'holdout')
NAMES = dict(main='SceneVolume', amount='Sub1Volume', cutoff='Sub2Volume', enabled='ReverbUpButton')


def recipe(stage):
    if stage not in STAGES:
        raise ValueError('Unknown Up motion stage')
    if stage == 'holdout':
        rng=np.random.default_rng(0x75701027);program=rng.normal(0,.016,(456000,2));t=np.arange(len(program))/48000
        program+=.008*np.column_stack((np.sin(2*np.pi*(293*t+37*t*t)),np.cos(2*np.pi*1789*t)))
        gap=program.copy();gap[168000:240000]=0
        pulses=np.zeros_like(program);locations=[0,7,31,33,127,161,1021,4093,11897,12391,12527,24107,48109,96113,192137,288179]
        pulses[locations]=np.random.default_rng(0x75701028).uniform(-.024,.024,(len(locations),2))
        waves=dict(program=program,gap=gap,pulses=pulses)
        specs=[(64,128,37,1,'program',128,[(96019,'main',224),(120001,'main',64),(181043,'main',255),(181043,'amount',239),(181043,'cutoff',179)]),
            (224,207,211,1,'gap',63,[(17,'main',61),(11819,'amount',3),(12091,'main',231),(12091,'cutoff',5),(12739,'main',47),(96113,'main',242)]),
            (197,17,19,1,'pulses',31,[(31,'main',198),(11713,'main',196),(12403,'main',199),(12467,'main',197)]),
            (0,253,243,1,'program',32,[(17,'main',4),(95,'main',1),(503,'main',8),(11927,'main',3),(12619,'main',5),(24103,'main',131),(96013,'main',0),(192031,'main',224)]),
            (104,83,111,1,'program',8,[(12013,'main',105),(12631,'main',103),(48043,'main',106),(96047,'amount',247),(96047,'cutoff',229),(144019,'main',4)]),
            (255,239,77,0,'program',4096,[(5,'main',79),(17,'amount',3),(31,'cutoff',249),(67,'enabled',1),(11933,'main',248),(24117,'main',0),(96053,'main',255)]),
            (133,149,1,1,'program',15,[(3,'enabled',0),(29,'enabled',1),(63,'enabled',0),(139,'enabled',1),(12101,'main',242),(18121,'main',130)]),
            (41,31,249,1,'pulses',511,[(17,'cutoff',0),(63,'cutoff',5),(12019,'cutoff',255),(12051,'cutoff',241),(96139,'amount',223)]),
            (183,1,37,1,'program',17,[(31,'amount',255),(12001,'amount',0),(12673,'amount',239),(14519,'main',190),(96031,'amount',253),(144019,'amount',1)]),
            (231,247,211,1,'gap',1024,[(17,'main',5),(95,'main',248),(12043,'cutoff',0),(24121,'main',64),(24121,'amount',17),(96073,'main',224)]),
            (4,4,5,1,'pulses',33,[(31,'main',3),(91,'main',5),(193,'main',2),(12017,'main',4),(12469,'main',64),(96017,'amount',128)]),
            (128,128,179,0,'program',256,[(3,'enabled',1),(19,'enabled',0),(31,'enabled',1),(47,'enabled',0),(129,'enabled',1),(12103,'main',224),(96019,'main',0)]),
            (255,17,0,1,'program',47,[(96071,'main',197),(96139,'main',196),(96203,'main',198),(192137,'main',231)]),
            (197,255,5,1,'pulses',2048,[(17,'cutoff',249),(12113,'main',194),(12203,'main',201),(96023,'cutoff',0),(96101,'cutoff',255)]),
            (79,137,119,1,'program',9,[(17,'main',61),(11717,'main',197),(12043,'amount',239),(12239,'cutoff',224),(96073,'main',231),(192139,'main',104)]),
            (248,223,32,0,'program',255,[(7,'enabled',1),(37,'enabled',0),(103,'enabled',1),(12359,'main',104),(12789,'main',105),(48097,'main',3),(96101,'amount',0),(96101,'cutoff',255)])]
        cases=[]
        for i,(main,amount,cutoff,enabled,source,block,changes) in enumerate(specs):
            high=max([amount]+[v for _,k,v in changes if k=='amount'])
            cases.append(dict(name=f'up-motion-holdout-{i}',source=source,direction='up',main=main,amount=amount,cutoff=cutoff,enabled=enabled,block=block,tail=90 if high>=192 else 18,baseline=None,events=[dict(frame=f,control=k,value=v) for f,k,v in changes]))
        return waves,cases
    waves, originals = down_recipe('startup-v3-holdout' if stage == 'cold' else stage)
    cases = []
    for original in originals:
        c = original | dict(direction='up')
        c['name'] = c['name'].replace('down-', 'up-', 1)
        if stage == 'cold':
            c['name'] = c['name'].replace('startup-v3-holdout', 'cold-discovery')
        if c['baseline']:
            c['baseline'] = c['baseline'].replace('down-', 'up-')
        cases.append(c)
    return waves, cases


def parameters(case):
    return controls(case) | {'ReverbUpButton': case['enabled']}


def events(case):
    return [dict(frame=e['frame'], name=NAMES[e['control']], value=e['value'] if e['control'] == 'enabled' else e['value']/255)
            for e in case['events']]


def capture(args):
    model_checked(args); model_hash = sha256(args.model)
    prediction_path=getattr(args,'prediction',None);prediction=None
    if args.stage=='holdout':
        if prediction_path is None:raise ValueError('Fresh Up motion capture requires a frozen prediction')
        prediction=json.loads(prediction_path.read_text())
        if (any(prediction.get(k)!=v for k,v in prediction_payload().items()) or prediction['model_sha256']!=model_hash
                or prediction['calibration_sha256']!=sha256(args.calibration)
                or prediction['renderer_sha256']!=sha256(Path(prediction['renderer_path']))):raise ValueError('Frozen Up motion prediction differs')
    elif prediction_path is not None:raise ValueError('Predictions apply only to fresh Up holdout')
    recipe_files = [Path(__file__), Path('tools/rmx_reverb_motion.py'), Path('tools/rmx_reverb_characterize.py')]
    recipe_hashes = {str(p): sha256(p) for p in recipe_files}
    root = new_directory(args.session)
    if prediction_path is not None:(root/'predictions.json').write_bytes(prediction_path.read_bytes())
    inventory = json.loads(run([args.host, 'inventory', args.plugin]))
    if any(inventory[k] != v for k, v in IDENTITY.items()):
        raise ValueError('Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json', inventory)
    def setting(name, value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous original parameter: '+name)
        return {k: matches[0][k] for k in ('index', 'id', 'name')} | dict(value=value)
    waves, cases = recipe(args.stage)
    for name, x in waves.items():
        write_wav(root/(name+'.wav'), 48000, x.ravel())
    for c in cases:
        plan = dict(schema_version=1, kind='audio-plugin-capture-plan', role='reference', expected_plugin=IDENTITY,
            sample_rate=48000, bpm=120, tail_seconds=c['tail'], parameters=[setting(k, v) for k, v in parameters(c).items()],
            events=[setting(e['name'], e['value']) | dict(frame=e['frame'], type='parameter') for e in events(c)])
        save_json(root/(c['name']+'.json'), plan)
        run([args.host, 'render', args.plugin, root/(c['source']+'.wav'), root/(c['name']+'.json'), root/c['name'], c['block']])
        c['receipt_sha256'] = sha256(root/c['name']/'receipt.json'); print(c['name'], flush=True)
    if sha256(args.model) != model_hash or any(sha256(p) != recipe_hashes[str(p)] for p in recipe_files):
        raise ValueError('Discovery recipe/model changed during capture')
    if prediction and (any(prediction.get(k)!=v for k,v in prediction_payload().items())
            or prediction['renderer_sha256']!=sha256(Path(prediction['renderer_path']))):raise ValueError('Frozen motion candidate changed during capture')
    save_json(root/'matrix.json', dict(kind='rmx220-reverb-up-motion-discovery-captures', stage=args.stage, cases=cases,
        calibration_sha256=sha256(args.calibration), static_model_sha256=model_hash, capture_source_sha256=recipe_hashes,
        prediction_sha256=sha256(prediction_path) if prediction_path else None,
        role='Fresh original captures after frozen candidate prediction.' if prediction else 'Development/identification captures; not a prospective candidate holdout.'))


def checked(directory, case, expected):
    folder = directory/case['name']; receipt = json.loads((folder/'receipt.json').read_text())
    if (not receipt['complete'] or receipt['role'] != 'reference' or any(receipt['plugin'][k] != v for k, v in IDENTITY.items())):
        raise ValueError('Wrong original reference')
    for path, field in [(folder/'audio.wav', 'output_sha256'), (folder/'plan.json', 'plan_sha256'),
                        (Path(receipt['input_path']), 'input_sha256'), (folder/'state-before.bin', 'initial_state_sha256'),
                        (folder/'state-after.bin', 'final_state_sha256'), (folder/'parameter-log.json', 'parameter_log_sha256'),
                        (folder/'inventory-after.json', 'final_inventory_sha256')]:
        if sha256(path) != receipt[field]:
            raise ValueError('Modified capture file: '+str(path))
    plan = json.loads((folder/'plan.json').read_text())
    if ({p['name']: p['value'] for p in plan['parameters']} != parameters(case)
            or [{k: e[k] for k in ('frame', 'name', 'value')} for e in plan['events']] != events(case)
            or any(e['type'] != 'parameter' for e in plan['events']) or plan['sample_rate'] != 48000 or plan['bpm'] != 120
            or plan['tail_seconds'] != case['tail'] or receipt['maximum_block_size'] != case['block']):
        raise ValueError('Outside exact Up motion recipe')
    log = json.loads((folder/'parameter-log.json').read_text())['entries']
    requested = [p | dict(frame=-1) for p in plan['parameters']] + plan['events']
    if len(log) != len(requested):
        raise ValueError('Unexpected parameter log length')
    final = dict(parameters(case))
    for request, actual in zip(requested, log):
        if (any(actual[k] != request[k] for k in ('frame', 'name', 'index', 'id'))
                or np.float32(actual['requested_value']) != np.float32(request['value'])
                or abs(actual['immediate_readback']-float(np.float32(request['value']))) > 1e-14):
            raise ValueError('Immediate readback differs')
        final[request['name']] = request['value']
    inventory = {p['name']: p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
    if any(abs(inventory[k]-float(np.float32(v))) > 1e-14 for k, v in final.items()):
        raise ValueError('Final readback differs')
    rate, audio = float_wav(folder/'audio.wav'); input_rate, x = float_wav(Path(receipt['input_path']))
    if rate != 48000 or input_rate != rate or not np.array_equal(x, expected.astype(np.float32)) or len(audio) != len(x)+case['tail']*48000:
        raise ValueError('Motion sample/rate/extent differs')
    manifest = json.loads((directory/'matrix.json').read_text()); stored = next(c for c in manifest['cases'] if c['name'] == case['name'])
    if stored['receipt_sha256'] != sha256(folder/'receipt.json'):
        raise ValueError('Capture receipt changed')
    return receipt, audio.astype(float), x, dict(case=case['name'], receipt_sha256=sha256(folder/'receipt.json'),
        input_sha256=receipt['input_sha256'], output_sha256=receipt['output_sha256'], plan_sha256=receipt['plan_sha256'])


def source_hashes():
    paths = [Path(__file__), Path('tools/rmx_reverb_motion.py'), Path('tools/rmx_reverb_characterize.py'), Path('CMakeLists.txt'),
        *sorted(Path('research/audio/experiments').glob('*UpMotion*')), Path('research/audio/experiments/reverb_up_motion_probe.cpp'),
        Path('research/audio/experiments/ReverbUpControlCalibration.h'), Path('src/core/Wav.cpp'), Path('include/rmx/Wav.h'), Path('include/rmx/Dsp.h')]
    return {str(p): sha256(p) for p in paths}


def prediction_payload():
    waves,cases=recipe('holdout')
    return dict(kind='rmx220-reverb-up-motion-predictions',stage='holdout',cases=cases,source_sha256=source_hashes(),
        source_samples_sha256={name:hashlib.sha256(x.astype('<f4').tobytes()).hexdigest() for name,x in waves.items()})


def predict(args):
    model_checked(args)
    save_json(args.report,prediction_payload()|dict(model_path=str(args.model.resolve()),model_sha256=sha256(args.model),
        renderer_path=str(args.renderer.resolve()),renderer_sha256=sha256(args.renderer),calibration_sha256=sha256(args.calibration),
        expected='All 16 complete renders pass fixed 1% whole/wet/tail/event/startup windows, 1e-20 reference energy floor and silent absolute RMS1e-8, offsets32/32, no gain fit or wet alignment search.',
        scope='New source programs, pulses, cold toggles, wide/reversing/simultaneous controls, silent positions and callbacks8..4096; standalone factory Up/48k/120BPM only.'))


def compare(args):
    model_checked(args); root = new_directory(args.output); rows = []
    for stage, directory in args.session:
        if stage=='holdout':
            prediction=json.loads((directory/'predictions.json').read_text());manifest=json.loads((directory/'matrix.json').read_text())
            if (any(prediction.get(k)!=v for k,v in prediction_payload().items()) or manifest['prediction_sha256']!=sha256(directory/'predictions.json')
                    or prediction['model_sha256']!=sha256(args.model) or prediction['renderer_sha256']!=sha256(args.renderer)
                    or prediction['calibration_sha256']!=sha256(args.calibration)):raise ValueError('Fresh comparison prediction differs')
        waves, cases = recipe(stage)
        for c in cases:
            if args.case and c['name'] not in args.case:
                continue
            receipt, audio, x, provenance = checked(directory, c, waves[c['source']])
            prefix = stage+'-'+c['name']; schedule = root/(prefix+'.tsv'); output = root/(prefix+'.wav'); dry_path = root/(prefix+'-dry.wav')
            schedule.write_text('RMX_REVERB_MOTION 1\n'+f'initial {c["main"]} {c["amount"]} {c["cutoff"]} {c["enabled"]}\n'
                +f'tail {c["tail"]}\nblock {c["block"]}\n'+''.join(f'event {e["frame"]} {e["control"]} {e["value"]}\n' for e in c['events']))
            run([args.renderer, receipt['input_path'], output, schedule, dry_path])
            rate, b = float_wav(output); dry_rate, dry = float_wav(dry_path)
            if rate != 48000 or dry_rate != rate or len(b) != len(audio) or len(dry) != len(audio):
                raise ValueError('Candidate extent/rate differs')
            a = audio[32:]; b = b[32:].astype(float); dry = dry[32:].astype(float); wa, wb = a-dry, b-dry
            row = provenance | dict(stage=stage,role='fresh_prediction_bound' if stage=='holdout' else 'development_regression', whole=screen(a, b), wet=screen(wa, wb), post_input_tail=screen(a[len(x):], b[len(x):]),
                candidate_sha256=sha256(output), dry_trace_sha256=sha256(dry_path), schedule_sha256=sha256(schedule), event_windows=[], startup_windows=[])
            for at in sorted({e['frame'] for e in c['events']}):
                start, end = max(0, at-64), min(len(a), at+4096)
                row['event_windows'].append(dict(frame=at, whole=screen(a[start:end], b[start:end]), wet=screen(wa[start:end], wb[start:end])))
            anchors = {0, 12416} if c['enabled'] else set()
            anchors.update((e['frame']//32+1)*32+12416 for e in c['events'] if e['control'] == 'enabled' and e['value'])
            for at in sorted(anchors):
                start, end = max(0, at-64), min(len(a), at+4096)
                if end > start:
                    row['startup_windows'].append(dict(frame=at, whole=screen(a[start:end], b[start:end]), wet=screen(wa[start:end], wb[start:end])))
            row['passed'] = (all(row[k]['passed'] for k in ('whole', 'wet', 'post_input_tail'))
                and all(w[k]['passed'] for group in ('event_windows', 'startup_windows') for w in row[group] for k in ('whole', 'wet')))
            rows.append(row); print('PASS' if row['passed'] else 'FAIL', stage, c['name'], flush=True)
    if not rows:
        raise ValueError('No comparison cases')
    save_json(root/'comparison.json', dict(kind='rmx220-reverb-up-motion-development-comparison', passed=all(c['passed'] for c in rows),
        full_reverb_match=False, physical_hardware=False, model_sha256=sha256(args.model), calibration_sha256=sha256(args.calibration),
        renderer_sha256=sha256(args.renderer), source_sha256=source_hashes(), cases=rows,
        acceptance=dict(relative_rms_error_limit=.01, reference_channel_energy_floor=1e-20, silent_channel_absolute_rms_limit=1e-8,
            reference_offset_frames=32, candidate_offset_frames=32, gain_fit=False, wet_alignment_search=False),
        scope='Development comparison of factory Up at 48 kHz/120 BPM; original/candidate dry subtraction is diagnostic and is not an independently captured wet stem. No live Engine or hardware claim.'))
    return 0 if all(c['passed'] for c in rows) else 1


def characterize(args):
    calibration(args.calibration); records = {}; findings = []
    for stage, directory in args.session:
        waves, cases = recipe(stage)
        for c in cases:
            records[stage, c['name']] = checked(directory, c, waves[c['source']]), c
    for (stage, name), ((receipt, audio, x, provenance), c) in records.items():
        row = provenance | dict(stage=stage, events=c['events'], block=c['block'], readbacks_verified=True)
        if c['baseline']:
            other, baseline = c['baseline'].split('/', 1) if '/' in c['baseline'] else (stage, c['baseline'])
            (_, a, _, baseprov), _ = records[other, baseline]; length = min(len(a), len(audio))
            changed = np.flatnonzero(np.any(a[:length] != audio[:length], axis=1))
            row |= dict(baseline=baseprov, overlap_frames=length, bit_exact=not bool(len(changed)),
                first_different_output_frame=int(changed[0]) if len(changed) else None,
                first_different_after_bypass_offset=int(changed[0])-32 if len(changed) else None,
                post_input_tail_vs_baseline=screen(a[len(x):length], audio[len(x):length]))
        findings.append(row)
    save_json(args.report, dict(kind='rmx220-reverb-up-motion-original-characterization', passed_capture_verification=True,
        cases=findings, calibration_sha256=sha256(args.calibration), script_sha256=sha256(Path(__file__)),
        scope='Original-versus-original timing/state diagnostics only; no candidate match claim.'))
    print('Verified', len(findings), 'original motion recipes/readbacks; recorded baseline differences')


def main():
    p = argparse.ArgumentParser(description=__doc__); commands = p.add_subparsers(dest='command', required=True)
    for command in ('capture', 'compare', 'characterize','predict'):
        q = commands.add_parser(command); q.add_argument('--calibration', type=Path, required=True)
        if command in ('capture', 'compare','predict'):
            q.add_argument('--model', type=Path, required=True)
        if command=='predict':
            q.add_argument('--renderer',type=Path,required=True);q.add_argument('--report',type=Path,required=True)
        elif command == 'capture':
            q.add_argument('--stage', choices=STAGES, required=True)
            q.add_argument('--prediction',type=Path)
            for name in ('host', 'plugin', 'session'):
                q.add_argument('--'+name, type=Path, required=True)
        else:
            q.add_argument('--session', nargs=2, action='append', required=True)
            if command == 'compare':
                q.add_argument('--renderer', type=Path, required=True); q.add_argument('--output', type=Path, required=True); q.add_argument('--case', action='append')
            else:
                q.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    if args.command in ('compare','characterize'):
        args.session = [(s, Path(d)) for s, d in args.session]
    result = globals()[args.command](args)
    if result is not None:
        raise SystemExit(result)


if __name__ == '__main__':
    main()
