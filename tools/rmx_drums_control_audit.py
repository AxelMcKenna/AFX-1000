#!/usr/bin/env python3
"""Independently recompute all drum control scores and sanitizer audio parity."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import DRUMS, checked, require
from tools.rmx_drums_control_match import ACCEPTANCE, SETS, frozen, recipe, regression_cases, source_hashes
from tools.rmx_factory_match import new_directory
from tools.rmx_filter_match import screen
from tools.rmx_snare_audit import verify_score


def rejection(call,message):
    try:call()
    except ValueError as error:require(str(error)==message,'Unexpected rejection: '+str(error));return
    raise ValueError('Modified evidence was accepted')


def guards(args,neutral,hot,plan,source,root):
    with tempfile.TemporaryDirectory(prefix='rmx-drums-frozen-') as temp:
        for field in ('case','gate'):
            prediction=json.loads(args.prediction.read_text())
            if field=='case':prediction['cases'][1]['level']+=1
            else:prediction['acceptance']['relative_rms_error_limit']=.02
            path=Path(temp)/(field+'.json');save_json(path,prediction);changed=copy.copy(args);changed.prediction=path
            rejection(lambda:frozen(changed),'Frozen drum control prediction differs')
    same=root/'invalid-same-output.wav'
    result=subprocess.run([str(args.renderer),str(source),str(same),str(plan),str(same)],capture_output=True,text=True,timeout=120)
    require(result.returncode!=0 and not same.exists() and 'Outputs must be distinct and new' in result.stderr,'Same-output guard failed')
    a=neutral[32:].astype(float)
    shifted=np.zeros_like(a);shifted[1:]=a[:-1]
    require(not screen(a,shifted)['passed'] and not screen(a,a*1.1)['passed'],'Waveform sensitivity guard failed')
    clipping=screen(hot[32:].astype(float),np.clip(hot[32:].astype(float),-1,1))
    require(not clipping['passed'],'High-level clipping was not detected')
    return dict(modified_case_rejected=True,relaxed_gate_rejected=True,aliased_output_rejected_without_writes=True,
                one_frame_shift_rejected=True,ten_percent_gain_error_rejected=True,original_above_unity_clipping_rejected=clipping)


def audit(args):
    frozen(args);binding=source_hashes();root=new_directory(args.output);rows=[];screens=0;neutral=hot=first_plan=first_source=None
    require(sorted(d[0] for d in args.dataset)==sorted([*SETS,'fresh']),'Requires exactly nine complete datasets')
    commands_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(commands_path.read_text())
    files=('drums_control_probe.cpp','KickResearch.cpp','SnareResearch.cpp','ClapResearch.cpp','HatResearch.cpp')
    commands=[c['command'] for c in commands if c['file'].endswith(files) and 'rmx_drums_control_probe.dir' in c['command']]
    require(len(commands)==5 and all('-fsanitize=address,undefined' in c and '-ffp-contract=off' in c for c in commands),'Missing sanitizer/float compile flags')
    for name,session_text,comparison_text in args.dataset:
        session=Path(session_text);comparison=Path(comparison_text);report=json.loads(comparison.read_text())
        cases=recipe() if name=='fresh' else regression_cases(name);role='fresh_prediction_bound' if name=='fresh' else 'development_regression'
        require(report['kind']=='rmx220-drums-controls-comparison' and report['passed'] and report['role']==role
                and report['source_sha256']==binding and report['renderer_sha256']==sha256(args.renderer) and report['acceptance']==ACCEPTANCE,'Comparison candidate/gates differ')
        require([c['name'] for c in cases]==[r['case'] for r in report['cases']],'Case set differs')
        if name=='fresh':
            require(report['prediction_sha256']==sha256(args.prediction) and sha256(session/'predictions.json')==sha256(args.prediction)
                    and json.loads((session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Fresh prediction binding differs')
        for c,row in zip(cases,report['cases']):
            original,provenance=checked(session,c,cold_kick=c['drum']=='kick')
            require(all(row[k]==v for k,v in provenance.items()) and row['drum']==c['drum'] and row['level']==c['level'] and row['pitch']==c['pitch'] and row['role']==role,'Case provenance/controls differ')
            receipt=json.loads((session/c['name']/'receipt.json').read_text());require(receipt['host_sha256']==sha256(args.host),'Original host differs')
            for binary in receipt['plugin']['binary_files']:
                require(sha256(Path(receipt['plugin']['bundle'])/binary['path'])==binary['sha256'],'Original binary differs')
            folder=comparison.parent;output=folder/(c['name']+'.wav');dry=folder/(c['name']+'-dry.wav');plan=folder/(c['name']+'.tsv')
            require(sha256(output)==row['candidate_sha256'] and sha256(dry)==row['dry_trace_sha256'] and sha256(plan)==row['schedule_sha256'],'Candidate artifact differs')
            expected='RMX_DRUM 1\n'+f'{list(DRUMS).index(c["drum"])} {c["level"]} {c["pitch"]} {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits'])
            require(plan.read_text()==expected,'Candidate schedule differs')
            rate,candidate=float_wav(output);dry_rate,dry_audio=float_wav(dry)
            require(rate==dry_rate==48000 and candidate.shape==original.shape==dry_audio.shape and not np.any(dry_audio),'Candidate extent/dry differs')
            a,b=original[32:],candidate[32:];verify_score(a,b,row['whole']);screens+=1
            windows=[(kind,at,left,min(len(a),right)) for at in c['hits']
                     for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)] if min(len(a),right)>left]
            require(len(windows)==len(row['windows']),'Window count differs')
            for (kind,at,left,right),w in zip(windows,row['windows']):
                require((w['kind'],w['frame'],w['start'],w['stop'])==(kind,at,left,right),'Window boundaries differ')
                verify_score(a[left:right],b[left:right],w['score']);screens+=1
            require(row['passed'],'Stored case failed')
            sanitized=root/(c['name']+'.wav');sanitized_dry=root/(c['name']+'-dry.wav')
            process=subprocess.run([str(p) for p in [args.sanitized,session/'silence.wav',sanitized,plan,sanitized_dry]],capture_output=True,text=True,
                        timeout=120,env=os.environ|{'ASAN_OPTIONS':'halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
            require(process.returncode==0 and not process.stderr,'Sanitizer reported an error: '+process.stderr)
            require(sha256(sanitized)==sha256(output) and sha256(sanitized_dry)==sha256(dry),'Optimized/sanitized bytes differ')
            if c['name']=='drum-hat-base':neutral=original
            if c['name']=='controls-kick-level-255':hot=original
            if first_plan is None:first_plan=plan;first_source=session/'silence.wav'
            rows.append(dict(case=c['name'],role=role,comparison_sha256=sha256(comparison),receipt_sha256=provenance['receipt_sha256'],candidate_sha256=sha256(output),sanitizer_byte_identical=True))
            print('AUDITED',c['name'],flush=True)
    require(neutral is not None and hot is not None,'Missing negative-control source')
    checks=guards(args,neutral,hot,first_plan,first_source,root);frozen(args);require(binding==source_hashes(),'Candidate source changed during audit')
    save_json(root/'verification.json',dict(kind='rmx220-drums-controls-independent-audit',passed=True,cases=rows,recomputed_stereo_screens=screens,
        source_sha256=binding,auditor_sha256=sha256(Path(__file__)),score_helper_sha256=sha256(Path('tools/rmx_snare_audit.py')),
        renderer_sha256=sha256(args.renderer),sanitized_sha256=sha256(args.sanitized),sanitizer_compile_commands_sha256=sha256(commands_path),
        sanitizer_compile_commands=commands,sanitizer_stderr_empty=True,prediction_sha256=sha256(args.prediction),acceptance=ACCEPTANCE,guards=checks,
        scope='76 static control discovery regressions,64 previous neutral regressions,32 former failed-prediction regressions,32 frozen fresh static-control predictions. Complete score recomputation and all204 optimized/ASan/UBSan audio byte parity. No automation, alternate profiles, Engine or hardware claim.'))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('renderer','sanitized','host','prediction','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--dataset',nargs=3,action='append',required=True,metavar=('NAME','SESSION','COMPARISON'))
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
