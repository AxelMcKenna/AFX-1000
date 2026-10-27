#!/usr/bin/env python3
"""Independently audit shared-clock drum/FX scores, failures and sanitizer parity."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import ACCEPTANCE,FRAMES,checked,frozen,payload,recipe,schedule,source_hashes
from tools.rmx_factory_match import new_directory
from tools.rmx_filter_match import screen


def verify(a,b,stored):
    require(len(a)>0 and len(stored['channels'])==2,'Missing score data');passed=True
    for ch,c in enumerate(stored['channels']):
        x=a[:,ch].astype(np.float64);delta=x-b[:,ch].astype(np.float64)
        energy=float(np.sum(x*x));error=float(np.sum(delta*delta));absolute=math.sqrt(error/len(x));relative=math.sqrt(error/energy) if energy>1e-20 else None
        require(math.isclose(absolute,c['absolute_error_rms'],rel_tol=1e-12,abs_tol=1e-15),'Absolute score differs')
        require((relative is None and c['relative_rms_error'] is None) or (relative is not None and math.isclose(relative,c['relative_rms_error'],rel_tol=1e-12,abs_tol=1e-15)),'Relative score differs')
        ok=relative<=.01 if relative is not None else absolute<=1e-8
        require(c['passed']==ok,'Channel pass differs');passed=passed and ok
    require(stored['passed']==passed,'Screen pass differs');return passed


def guards(args,root,source,plan):
    with tempfile.TemporaryDirectory(prefix='rmx-drums-fx-prediction-') as folder:
        for field in ['case','gate']:
            d=json.loads(args.prediction.read_text())
            if field=='case':d['cases'][1]['block']+=1
            else:d['acceptance']['relative_rms_error_limit']=.02
            p=Path(folder)/(field+'.json');save_json(p,d);changed=copy.copy(args);changed.prediction=p
            try:frozen(changed)
            except ValueError as error:require(str(error)=='Frozen shared-clock drum/FX prediction differs','Unexpected prediction rejection')
            else:raise ValueError('Modified prediction accepted')
    path=root/'existing-output.wav';path.write_bytes(b'do not replace')
    result=subprocess.run([str(args.renderer),str(source),str(path),str(plan)],capture_output=True,text=True,timeout=120)
    require(result.returncode!=0 and path.read_bytes()==b'do not replace' and 'Output must be new' in result.stderr,'Existing output overwritten')
    _,a=float_wav(source);a=a[32:288000].astype(float);shifted=np.zeros_like(a);shifted[1:]=a[:-1]
    require(not screen(a,shifted)['passed'] and not screen(a,a*1.1)['passed'],'Waveform guard failed')
    return dict(modified_case_rejected=True,relaxed_gate_rejected=True,existing_output_preserved=True,one_frame_shift_rejected=True,ten_percent_gain_error_rejected=True)


def audit(args):
    args.stage=args.prediction_stage
    frozen(args);binding=source_hashes();root=new_directory(args.output);rows=[];screens=0
    required={'fresh':['discovery','fresh'],'fresh-v2':['discovery','former','fresh-v2'],
              'fresh-v3':['discovery','former','second','fresh-v3'],
              'fresh-v4':['discovery','former','second','third','fresh-v4'],
              'fresh-v5':['discovery','former','second','third','fourth','fresh-v5'],
              'fresh-v6':['discovery','former','second','third','fourth','fifth','fresh-v6'],
              'live-fresh':['discovery','former','second','third','fourth','fifth','sixth','live-fresh']}[args.stage]
    require(sorted(d[0] for d in args.dataset)==sorted(required),'Requires exactly the complete declared datasets')
    legacy={'former':('fresh',args.former_prediction),'second':('fresh-v2',args.second_prediction),'third':('fresh-v3',args.third_prediction),'fourth':('fresh-v4',args.fourth_prediction),'fifth':('fresh-v5',args.fifth_prediction),'sixth':('fresh-v6',args.sixth_prediction)}
    for name in set(required)&set(legacy):
        recipe_stage,prediction=legacy[name];require(prediction is not None,'Requires the '+name+' frozen prediction')
        old=json.loads(prediction.read_text());call=copy.copy(args);call.stage=recipe_stage;expected=payload(call)
        require(old['kind']=='rmx220-drums-fx-shared-prediction' and all(old[k]==expected[k] for k in ('cases','source_samples_sha256','acceptance')),'Former recipe/gates differ')
    command_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(command_path.read_text())
    suffixes=('/Scene.cpp','/ReverbUp.cpp','/ReverbDown.cpp','/drums/Kick.cpp','/drums/Snare.cpp','/drums/Clap.cpp','/drums/Hat.cpp','/Wav.cpp')
    native=args.backend=='engine'
    if native:suffixes+=('/Engine.cpp',)
    selected=[c for c in commands if c['file'].endswith(suffixes) or (c['file'].endswith('/drums_fx_probe.cpp') and ('RMX_DRUMS_SHARED_FIXTURE=1' in c['command'])!=native)]
    require(len(selected)==(10 if native else 9) and all('-fsanitize=address,undefined' in c['command'] for c in selected),'Missing sanitizer units/flags')
    require(all('-ffp-contract=off' in c['command'] for c in selected if '/drums/' in c['file'] or '/Reverb' in c['file']),'Missing generator/reverb float flags')
    symbols={}
    if native:
        for name,binary in [('optimized',args.renderer),('sanitized',args.sanitized)]:
            output=subprocess.check_output(['nm','-C',str(binary)],text=True)
            require('rmx::Engine::process(' in output,'Native fixture lacks the live Engine process entry point')
            symbols[name]=dict(engine_process_symbol_present=True,nm_output_sha256=hashlib.sha256(output.encode()).hexdigest())
    first_source=first_plan=None
    for stage,session_text,report_text in args.dataset:
        recipe_stage=legacy[stage][0] if stage in legacy else stage
        session=Path(session_text);path=Path(report_text);d=json.loads(path.read_text());cases=recipe(recipe_stage);call=copy.copy(args);call.session=session;call.stage=recipe_stage;baselines={};case_results=[]
        role='development_regression' if stage=='discovery' else 'former_prediction_regression' if stage in legacy else 'fresh_prediction_bound'
        require(d['kind']=='rmx220-drums-fx-discovery-comparison' and d['backend']==args.backend and d['live_engine']==native and d['stage']==recipe_stage and d['role']==role and d['source_sha256']==binding and d['acceptance']==ACCEPTANCE
                and d['renderer_sha256']==sha256(args.renderer) and [r['case'] for r in d['cases']]==[c['name'] for c in cases],'Comparison source/recipe/gates differ')
        if stage!='discovery':
            prediction=legacy[stage][1] if stage in legacy else args.prediction
            require(d['prediction_sha256']==sha256(prediction)==sha256(session/'predictions.json')==json.loads((session/'matrix.json').read_text())['prediction_sha256'],'Prediction copy differs')
        for c,row in zip(cases,d['cases']):
            original,provenance=checked(call,c);require(all(row[k]==v for k,v in provenance.items()) and all(row[k]==c[k] for k in ('effect','route','enabled')),'Original provenance differs')
            output=path.parent/(c['name']+'.wav');plan=path.parent/(c['name']+'.tsv')
            require(sha256(output)==row['candidate_sha256'] and sha256(plan)==row['schedule_sha256'] and plan.read_text()==schedule(c),'Candidate artifact differs')
            rate,b=float_wav(output);require(rate==48000 and original.shape==b.shape==(FRAMES,2),'Candidate extent differs');a=original[32:].astype(float);b=b[32:].astype(float)
            if not c['enabled']:baselines={c['baseline']:(a,b)}
            require(c['baseline'] in baselines,'Missing independent FX-off baseline');da,db=baselines[c['baseline']];wa,wb=a-da,b-db
            states=[verify(a,b,row['whole']),verify(wa,wb,row['wet']),verify(a[288000:],b[288000:],row['tail'])];screens+=3
            windows=[(at,kind,left,right) for at in [24000 if stage=='discovery' else 0,*c['hits']]
                     for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]]
            require(len(windows)==len(row['windows']),'Window count differs')
            for (at,kind,left,right),w in zip(windows,row['windows']):
                require((w['frame'],w['kind'],w['start'],w['stop'])==(at,kind,left,right),'Window boundaries differ')
                states.extend([verify(a[left:right],b[left:right],w['whole']),verify(wa[left:right],wb[left:right],w['wet'])]);screens+=2
            passed=all(states);require(row['passed']==passed,'Case pass differs');case_results.append(passed)
            sanitized=root/(c['name']+'.wav');process=subprocess.run([str(args.sanitized),str(session/'program.wav'),str(sanitized),str(plan)],capture_output=True,text=True,timeout=120,
                env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            require(process.returncode==0 and not process.stderr,'Sanitizer error: '+process.stderr);require(sha256(sanitized)==sha256(output),'Sanitized WAV differs')
            rows.append(dict(case=c['name'],stage=stage,passed=passed,comparison_sha256=sha256(path),receipt_sha256=provenance['receipt_sha256'],candidate_sha256=sha256(output),sanitizer_byte_identical=True))
            if first_source is None:first_source=session/'program.wav';first_plan=plan
            print('AUDITED',c['name'],'PASS' if passed else 'FAIL',flush=True)
        require(d['passed']==all(case_results),'Campaign pass differs')
    checks=guards(args,root,first_source,first_plan);frozen(args);require(binding==source_hashes(),'Candidate changed during audit')
    save_json(root/'verification.json',dict(kind='rmx220-live-engine-drums-fx-independent-audit' if native else 'rmx220-shared-drums-fx-independent-audit',backend=args.backend,live_engine=native,
        engine_symbols=symbols,evidence_verified=True,audio_passed=all(r['passed'] for r in rows),cases=rows,
        recomputed_stereo_screens=screens,source_sha256=binding,auditor_sha256=sha256(Path(__file__)),prediction_sha256=sha256(args.prediction),renderer_sha256=sha256(args.renderer),
        sanitized_sha256=sha256(args.sanitized),sanitizer_compile_commands_sha256=sha256(command_path),sanitizer_compile_commands=[c['command'] for c in selected],sanitizer_stderr_empty=True,
        acceptance=ACCEPTANCE,guards=checks,scope=('Actual live Engine common-clock routing. ' if native else 'Shared-clock research adapter only. ')
        +'Complete declared discovery/regression/fresh programs. The first five fresh campaigns and live-fresh each contain28 FX-on and28 independent FX-off programs; fresh-v6 has52 of each. Evidence integrity does not turn an audio failure into a pass. Moving controls, broader source/Isolator/Release interactions, other profiles/rates, wrappers and physical hardware require separate qualification.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('host','renderer','sanitized','prediction','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--prediction-stage',choices=['fresh','fresh-v2','fresh-v3','fresh-v4','fresh-v5','fresh-v6','live-fresh'],default='fresh')
    p.add_argument('--backend',choices=['shared','engine'],default='shared')
    p.add_argument('--former-prediction',type=Path)
    p.add_argument('--second-prediction',type=Path)
    p.add_argument('--third-prediction',type=Path)
    p.add_argument('--fourth-prediction',type=Path)
    p.add_argument('--fifth-prediction',type=Path)
    p.add_argument('--sixth-prediction',type=Path)
    p.add_argument('--dataset',nargs=3,action='append',required=True,metavar=('STAGE','SESSION','COMPARISON'))
    raise SystemExit(audit(p.parse_args()))


if __name__=='__main__':main()
