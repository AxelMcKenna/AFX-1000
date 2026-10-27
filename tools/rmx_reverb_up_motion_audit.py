#!/usr/bin/env python3
"""Audit scoped Up motion/static waveforms, frozen captures, guards and sanitizer parity."""
import argparse
import copy
import json
from pathlib import Path
import shlex

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_factory_match import new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked as checked_static
from tools.rmx_reverb_up_model import model_checked,session_recipe
from tools.rmx_reverb_up_model_audit import auxiliary
from tools.rmx_reverb_up_motion import checked,recipe,prediction_payload,source_hashes,capture,HOLDOUT_STAGES

ACCEPTANCE=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,
                reference_offset_frames=32,candidate_offset_frames=32,gain_fit=False,wet_alignment_search=False)


def require(value,message):
    if not value:raise ValueError(message)


def schedule(case):
    return ('RMX_REVERB_MOTION 1\n'+f'initial {case["main"]} {case["amount"]} {case["cutoff"]} {case["enabled"]}\n'
        +f'tail {case["tail"]}\nblock {case["block"]}\n'+''.join(f'event {e["frame"]} {e["control"]} {e["value"]}\n' for e in case['events']))


def sanitizer_manifest(args):
    repo=Path(__file__).resolve().parents[1];build=args.sanitized_build.resolve();manifest=build/'compile_commands.json'
    require(args.sanitized.resolve()==build/'rmx_reverb_up_motion_probe','Unexpected sanitizer binary')
    entries=json.loads(manifest.read_text());objects={};newest=0
    for name in ('research/audio/experiments/ReverbUpMotion.cpp','research/audio/experiments/reverb_up_motion_probe.cpp','src/core/Wav.cpp'):
        matches=[e for e in entries if Path(e['file']).resolve()==repo/name];require(len(matches)==1,'Missing/ambiguous sanitizer entry')
        e=matches[0];command=e.get('arguments') or shlex.split(e['command']);flags={flag for item in command if item.startswith('-fsanitize=') for flag in item.split('=',1)[1].split(',')}
        require({'address','undefined'}<=flags and '-fno-omit-frame-pointer' in command,'Missing sanitizer flags')
        dependencies=[repo/name,repo/'include/rmx/Wav.h',repo/'include/rmx/Dsp.h']
        if name!='src/core/Wav.cpp':dependencies += [repo/'research/audio/experiments'/s for s in ('ReverbUpMotion.h','ReverbUpMotionCalibration.h','ReverbUpControlCalibration.h')]
        obj=Path(e['directory'])/command[command.index('-o')+1];require(obj.stat().st_mtime_ns>=max(p.stat().st_mtime_ns for p in dependencies),'Stale instrumented object')
        newest=max(newest,obj.stat().st_mtime_ns);objects[name]=dict(command=command,dependency_sha256={str(p.relative_to(repo)):sha256(p) for p in dependencies},object_sha256=sha256(obj))
    require(args.sanitized.stat().st_mtime_ns>=newest,'Stale sanitizer executable')
    return dict(renderer_sha256=sha256(args.sanitized),compile_commands_sha256=sha256(manifest),instrumented_sources=objects)


def audit(args):
    model_checked(args);root=new_directory(args.output);prediction=json.loads(args.prediction.read_text());stage=prediction['stage'];binding=source_hashes()
    require(all(prediction.get(k)==v for k,v in prediction_payload(stage).items()) and prediction['renderer_sha256']==sha256(args.renderer)
        and prediction['model_sha256']==sha256(args.model) and prediction['calibration_sha256']==sha256(args.calibration),'Current frozen binding differs')
    motion=json.loads(args.comparison.read_text());static=json.loads(args.static_comparison.read_text())
    for report in (motion,static):
        require(report['source_sha256']==binding and report['model_sha256']==sha256(args.model) and report['calibration_sha256']==sha256(args.calibration)
            and report['renderer_sha256']==sha256(args.renderer) and report['acceptance']==ACCEPTANCE,'Comparison binding/gate differs')
    records={}
    for path,report in ((args.comparison,motion),(args.static_comparison,static)):
        for row in report['cases']:
            key=row['stage'],row['case'];require(key not in records,'Duplicate comparison');records[key]=path.parent,row
    historical=dict(args.historical_prediction or []);verified=[];direct=[];cold=[];seen=set();hosts=set();members=None;bundle=None;fixtures={}
    for dynamic,sessions in ((True,args.motion_session),(False,args.static_session)):
        for session_stage,directory in sessions:
            if dynamic and session_stage in HOLDOUT_STAGES:
                path=args.prediction if session_stage==stage else historical[session_stage];saved=json.loads(path.read_text());manifest=json.loads((directory/'matrix.json').read_text())
                expected=prediction_payload(session_stage)
                if session_stage!=stage:expected={k:v for k,v in expected.items() if k!='source_sha256'}
                require(all(saved[k]==v for k,v in expected.items()) and sha256(directory/'predictions.json')==sha256(path)
                    and manifest['prediction_sha256']==sha256(path),'Frozen capture recipe/copy differs')
            waves,cases=recipe(session_stage) if dynamic else session_recipe(session_stage)
            for c in cases:
                key=session_stage,c['name'];require(key not in seen,'Duplicate session');seen.add(key);parent,row=records[key]
                if dynamic:
                    receipt,raw_a,x,provenance=checked(directory,c,waves[c['source']]);a=raw_a[32:]
                else:
                    receipt,a,x,provenance=checked_static(directory,c,waves[c['source']]);auxiliary(directory/c['name'],receipt)
                require(all(row[k]==v for k,v in provenance.items()),'Comparison provenance differs')
                prefix=session_stage+'-'+c['name'];output=parent/(prefix+'.wav');dry_path=parent/(prefix+'-dry.wav');plan=parent/(prefix+'.tsv')
                require(sha256(output)==row['candidate_sha256'] and sha256(dry_path)==row['dry_trace_sha256'] and sha256(plan)==row['schedule_sha256'],'Candidate/trace/schedule changed')
                expected_plan=schedule(c if dynamic else c|dict(enabled=1,block=128,events=[]))
                require(plan.read_text()==expected_plan,'Candidate schedule differs from reference controls')
                rate,raw_b=float_wav(output);dry_rate,raw_d=float_wav(dry_path)
                require(rate==48000 and dry_rate==rate and len(raw_b)==len(a)+32 and raw_b.shape==raw_d.shape,'Candidate extent/rate differs')
                b=raw_b[32:].astype(float);dry=raw_d[32:].astype(float);wa,wb=a-dry,b-dry
                groups=dict(whole=screen(a,b),wet=screen(wa,wb),post_input_tail=screen(a[len(x):],b[len(x):]))
                require(all(value==row[k] for k,value in groups.items()),'Recomputed waveform score differs')
                windows=[];starts=[]
                if dynamic:
                    for at in sorted({e['frame'] for e in c['events']}):
                        left,right=max(0,at-64),min(len(a),at+4096)
                        windows.append(dict(frame=at,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
                    anchors={0,12416} if c['enabled'] else set();anchors.update((e['frame']//32+1)*32+12416 for e in c['events'] if e['control']=='enabled' and e['value'])
                    for at in sorted(anchors):
                        left,right=max(0,at-64),min(len(a),at+4096)
                        if right>left:starts.append(dict(frame=at,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
                    require(windows==row['event_windows'] and starts==row['startup_windows'],'Recomputed event/startup windows differ')
                    expected_role='fresh_prediction_bound' if session_stage==stage else 'prior_frozen_regression' if session_stage in HOLDOUT_STAGES else 'development_regression'
                    require(row['role']==expected_role,'Mislabelled prospective/regression role')
                    stop=min(12000,len(x))
                    if np.any(x[:stop]):
                        require(np.array_equal(raw_a[:stop].astype(np.float32),raw_b[:stop]) and np.array_equal(raw_a[:stop].astype(np.float32),raw_d[:stop]),'Cold direct-only prefix differs')
                        cold.append(dict(stage=session_stage,case=c['name'],frames=stop,original_candidate_dry_equal_numeric=True,
                            original_candidate_bit_exact=bool(np.array_equal(raw_a[:stop].astype(np.float32).view(np.uint32),raw_b[:stop].view(np.uint32))),
                            original_dry_bit_exact=bool(np.array_equal(raw_a[:stop].astype(np.float32).view(np.uint32),raw_d[:stop].view(np.uint32)))))
                else:
                    expected=np.zeros_like(raw_d);expected[32:32+len(x)]=x
                    require(np.array_equal(expected.view(np.uint32),raw_d.view(np.uint32)),'Static predicted dry differs from delayed input')
                    nonzero=np.flatnonzero(np.any(x!=0,axis=1))
                    if len(nonzero):
                        left=int(nonzero[0]);right=min(len(x),left+128);bits=[v[left:right].astype(np.float32).view(np.uint32) for v in (a,b,x)]
                        require(np.array_equal(bits[0],bits[2]) and np.array_equal(bits[1],bits[2]),'Static direct-only prefix differs')
                        direct.append(dict(stage=session_stage,case=c['name'],start=left,frames=right-left,original_candidate_source_bit_exact=True))
                    else:require(not np.any(a) and not np.any(b),'Silent static input produces audio')
                passed=all(v['passed'] for v in groups.values()) and all(w[k]['passed'] for w in windows+starts for k in ('whole','wet'))
                require(row['passed']==passed,'Saved acceptance flag differs')
                hosts.add(receipt['host_sha256'])
                if members is None:members=receipt['plugin']['binary_files'];bundle=Path(receipt['plugin']['bundle'])
                require(receipt['plugin']['binary_files']==members,'Original bundle members differ')
                verified.append(provenance|dict(stage=session_stage,dynamic=dynamic,applied_controls_and_auxiliary_hashes_verified=True,screens_recomputed=True,passed=passed))
                if dynamic and session_stage==stage and c['name'].endswith(('-3','-15')):fixtures[c['name'].rsplit('-',1)[1]]=(directory,c,waves[c['source']],parent,row)
            print('Audited',session_stage,len(cases),flush=True)
    require(seen==set(records) and len(hosts)==1 and len(fixtures)==2,'Coverage/host differs')
    for member in members:require(sha256(bundle/member['path'])==member['sha256'] and (bundle/member['path']).stat().st_size==member['bytes'],'Installed original changed')
    proof=json.loads(args.read_window_proof.read_text());negative=json.loads(args.negative_comparison.read_text());key=('holdout',proof['case']);parent,row=records[key]
    old=next(r for r in negative['cases'] if (r['stage'],r['case'])==key)
    require(proof['passed'] and sha256(args.negative_comparison)==proof['old_comparison_sha256'] and old['candidate_sha256']==proof['old_candidate_sha256']
        and row['candidate_sha256']==proof['corrected_candidate_sha256'] and proof['reference_receipt_sha256']==row['receipt_sha256'],'Retained read-window negative/correction differs')
    require(sha256(args.negative_comparison.parent/('holdout-'+proof['case']+'.wav'))==proof['old_candidate_sha256'],'Negative-control audio changed')
    directory,c,signal,parent,row=fixtures['3'];recipe_guards=[]
    for field in ('main','amount','cutoff','tail','block','event-frame','source-samples'):
        changed=copy.deepcopy(c);source=signal
        if field=='source-samples':source=signal.copy();source[1,0]+=.01
        elif field=='event-frame':changed['events'][0]['frame']+=1
        else:changed[field]+=1
        try:checked(directory,changed,source)
        except ValueError:recipe_guards.append(field)
        else:raise ValueError('Changed recipe accepted')
    prediction_guards=[]
    for field in ('kind','stage','cases','source_sha256','source_samples_sha256','model_sha256','renderer_sha256','calibration_sha256'):
        bad=copy.deepcopy(prediction)
        if field=='cases':bad[field][0]['main']+=1
        elif field in ('source_sha256','source_samples_sha256'):bad[field][next(iter(bad[field]))]='0'*64
        else:bad[field]='modified'
        path=root/(field+'.json');save_json(path,bad);forbidden=root/('forbidden-'+field)
        try:capture(argparse.Namespace(stage=stage,model=args.model,calibration=args.calibration,prediction=path,session=forbidden))
        except ValueError as error:require(str(error)=='Frozen Up motion prediction differs' and not forbidden.exists(),'Frozen guard did not reject before capture');prediction_guards.append(field)
        else:raise ValueError('Changed prediction accepted')
    source=root/'guard-input.wav';wrong_rate=root/'wrong-rate.wav';nonfinite=root/'nonfinite.wav';write_wav(source,48000,[.01,-.01]*2048);write_wav(wrong_rate,44100,[0,0]*2048);write_wav(nonfinite,48000,[float('nan'),0]*2048)
    valid='RMX_REVERB_MOTION 1\ninitial 128 128 0 1\ntail 1\nblock 128\n'
    changes=[('schema',valid.replace('MOTION 1','MOTION 2')),('main-negative',valid.replace('initial 128','initial -1')),('main-overflow',valid.replace('initial 128','initial 256')),
        ('main-nan',valid.replace('initial 128','initial nan')),('amount-overflow',valid.replace('128 128','128 256')),('cutoff-fraction',valid.replace('128 128 0','128 128 .5')),
        ('enabled',valid.replace('128 128 0 1','128 128 0 2')),('tail-negative',valid.replace('tail 1','tail -1')),('tail-overflow',valid.replace('tail 1','tail 121')),
        ('tail-nan',valid.replace('tail 1','tail nan')),('block-low',valid.replace('block 128','block 7')),('block-high',valid.replace('block 128','block 4097')),
        ('negative-event',valid+'event -1 main 0\n'),('unknown-event',valid+'event 31 unknown 0\n'),('unordered-events',valid+'event 33 main 0\nevent 31 main 1\n'),
        ('event-extent',valid+'event 999999 main 0\n')]
    native=[]
    for name,text in changes:
        path=root/(name+'.tsv');path.write_text(text);output=root/(name+'.wav');dry_path=root/(name+'-dry.wav')
        try:run([args.renderer,source,output,path,dry_path])
        except RuntimeError:require(not output.exists() and not dry_path.exists(),'Rejected native request wrote audio');native.append(name)
        else:raise ValueError('Malformed native schedule accepted')
    plan=root/'valid.tsv';plan.write_text(valid)
    for name,input_file,argv in [('rate',wrong_rate,None),('argc',source,[])]:
        output=root/(name+'.wav');dry_path=root/(name+'-dry.wav')
        try:run([args.renderer,input_file,output,plan,dry_path] if argv is None else [args.renderer,input_file,output,plan])
        except RuntimeError:require(not output.exists() and not dry_path.exists(),'Rejected native input wrote output');native.append(name)
        else:raise ValueError('Invalid rate/argument count accepted')
    for which in ('output','dry'):
        output=root/('existing-'+which+'.wav');dry_path=root/('existing-'+which+'-dry.wav');sentinel=output if which=='output' else dry_path;sentinel.write_bytes(b'keep-existing-output')
        try:run([args.renderer,source,output,plan,dry_path])
        except RuntimeError:require(sentinel.read_bytes()==b'keep-existing-output','Existing output changed');native.append('existing-'+which)
        else:raise ValueError('Existing output accepted')
    clean=root/'sanitized-nan.wav';clean_dry=root/'sanitized-nan-dry.wav';run([args.renderer,nonfinite,clean,plan,clean_dry]);require(not np.any(float_wav(clean)[1]),'NaN-to-zero input policy differs')
    # Nominal latency is checked on a settled, initially disabled callback128 fixture.
    quiet=np.zeros((4096,2));quiet[512:]=np.random.default_rng(0x7570B1).normal(0,.01,(3584,2));bypass_input=root/'bypass-input.wav';write_wav(bypass_input,48000,quiet.ravel())
    bypass_plan=root/'bypass.tsv';bypass_plan.write_text(valid.replace('128 128 0 1','128 128 0 0'));bypass=root/'bypass.wav';bypass_dry=root/'bypass-dry.wav';run([args.renderer,bypass_input,bypass,bypass_plan,bypass_dry]);audio=float_wav(bypass)[1]
    rejected_offsets=[]
    for offset in (0,31,32,33):
        expected=np.zeros_like(audio);expected[offset:offset+len(quiet)]=quiet.astype(np.float32)
        if offset==32:require(np.array_equal(audio.view(np.uint32),expected.view(np.uint32)),'Nominal bypass32 differs')
        else:require(not screen(expected,audio)['passed'],'Wrong bypass offset accepted');rejected_offsets.append(offset)
    # Both causal schedules have identical callback split points, including the test anchor.
    causal=np.random.default_rng(0x7570CA).normal(0,.013,(32000,2));alternate=causal.copy();alternate[15013:]*=-.37;causal_audio=[];causal_dry=[]
    for label,x,target in [('base',causal,149),('changed',alternate,241)]:
        source_path=root/('causal-'+label+'-input.wav');write_wav(source_path,48000,x.ravel());plan_path=root/('causal-'+label+'.tsv')
        plan_path.write_text('RMX_REVERB_MOTION 1\ninitial 224 149 37 1\ntail 1\nblock 31\nevent 12011 main 197\n'+f'event 15013 cutoff {target}\n')
        output=root/('causal-'+label+'.wav');dry_path=root/('causal-'+label+'-dry.wav');run([args.renderer,source_path,output,plan_path,dry_path]);causal_audio.append(float_wav(output)[1]);causal_dry.append(float_wav(dry_path)[1])
    require(np.array_equal(causal_audio[0][:15013].view(np.uint32),causal_audio[1][:15013].view(np.uint32)) and np.array_equal(causal_dry[0][:15013].view(np.uint32),causal_dry[1][:15013].view(np.uint32)) and not np.array_equal(causal_audio[0][15013:],causal_audio[1][15013:]),'Causal input/control prefix differs')
    instrumented=sanitizer_manifest(args);sanitized=[]
    for label,(directory,c,_,parent,row) in fixtures.items():
        receipt=json.loads((directory/c['name']/'receipt.json').read_text());output=root/(label+'-asan.wav');dry_path=root/(label+'-asan-dry.wav');plan_path=parent/(stage+'-'+c['name']+'.tsv')
        run([args.sanitized,receipt['input_path'],output,plan_path,dry_path]);require(sha256(output)==row['candidate_sha256'] and sha256(dry_path)==row['dry_trace_sha256'],'Optimized/sanitized audio or dry trace differs')
        sanitized.append(dict(case=c['name'],output_sha256=sha256(output),dry_trace_sha256=sha256(dry_path),byte_exact=True))
    passed=all(c['passed'] for c in verified)
    save_json(root/'verification.json',dict(kind='rmx220-reverb-up-motion-audit',passed=passed,provenance_verified=True,waveform_acceptance_passed=passed,
        script_sha256=sha256(Path(__file__)),auxiliary_helper_sha256=sha256(Path('tools/rmx_reverb_up_model_audit.py')),model_sha256=sha256(args.model),prediction_sha256=sha256(args.prediction),
        comparison_sha256=sha256(args.comparison),static_comparison_sha256=sha256(args.static_comparison),renderer_sha256=sha256(args.renderer),source_sha256=binding,acceptance=ACCEPTANCE,
        reference_host_sha256=next(iter(hosts)),original_binary_files=members,captures=verified,static_direct_only_prefixes=direct,cold_direct_only_prefixes=cold,
        read_window_proof_sha256=sha256(args.read_window_proof),rejected_recipe_changes=recipe_guards,rejected_prediction_changes=prediction_guards,rejected_native_requests=native,
        nonfinite_input_sanitized_to_zero=True,bypass_nominal32_bit_exact=True,rejected_bypass_offsets=rejected_offsets,
        causal_prefix=dict(changed_at_frame=15013,whole_output_and_dry_bit_exact_before=True,later_output_differs=True,callback_split_points_identical=True),
        sanitizer=instrumented,sanitized_renders=sanitized,
        limitations=['Standalone factory Up, integer controls, stereo48k/120BPM only; no live Engine, other profiles/rates/tempos, overload, listening or hardware claim.',
            'Sanitizers cover the two stated complete programs. Offline WAV buffers allocate; callback allocation/resource and MCU deadline qualification remain separate.',
            'Prior frozen tests become regressions after correction. Fixed comparison crops do not search away partial-callback timing.']))
    print('Audited',len(verified),'captures,',len(cold),'non-silent cold prefixes,',len(direct),'static prefixes, guards and sanitizer parity',flush=True)
    return 0 if passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','calibration','prediction','comparison','static-comparison','renderer','sanitized','sanitized-build','read-window-proof','negative-comparison','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--motion-session',nargs=2,action='append',required=True);p.add_argument('--static-session',nargs=2,action='append',required=True);p.add_argument('--historical-prediction',nargs=2,action='append')
    args=p.parse_args();args.motion_session=[(s,Path(d)) for s,d in args.motion_session];args.static_session=[(s,Path(d)) for s,d in args.static_session]
    raise SystemExit(audit(args))


if __name__=='__main__':main()
