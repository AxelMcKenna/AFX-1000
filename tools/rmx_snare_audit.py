#!/usr/bin/env python3
"""Independently recompute snare scores, sanitizer parity and control guard checks."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import checked, require, recipe as discovery_recipe
from tools.rmx_factory_match import new_directory
from tools.rmx_snare_validate import ACCEPTANCE, frozen, recipe, source_hashes
from tools.rmx_snare import source_hashes as candidate_hashes



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


def observations(args):
    session=Path(next(d[1] for d in args.dataset if d[0]=='discovery'));normal=session/'drum-snare-base'
    a=json.loads((normal/'receipt.json').read_text());b=json.loads((args.debugger/'receipt.json').read_text())
    require(b['complete'] and b['role']=='reference' and b['plugin']['binary_files']==a['plugin']['binary_files'],'Debugger identity differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),
                       ('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(args.debugger/name)==b[field]==a[field],'Observed render differs: '+name)
    require(all(b[k]==a[k] for k in ('host_sha256','input_sha256','sample_rate','frames','maximum_block_size','bpm')),'Observed recipe differs')
    rows=[json.loads(s) for s in args.trace.read_text().splitlines()]
    stages={name:[r for r in rows if r['stage']==name] for name in ('pitch','source','tone','noise','output')}
    require(len(rows)==320 and all([r['subblock'] for r in v]==list(range(64)) for v in stages.values()),'Incomplete observed trace')
    require(all(r['custom']==[3,1,0] and r['pitch_controls']==[11,11,0] and r['pitch_raw']==128 for r in rows),'Observed controls differ')
    f=np.float32;envelopes={}
    for name,stage,decay in [('pitch','pitch',.035),('tone','source',.1875),('noise','output',.49)]:
        position=value=f(0);rising=True;falling=False;exact=0
        for r in stages[stage]:
            if rising:
                value=position;position=f(position+f(f(16)*f(f(1)/f(f(.001)*f(48000)))))
                if position>1:position=f(0);value=f(1);rising=False;falling=True
            if falling:
                value=f(value+f(f(16)*f(-f(1)/f(f(decay)*f(48000)))))
                if value<0:value=f(0);rising=falling=False
            observed=r['envelopes'][name]
            exact+=observed==dict(attack=float(f(.001)),decay=float(f(decay)),flags=[int(rising),int(falling)],value=float(value),position=float(position))
        require(exact==64,'Observed envelope replay differs: '+name);envelopes[name]=dict(blocks=64,exact_blocks=exact,decay=float(f(decay)))
    phases=[f(.25),f(.25)];exact=0
    for r in stages['source']:
        p=f(r['envelopes']['pitch']['value']);p=f(p*p);p=f(f(p*p)+f(1))
        frequencies=[f(f(168.2)*p),f(f(f(168.2)+f(84.8))*p)]
        for i,frequency in enumerate(frequencies):
            step=f(frequency*f(f(1)/f(48000)))
            for _ in range(16):
                phases[i]=f(phases[i]+step)
                if phases[i]>1:phases[i]=f(phases[i]-f(1))
        exact+=[float(v) for v in phases]==r['phase']
    require(exact==64,'Observed phase replay differs')
    return dict(audio_and_auxiliary_files_byte_identical=True,debugger_receipt_sha256=sha256(args.debugger/'receipt.json'),
                trace_sha256=sha256(args.trace),observer_sha256=sha256(args.observer),stages=5,subblocks_per_stage=64,
                envelopes=envelopes,oscillator_phase_replay=dict(blocks=64,exact_blocks=exact,uses_observed_pitch_envelope=True),
                static_noise_filter_coefficients={k:stages['source'][0]['filters'][k][4:9] for k in ('lowpass','lowpass1','highpass1')},
                scope='Read-only component replay; phase check uses observed pitch envelope. Independent full waveform renders provide separate autonomous-generator evidence.')

def audit(args):
    frozen(args);binding=source_hashes();root=new_directory(args.output);rows=[];scores=0
    compile_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(compile_path.read_text())
    generator_commands=[c['command'] for c in commands if c['file'].endswith(('Snare.cpp','snare_research_probe.cpp'))]
    require(len(generator_commands)==2 and all('-fsanitize=address,undefined' in c and '-ffp-contract=off' in c for c in generator_commands),'Missing sanitizer/float compile flags')
    recipes=dict(discovery=[c for c in discovery_recipe() if c['drum']=='snare'],fresh=recipe())
    require(sorted(d[0] for d in args.dataset)==['discovery','fresh'],'Requires exactly two complete datasets')
    for kind,session_text,comparison_text in args.dataset:
        session=Path(session_text);comparison=Path(comparison_text);report=json.loads(comparison.read_text());cases=recipes[kind]
        expected_sources=binding if kind=='fresh' else candidate_hashes()
        require(report['source_sha256']==expected_sources and report['renderer_sha256']==sha256(args.renderer)
                and report['acceptance']==ACCEPTANCE and report['passed'],'Comparison candidate/gates differ')
        require([r['case'] for r in report['cases']]==[c['name'] for c in cases],'Case set differs')
        if kind=='fresh':
            require(all(r['role']=='fresh_prediction_bound' for r in report['cases']) and report['prediction_sha256']==sha256(args.prediction)
                    and sha256(session/'predictions.json')==sha256(args.prediction)
                    and json.loads((session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Fresh prediction binding differs')
        else:require(report['kind']=='rmx220-snare-research-development','Regression role differs')
        for c,row in zip(cases,report['cases']):
            original,provenance=checked(session,c)
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
            rows.append(dict(case=c['name'],role=row.get('role','development_regression'),receipt_sha256=provenance['receipt_sha256'],
                             comparison_sha256=sha256(comparison),candidate_sha256=sha256(output),sanitizer_byte_identical=True))
            print('AUDITED',c['name'],flush=True)
    components=observations(args);frozen(args);require(binding==source_hashes(),'Candidate source changed during audit')
    save_json(root/'verification.json',dict(kind='rmx220-snare-cold-independent-audit',passed=True,cases=rows,
              recomputed_stereo_screens=scores,component_replay=components,source_sha256=binding,
              auditor_sha256=sha256(Path(__file__)),renderer_sha256=sha256(args.renderer),sanitized_sha256=sha256(args.sanitized),
              sanitizer_compile_commands_sha256=sha256(compile_path),sanitizer_compile_commands=generator_commands,sanitizer_stderr_empty=True,
              prediction_sha256=sha256(args.prediction),acceptance=ACCEPTANCE,
              scope='Six discovery plus eight new frozen prediction cases. Independent numeric score recomputation and all14 optimized/ASan/UBSan WAV byte parity. Neutral factory48k snare research only; no broader drum, live Engine or hardware claim.'))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('renderer','sanitized','host','prediction','output','debugger','trace','observer'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--dataset',nargs=3,action='append',required=True,metavar=('KIND','SESSION','COMPARISON'))
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
