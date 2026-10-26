#!/usr/bin/env python3
"""Audit static Up captures, frozen predictions, negative controls and sanitizers."""
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
from tools.rmx_reverb_characterize import checked
from tools.rmx_reverb_up import capture,model_checked,payload,recipe


def audit(args):
    model_checked(args);root=new_directory(args.output);prediction=json.loads(args.prediction.read_text())
    if (any(prediction.get(k)!=v for k,v in payload().items()) or prediction['model_sha256']!=sha256(args.model)
            or prediction['calibration_sha256']!=sha256(args.calibration) or prediction['renderer_sha256']!=sha256(args.renderer)):
        raise ValueError('Frozen prediction/source/model/calibration/renderer differs')
    reports=[json.loads(p.read_text()) for p in args.comparison];records={}
    for path,report in zip(args.comparison,reports):
        if (report['model_sha256']!=sha256(args.model) or report['renderer_sha256']!=sha256(args.renderer)
                or report['source_sha256']!=prediction['source_sha256']):raise ValueError('Comparison binding differs')
        for row in report['cases']:
            key=row['stage'],row['case']
            if key in records:raise ValueError('Duplicate comparison case')
            records[key]=(path.parent,row)
    verified=[];direct=[];hosts=set();seen=set();fixture=None;negative_alignment=None
    for stage,directory in args.session:
        if stage=='holdout':
            manifest=json.loads((directory/'matrix.json').read_text())
            if manifest['prediction_sha256']!=sha256(args.prediction) or sha256(directory/'predictions.json')!=sha256(args.prediction):raise ValueError('Fresh captures are not frozen-prediction bound')
        waves,cases=recipe(stage)
        for c in cases:
            _,a,x,provenance=checked(directory,c,waves[c['source']]);folder=directory/c['name'];key=stage,c['name'];seen.add(key)
            receipt=json.loads((folder/'receipt.json').read_text());plan=json.loads((folder/'plan.json').read_text())
            for name,field in [('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
                if sha256(folder/name)!=receipt[field]:raise ValueError('Modified auxiliary capture file')
            log=json.loads((folder/'parameter-log.json').read_text())['entries']
            if len(log)!=len(plan['parameters']):raise ValueError('Unexpected parameter event')
            for requested,actual in zip(plan['parameters'],log):
                if (actual['frame']!=-1 or any(actual[k]!=requested[k] for k in ('index','id','name'))
                        or np.float32(actual['requested_value'])!=np.float32(requested['value'])
                        or abs(actual['immediate_readback']-float(np.float32(requested['value'])))>1e-14):raise ValueError('Immediate control readback differs')
            final={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
            if any(abs(final[p['name']]-float(np.float32(p['value'])))>1e-14 for p in plan['parameters']):raise ValueError('Final controls differ')
            parent,row=records[key]
            if any(row[k]!=v for k,v in provenance.items()):raise ValueError('Comparison provenance differs')
            output=parent/(stage+'-'+c['name']+'.wav')
            if sha256(output)!=row['candidate_sha256']:raise ValueError('Candidate audio changed')
            b=float_wav(output)[1][:len(a)]
            nonzero=np.flatnonzero(np.any(x!=0,axis=1))
            if len(nonzero):
                start=int(nonzero[0]);stop=min(start+128,len(x))
                original_bits=a[start:stop].astype(np.float32).view(np.uint32)
                candidate_bits=b[start:stop].view(np.uint32);source_bits=x[start:stop].view(np.uint32)
                if not np.array_equal(original_bits,source_bits) or not np.array_equal(candidate_bits,source_bits):raise ValueError('Initial direct-only gain/timing check differs')
                direct.append(dict(stage=stage,case=c['name'],start=start,frames=stop-start,original_candidate_source_bit_exact=True))
            elif np.any(a) or np.any(b):raise ValueError('Silent input produced audio')
            if stage=='initial' and c['name']=='up-source-left':
                fixture=(directory,c,waves[c['source']],output)
                dry=np.zeros_like(a);dry[:min(len(x),len(a))]=x[:len(a)]
                shifted=np.pad(b,((1,0),(0,0)))[:len(b)]
                negative_alignment=dict(whole=screen(a,shifted),wet=screen(a-dry,shifted-dry))
                if negative_alignment['whole']['passed'] or negative_alignment['wet']['passed']:raise ValueError('One-frame negative alignment was not rejected')
            verified.append(provenance|dict(stage=stage,applied_controls_verified=True,auxiliary_hashes_verified=True));hosts.add(receipt['host_sha256'])
    if seen!=set(records) or len(hosts)!=1 or fixture is None:raise ValueError('Session coverage or original host differs')
    directory,c,source,valid_output=fixture;guards=[]
    for field in ('main','amount','cutoff','tail','source-samples'):
        changed=copy.deepcopy(c);signal=source
        if field=='source-samples':signal=source.copy();signal[1,0]=.01
        else:changed[field]+=1
        try:checked(directory,changed,signal)
        except ValueError:guards.append(field)
        else:raise ValueError('Changed static recipe accepted: '+field)
    prediction_guards=[]
    for field in ('kind','cases','source_sha256','samples_sha256','model_sha256','renderer_sha256','calibration_sha256'):
        bad=copy.deepcopy(prediction)
        if field=='cases':bad[field][0]['main']+=1
        elif field in ('source_sha256','samples_sha256'):bad[field][next(iter(bad[field]))]='0'*64
        else:bad[field]='modified'
        path=root/(field+'.json');save_json(path,bad)
        forbidden=root/('forbidden-'+field)
        try:capture(argparse.Namespace(model=args.model,calibration=args.calibration,prediction=path,session=forbidden))
        except ValueError as error:
            if str(error)!='Frozen prediction differs' or forbidden.exists():raise
            prediction_guards.append(field)
        else:raise ValueError('Modified prediction accepted')
    native=[];input_path=Path(json.loads((directory/c['name']/'receipt.json').read_text())['input_path'])
    wrong_rate=root/'wrong-rate-input.wav';nonfinite=root/'nonfinite-input.wav'
    write_wav(wrong_rate,44100,[0,0]*1024);write_wav(nonfinite,48000,[float('nan'),0]*1024)
    requests=[('raw-negative',input_path,-1,1),('raw-overflow',input_path,256,1),('raw-fraction',input_path,.5,1),
        ('raw-nan',input_path,'nan',1),('tail-negative',input_path,0,-1),('tail-overflow',input_path,0,121),
        ('number-suffix',input_path,'19x',1),('rate',wrong_rate,0,1)]
    for name,input_file,raw,tail in requests:
        output=root/(name+'.wav')
        try:run([args.renderer,input_file,output,raw,tail])
        except RuntimeError:
            if output.exists():raise ValueError('Rejected input wrote audio')
            native.append(name)
        else:raise ValueError('Invalid native request accepted: '+name)
    sentinel=root/'existing.wav';sentinel.write_bytes(b'preserve-existing-output')
    try:run([args.renderer,input_path,sentinel,0,1])
    except RuntimeError:
        if sentinel.read_bytes()!=b'preserve-existing-output':raise ValueError('Existing output modified')
        native.append('existing-output')
    else:raise ValueError('Existing output accepted')
    sanitized_input=root/'nonfinite-sanitized-output.wav'
    run([args.renderer,nonfinite,sanitized_input,0,1])
    sample_rate,sanitized_audio=float_wav(sanitized_input)
    if sample_rate!=48000 or len(sanitized_audio)!=49024 or np.any(sanitized_audio):raise ValueError('WAV loader did not sanitize NaNs to silence')
    build=args.sanitized_build.resolve();manifest=build/'compile_commands.json';entries=json.loads(manifest.read_text());repo=Path(__file__).resolve().parents[1]
    if args.sanitized.resolve()!=build/'rmx_reverb_up_probe':raise ValueError('Unexpected sanitizer target')
    instrumented={};newest=0
    for name in ('research/audio/experiments/reverb_up_neutral_probe.cpp','src/core/Wav.cpp'):
        matching=[e for e in entries if Path(e['file']).resolve()==repo/name]
        if len(matching)!=1:raise ValueError('Missing/ambiguous sanitizer compile entry')
        entry=matching[0];command=entry.get('arguments') or shlex.split(entry['command'])
        enabled={s for item in command if item.startswith('-fsanitize=') for s in item.split('=',1)[1].split(',')}
        if not {'address','undefined'}<=enabled or '-fno-omit-frame-pointer' not in command:raise ValueError('Sanitizer flags absent')
        obj=Path(entry['directory'])/command[command.index('-o')+1];newest=max(newest,obj.stat().st_mtime_ns)
        if obj.stat().st_mtime_ns<(repo/name).stat().st_mtime_ns:raise ValueError('Stale sanitizer object')
        instrumented[name]=dict(command=command,source_sha256=sha256(repo/name),object_sha256=sha256(obj))
    if args.sanitized.stat().st_mtime_ns<newest:raise ValueError('Stale sanitizer binary')
    sanitized=[]
    for key in [('initial','up-source-left'),('holdout','up-up_program-cutoff-19')]:
        parent,row=records[key];directory=dict(args.session)[key[0]];receipt=json.loads((directory/key[1]/'receipt.json').read_text())
        c=next(c for c in recipe(key[0])[1] if c['name']==key[1]);output=root/(key[0]+'-'+key[1]+'-asan.wav')
        run([args.sanitized,receipt['input_path'],output,c['cutoff'],c['tail']])
        if sha256(output)!=row['candidate_sha256']:raise ValueError('Optimized/sanitized output differs')
        sanitized.append(dict(stage=key[0],case=key[1],output_sha256=sha256(output),byte_exact=True))
    save_json(root/'verification.json',dict(kind='rmx220-reverb-up-neutral-audit',passed=True,script_sha256=sha256(Path(__file__)),
        prediction_sha256=sha256(args.prediction),model_sha256=sha256(args.model),renderer_sha256=sha256(args.renderer),
        comparison_sha256=[sha256(p) for p in args.comparison],reference_host_sha256=next(iter(hosts)),captures=verified,
        direct_only_prefixes=direct,one_frame_negative_control=negative_alignment,rejected_recipe_changes=guards,
        rejected_prediction_changes=prediction_guards,rejected_native_inputs=native,sanitized_renderer_sha256=sha256(args.sanitized),
        nonfinite_wav_policy=dict(policy='Shared readWav replaces non-finite input samples with zero.',
            all_output_samples_zero=True,output_sha256=sha256(sanitized_input)),
        sanitizer_compile_commands_sha256=sha256(manifest),instrumented_sources=instrumented,sanitized_renders=sanitized,
        limitations=['Static neutral-setting research fixture, not production/motion/full-device validation.',
        'Compile recipes and fresh object hashes are checked; sanitizer execution covers the two stated programs, not every possible input.']))
    print('Audited',len(verified),'captures,',len(direct),'direct prefixes, guards and two sanitizer renders')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','calibration','prediction','renderer','sanitized','sanitized-build','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--session',nargs=2,action='append',required=True);p.add_argument('--comparison',type=Path,action='append',required=True)
    args=p.parse_args();args.session=[(s,Path(d)) for s,d in args.session];audit(args)


if __name__=='__main__':main()
