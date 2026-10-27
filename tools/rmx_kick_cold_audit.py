#!/usr/bin/env python3
"""Independently recompute kick scores, sanitizer parity and control guard checks."""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import checked, require, recipe as discovery_recipe
from tools.rmx_factory_match import new_directory
from tools.rmx_kick_cold import ACCEPTANCE, frozen, recipe, source_hashes
from tools.rmx_kick_validate import recipe as first_recipe


def verify_score(a,b,stored):
    require(len(stored['channels'])==2,'Missing score channel')
    for channel,c in enumerate(stored['channels']):
        x=a[:,channel].astype(np.float64);delta=x-b[:,channel].astype(np.float64)
        energy=float(np.sum(x*x));error=float(np.sum(delta*delta));absolute=math.sqrt(error/len(x))
        relative=math.sqrt(error/energy) if energy>1e-20 else None
        require(math.isclose(absolute,c['absolute_error_rms'],rel_tol=1e-12,abs_tol=1e-15),'Absolute score differs')
        require((relative is None and c['relative_rms_error'] is None) or
                (relative is not None and math.isclose(relative,c['relative_rms_error'],rel_tol=1e-12,abs_tol=1e-15)),'Relative score differs')
        passed=relative<=.01 if relative is not None else absolute<=1e-8
        require(c['passed']==passed and passed,'Independent channel score fails')
    require(stored['passed'],'Stored screen failed')


def rejected(call,message):
    try:call()
    except ValueError as error:
        require(str(error)==message,'Unexpected guard rejection: '+str(error));return
    raise ValueError('Guard accepted modified evidence')


def guards(args,session):
    case=recipe()[0]
    rejected(lambda:checked(session,case),'Drum immediate readback differs')
    with tempfile.TemporaryDirectory(prefix='rmx-kick-controls-') as temp:
        root=Path(temp);folder=root/case['name'];shutil.copytree(session/case['name'],folder)
        for name in ('inventory.json','matrix.json'):shutil.copyfile(session/name,root/name)
        original_log=json.loads((folder/'parameter-log.json').read_text())
        original_receipt=json.loads((folder/'receipt.json').read_text())
        original_matrix=json.loads((root/'matrix.json').read_text())
        # Rebind hashes so these exercise semantic readbacks, beyond hash checks.
        for frame,value in [(0,1),(83,0)]:
            log=copy.deepcopy(original_log)
            entry=next(e for e in log['entries'] if e['frame']==frame and e['name']=='KickButton')
            entry['immediate_readback']=value;(folder/'parameter-log.json').write_text(json.dumps(log))
            receipt=copy.deepcopy(original_receipt);receipt['parameter_log_sha256']=sha256(folder/'parameter-log.json');(folder/'receipt.json').write_text(json.dumps(receipt))
            matrix=copy.deepcopy(original_matrix);next(c for c in matrix['cases'] if c['name']==case['name'])['receipt_sha256']=sha256(folder/'receipt.json');(root/'matrix.json').write_text(json.dumps(matrix))
            rejected(lambda:checked(root,case,cold_kick=True),'Drum immediate readback differs')
        # Prediction changes must fail before any render or capture is accepted.
        prediction=json.loads(args.prediction.read_text());prediction['cases'][0]['hits'][1]+=1
        altered=root/'prediction.json';save_json(altered,prediction)
        modified=copy.copy(args);modified.prediction=altered
        rejected(lambda:frozen(modified),'Frozen cold kick prediction differs')
    return dict(original_strict_contract_rejects_frame_zero=True,unexpected_frame_zero_acceptance_rejected=True,
                unexpected_later_rejection_rejected=True,modified_prediction_rejected=True)


def audit(args):
    frozen(args);binding=source_hashes();root=new_directory(args.output);rows=[];scores=0
    compile_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(compile_path.read_text())
    generator_commands=[c['command'] for c in commands if c['file'].endswith(('KickResearch.cpp','kick_research_probe.cpp'))]
    require(len(generator_commands)==2 and all('-fsanitize=address,undefined' in c and '-ffp-contract=off' in c for c in generator_commands),'Missing sanitizer/float compile flags')
    recipes=dict(discovery=[c for c in discovery_recipe() if c['drum']=='kick'],first=first_recipe(),fresh=recipe())
    require(sorted(d[0] for d in args.dataset)==['discovery','first','fresh'],'Requires exactly three complete datasets')
    fresh_session=None
    for kind,session_text,comparison_text in args.dataset:
        session=Path(session_text);comparison=Path(comparison_text);report=json.loads(comparison.read_text());cases=recipes[kind]
        require(report['source_sha256']==binding and report['renderer_sha256']==sha256(args.renderer)
                and report['acceptance']==ACCEPTANCE and report['passed'],'Comparison candidate/gates differ')
        require([r['case'] for r in report['cases']]==[c['name'] for c in cases],'Case set differs')
        if kind=='fresh':
            fresh_session=session
            require(report['role']=='fresh_prediction_bound' and report['prediction_sha256']==sha256(args.prediction)
                    and sha256(session/'predictions.json')==sha256(args.prediction)
                    and json.loads((session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Fresh prediction binding differs')
        else:require(report['role']=='development_regression','Regression role differs')
        for c,row in zip(cases,report['cases']):
            original,provenance=checked(session,c,cold_kick=True)
            require(all(row[k]==v for k,v in provenance.items()),'Original provenance differs')
            receipt=json.loads((session/c['name']/'receipt.json').read_text())
            require(receipt['host_sha256']==sha256(args.host),'Reference host differs')
            for binary in receipt['plugin']['binary_files']:
                require(sha256(Path(receipt['plugin']['bundle'])/binary['path'])==binary['sha256'],'Original plug-in differs')
            folder=comparison.parent;output=folder/(c['name']+'.wav');dry=folder/(c['name']+'-dry.wav');plan=folder/(c['name']+'.tsv')
            require(sha256(output)==row['candidate_sha256'] and sha256(dry)==row['dry_trace_sha256']
                    and sha256(plan)==row['schedule_sha256'],'Candidate artifact differs')
            rate,candidate=float_wav(output);dry_rate,dry_audio=float_wav(dry)
            require(rate==dry_rate==48000 and candidate.shape==original.shape==dry_audio.shape and not np.any(dry_audio),'Candidate extent/dry differs')
            a,b=original[32:],candidate[32:];verify_score(a,b,row['whole']);scores+=1
            windows=[(label,at,left,min(len(a),right)) for at in c['hits']
                     for label,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)] if min(len(a),right)>left]
            require(len(windows)==len(row['windows']),'Window count differs')
            for (label,at,left,right),w in zip(windows,row['windows']):
                require((w['kind'],w['frame'],w['start'],w['stop'])==(label,at,left,right),'Window boundaries differ')
                verify_score(a[left:right],b[left:right],w['score']);scores+=1
            require(row['passed'],'Stored case failed')
            sanitized=root/(c['name']+'.wav');sanitized_dry=root/(c['name']+'-dry.wav')
            process=subprocess.run([str(p) for p in [args.sanitized,session/'silence.wav',sanitized,plan,sanitized_dry]],
                        capture_output=True,text=True,timeout=120,env=os.environ|{'ASAN_OPTIONS':'halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
            require(process.returncode==0 and not process.stderr,'Sanitizer reported an error: '+process.stderr)
            require(sha256(sanitized)==sha256(output) and sha256(sanitized_dry)==sha256(dry),'Optimized/sanitized bytes differ')
            rows.append(dict(case=c['name'],role=row['role'],receipt_sha256=provenance['receipt_sha256'],
                             comparison_sha256=sha256(comparison),candidate_sha256=sha256(output),sanitizer_byte_identical=True))
            print('AUDITED',c['name'],flush=True)
    checks=guards(args,fresh_session);frozen(args);require(binding==source_hashes(),'Candidate source changed during audit')
    save_json(root/'verification.json',dict(kind='rmx220-kick-cold-independent-audit',passed=True,cases=rows,
              recomputed_stereo_screens=scores,control_and_prediction_guards=checks,source_sha256=binding,
              auditor_sha256=sha256(Path(__file__)),renderer_sha256=sha256(args.renderer),sanitized_sha256=sha256(args.sanitized),
              sanitizer_compile_commands_sha256=sha256(compile_path),sanitizer_compile_commands=generator_commands,sanitizer_stderr_empty=True,
              prediction_sha256=sha256(args.prediction),acceptance=ACCEPTANCE,
              scope='Six discovery plus eight former holdout regressions plus eight new frozen prediction cases. Independent numeric score recomputation and all22 optimized/ASan/UBSan WAV byte parity. Neutral factory48k kick research only; no broader drum, live Engine or hardware claim.'))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('renderer','sanitized','host','prediction','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--dataset',nargs=3,action='append',required=True,metavar=('KIND','SESSION','COMPARISON'))
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
