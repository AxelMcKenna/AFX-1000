#!/usr/bin/env python3
"""Audit bounded Up waveform transfer, fresh recordings, guards and instrumented renders."""
import argparse
import copy
import json
from pathlib import Path
import shlex

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_up_motion import checked
from tools.rmx_reverb_up_motion_audit import ACCEPTANCE, schedule
from tools.rmx_reverb_up_production import capture, frozen, payload, recipe, require, source_hashes


def instrumented(args):
    repo = Path(__file__).resolve().parents[1]; build = args.sanitized_build.resolve()
    manifest = build/'compile_commands.json'; entries = json.loads(manifest.read_text()); records = {}; newest = 0
    require(args.sanitized.resolve() == build/'rmx_reverb_up_production_probe', 'Unexpected sanitizer renderer')
    for name in ('src/core/ReverbUp.cpp','src/core/Wav.cpp','tools/reverb_up_probe.cpp','tests/reverb_up_tests.cpp'):
        matches = [e for e in entries if Path(e['file']).resolve() == repo/name]
        require(len(matches) == 1, 'Missing/ambiguous sanitizer recipe')
        entry = matches[0]; command = entry.get('arguments') or shlex.split(entry['command'])
        flags = {v for item in command if item.startswith('-fsanitize=') for v in item.split('=',1)[1].split(',')}
        require({'address','undefined'} <= flags and '-fno-omit-frame-pointer' in command, 'Incomplete sanitizer flags')
        dependencies = [repo/name,repo/'include/rmx/Dsp.h',repo/'include/rmx/Wav.h']
        if name != 'src/core/Wav.cpp':
            dependencies += [repo/'include/rmx'/s for s in ('CalibratedReverbUp.h','ReverbUpMotionCalibration.h','ReverbUpControlCalibration.h')]
        obj = Path(entry['directory'])/command[command.index('-o')+1]
        require(obj.stat().st_mtime_ns >= max(p.stat().st_mtime_ns for p in dependencies), 'Stale sanitizer object')
        records[name] = dict(command=command,object_sha256=sha256(obj),dependency_sha256={str(p.relative_to(repo)):sha256(p) for p in dependencies})
        if name != 'tests/reverb_up_tests.cpp': newest = max(newest,obj.stat().st_mtime_ns)
    require(args.sanitized.stat().st_mtime_ns >= newest, 'Stale sanitizer renderer')
    return dict(renderer_sha256=sha256(args.sanitized),compile_commands_sha256=sha256(manifest),sources=records)


def audit(args):
    frozen(args); root = new_directory(args.output); binding = source_hashes()
    fresh = json.loads(args.comparison.read_text()); regressions = json.loads(args.regressions.read_text())
    previous_audit = json.loads(args.previous_audit.read_text())
    previous_motion = json.loads(args.motion_comparison.read_text()); previous_static = json.loads(args.static_comparison.read_text())
    require(previous_audit['passed'] and sha256(args.previous_audit) == regressions['previous_audit_sha256'], 'Previous audit binding differs')
    for path, field in ((args.motion_comparison,'previous_motion_comparison_sha256'),(args.static_comparison,'previous_static_comparison_sha256')):
        require(sha256(path) == regressions[field], 'Previous report binding differs')
    require(previous_audit['comparison_sha256'] == sha256(args.motion_comparison) and previous_audit['static_comparison_sha256'] == sha256(args.static_comparison), 'Previous accepted evidence differs')
    for report in (fresh,regressions):
        require(report['source_sha256'] == binding and report['renderer_sha256'] == sha256(args.renderer)
                and report['model_sha256'] == sha256(args.model) and report['calibration_sha256'] == sha256(args.calibration)
                and report['acceptance'] == ACCEPTANCE, 'Current comparison binding differs')
    require(fresh['prediction_sha256'] == sha256(args.prediction) == sha256(args.session/'predictions.json'), 'Fresh prediction copy differs')
    old = {(r['stage'],r['case']):r for report in (previous_motion,previous_static) for r in report['cases']}
    seen = set(); regrows = []
    for row in regressions['cases']:
        key = row['stage'],row['case']; require(key not in seen, 'Duplicate regression'); seen.add(key); prior = old[key]
        prefix = '-'.join(key)
        output = args.regressions.parent/(prefix+'.wav'); dry = args.regressions.parent/(prefix+'-dry.wav'); plan = args.regressions.parent/(prefix+'.tsv')
        require(prior['passed'] and all(prior[k] == row[k] for k in ('receipt_sha256','input_sha256','output_sha256','plan_sha256')), 'Regression provenance differs')
        require(sha256(plan) == row['schedule_sha256'] == prior['schedule_sha256'], 'Regression schedule changed')
        equal = sha256(output) == row['candidate_sha256'] == prior['candidate_sha256'] and sha256(dry) == row['dry_trace_sha256'] == prior['dry_trace_sha256']
        require(row['passed'] == row['audio_byte_identical'] == row['dry_byte_identical'] == equal, 'Regression byte-parity claim differs')
        regrows.append(dict(stage=key[0],case=key[1],audio_and_dry_byte_identical=equal,previous_waveform_gates_passed=prior['passed']))
    require(seen == set(old) and len(seen) == 1305, 'Wrong regression coverage')
    waves,cases = recipe(); current = {r['case']:r for r in fresh['cases']}
    require(set(current) == {c['name'] for c in cases} and len(fresh['cases']) == 8, 'Wrong fresh coverage')
    newrows = []; cold = []; fixtures = {}; members = None
    for c in cases:
        row = current[c['name']]; receipt,raw_a,x,provenance = checked(args.session,c,waves[c['source']])
        require(all(row[k] == v for k,v in provenance.items()) and row['role'] == 'fresh_prediction_bound', 'Fresh provenance/role differs')
        require(receipt['host_sha256'] == previous_audit['reference_host_sha256'], 'Reference host changed')
        members = receipt['plugin']['binary_files']; bundle = Path(receipt['plugin']['bundle'])
        require(members == previous_audit['original_binary_files'], 'Original bundle identity changed')
        output = args.comparison.parent/(c['name']+'.wav'); dry = args.comparison.parent/(c['name']+'-dry.wav'); plan = args.comparison.parent/(c['name']+'.tsv')
        require(sha256(output) == row['candidate_sha256'] and sha256(dry) == row['dry_trace_sha256']
                and sha256(plan) == row['schedule_sha256'] and plan.read_text() == schedule(c), 'Fresh output/dry/schedule changed')
        rate,b = float_wav(output); dry_rate,d = float_wav(dry)
        require(rate == dry_rate == 48000 and b.shape == raw_a.shape == d.shape, 'Fresh extent/rate differs')
        a,b,d = raw_a[32:],b[32:].astype(float),d[32:].astype(float); wa,wb = a-d,b-d
        scores = dict(whole=screen(a,b),wet=screen(wa,wb),post_input_tail=screen(a[len(x):],b[len(x):]))
        require(all(row[k] == v for k,v in scores.items()), 'Fresh waveform score differs')
        anchors = {0,12416} if c['enabled'] else set()
        anchors.update((e['frame']//32+1)*32+12416 for e in c['events'] if e['control']=='enabled' and e['value'])
        for name,positions in [('event_windows',sorted({e['frame'] for e in c['events']})),('startup_windows',sorted(anchors))]:
            scores[name] = []
            for at in positions:
                left,right = max(0,at-64),min(len(a),at+4096)
                if right > left:
                    scores[name].append(dict(frame=at,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
            require(scores[name] == row[name], 'Fresh event/startup score differs')
        passed = all(scores[k]['passed'] for k in ('whole','wet','post_input_tail')) and all(w[k]['passed'] for name in ('event_windows','startup_windows') for w in scores[name] for k in ('whole','wet'))
        require(row['passed'] == passed, 'Fresh acceptance flag differs')
        raw_b = float_wav(output)[1]; raw_d = float_wav(dry)[1]
        triple = [v[:12000].astype(np.float32) for v in (raw_a,raw_b,raw_d)]
        require(np.any(x[:12000]) and np.array_equal(triple[0],triple[1]) and np.array_equal(triple[0],triple[2]), 'Cold direct prefix differs')
        cold.append(dict(case=c['name'],frames=12000,numeric_equal=True,original_candidate_bit_exact=bool(np.array_equal(triple[0].view(np.uint32),triple[1].view(np.uint32))),original_dry_bit_exact=bool(np.array_equal(triple[0].view(np.uint32),triple[2].view(np.uint32)))))
        newrows.append(provenance | dict(passed=passed,readbacks_verified=True,all_screens_recomputed=True))
        if c['name'].endswith(('-0','-6')): fixtures[c['name']] = (receipt,plan,output,dry)
    for member in members:
        p = bundle/member['path']; require(sha256(p) == member['sha256'] and p.stat().st_size == member['bytes'], 'Installed original changed')
    guards = []
    prediction = json.loads(args.prediction.read_text())
    for field in ('kind','cases','source_sha256','source_samples_sha256','model_sha256','renderer_sha256','calibration_sha256','acceptance'):
        bad = copy.deepcopy(prediction)
        if field == 'cases': bad[field][0]['main'] += 1
        elif field in ('source_sha256','source_samples_sha256'): bad[field][next(iter(bad[field]))] = '0'*64
        elif field == 'acceptance': bad[field]['relative_rms_error_limit'] = 1
        else: bad[field] = 'modified'
        path = root/(field+'.json'); save_json(path,bad); forbidden = root/('forbidden-'+field)
        changed = copy.copy(args); changed.prediction = path; changed.session = forbidden
        try: capture(changed)
        except ValueError as error:
            require(str(error) == 'Frozen production prediction differs' and not forbidden.exists(), 'Prediction guard failed before capture')
            guards.append(field)
        else: raise ValueError('Altered prediction accepted')
    recipe_guards = []
    for field in ('main','amount','cutoff','tail','block','event-frame','source-samples'):
        c = copy.deepcopy(cases[0]); x = waves[c['source']]
        if field == 'source-samples': x = x.copy(); x[1,0] += .01
        elif field == 'event-frame': c['events'][0]['frame'] += 1
        else: c[field] += 1
        try: checked(args.session,c,x)
        except ValueError: recipe_guards.append(field)
        else: raise ValueError('Altered capture recipe accepted')
    source = root/'guard-input.wav'; wrong_rate = root/'wrong-rate.wav'; nonfinite = root/'nonfinite.wav'
    write_wav(source,48000,[.01,-.01]*2048); write_wav(wrong_rate,44100,[0,0]*2048)
    write_wav(nonfinite,48000,[float('nan'),0]*2048)
    valid = 'RMX_REVERB_MOTION 1\ninitial 128 128 0 1\ntail 1\nblock 128\n'
    changes = [
        ('schema',valid.replace('MOTION 1','MOTION 2')),('main-negative',valid.replace('initial 128','initial -1')),
        ('main-overflow',valid.replace('initial 128','initial 256')),('main-nan',valid.replace('initial 128','initial nan')),
        ('amount-overflow',valid.replace('128 128','128 256')),('cutoff-fraction',valid.replace('128 128 0','128 128 .5')),
        ('enabled',valid.replace('128 128 0 1','128 128 0 2')),('tail-negative',valid.replace('tail 1','tail -1')),
        ('tail-overflow',valid.replace('tail 1','tail 121')),('tail-nan',valid.replace('tail 1','tail nan')),
        ('block-low',valid.replace('block 128','block 7')),('block-high',valid.replace('block 128','block 4097')),
        ('negative-event',valid+'event -1 main 0\n'),('unknown-event',valid+'event 31 unknown 0\n'),
        ('unordered-events',valid+'event 33 main 0\nevent 31 main 1\n'),('event-extent',valid+'event 999999 main 0\n'),
    ]
    native = []
    for name,text in changes:
        plan = root/(name+'.tsv'); plan.write_text(text); output = root/(name+'.wav'); dry = root/(name+'-dry.wav')
        try: run([args.renderer,source,output,plan,dry])
        except RuntimeError:
            require(not output.exists() and not dry.exists(),'Rejected native request wrote output'); native.append(name)
        else: raise ValueError('Malformed native request accepted')
    plan = root/'valid.tsv'; plan.write_text(valid)
    for name,input_path,short in [('rate',wrong_rate,False),('argc',source,True)]:
        output = root/(name+'.wav'); dry = root/(name+'-dry.wav')
        argv = [args.renderer,input_path,output,plan] + ([] if short else [dry])
        try: run(argv)
        except RuntimeError:
            require(not output.exists() and not dry.exists(),'Rejected native input wrote output'); native.append(name)
        else: raise ValueError('Invalid native input accepted')
    for which in ('output','dry'):
        output = root/('existing-'+which+'.wav'); dry = root/('existing-'+which+'-dry.wav')
        sentinel = output if which == 'output' else dry; sentinel.write_bytes(b'keep-existing-output')
        try: run([args.renderer,source,output,plan,dry])
        except RuntimeError:
            require(sentinel.read_bytes() == b'keep-existing-output','Existing output changed'); native.append('existing-'+which)
        else: raise ValueError('Existing native output accepted')
    clean = root/'nan-clean.wav'; clean_dry = root/'nan-clean-dry.wav'
    run([args.renderer,nonfinite,clean,plan,clean_dry])
    require(not np.any(float_wav(clean)[1]),'NaN-to-zero WAV policy differs')
    manifest = instrumented(args); parity = []
    for name,(receipt,plan,expected,dry) in fixtures.items():
        output = root/(name+'.wav'); trace = root/(name+'-dry.wav')
        run([args.sanitized,receipt['input_path'],output,plan,trace])
        require(sha256(output) == sha256(expected) and sha256(trace) == sha256(dry), 'Sanitizer audio/dry differs')
        parity.append(dict(case=name,audio_sha256=sha256(output),dry_sha256=sha256(trace),byte_identical=True))
    require(len(parity) == 2 and source_hashes() == binding, 'Sanitizer coverage/candidate changed')
    passed = all(r['audio_and_dry_byte_identical'] for r in regrows) and all(r['passed'] for r in newrows)
    save_json(root/'verification.json',dict(kind='rmx220-reverb-up-production-audit',passed=passed,
              script_sha256=sha256(Path(__file__)),source_sha256=binding,acceptance=ACCEPTANCE,
              renderer_sha256=sha256(args.renderer),prediction_sha256=sha256(args.prediction),
              comparison_sha256=sha256(args.comparison),regressions_sha256=sha256(args.regressions),previous_audit_sha256=sha256(args.previous_audit),
              prior_cases=regrows,fresh_cases=newrows,cold_prefixes=cold,rejected_recipes=recipe_guards,rejected_predictions=guards,
              rejected_native_requests=native,nonfinite_input_sanitized_to_zero=True,
              sanitizer=manifest,sanitized_renders=parity,
              full_reverb_match=False,physical_hardware=False,
              scope='1305 byte-identical prior regressions plus eight fresh prospective cases. Standalone bounded Up; Engine, MCU deadlines and device-wide fidelity remain separate.'))
    print('Audited 1305 prior WAV/dry identities, eight fresh references, guards and two sanitizer programs',flush=True)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model','calibration','renderer','prediction','session','comparison','regressions','previous-audit','motion-comparison','static-comparison','sanitized','sanitized-build','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(audit(parser.parse_args()))


if __name__ == '__main__':
    main()
