#!/usr/bin/env python3
"""Independently audit drum model recordings, scores, sanitizers and scalar traces."""
import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import checked, recipe as discovery_recipe, require
from tools.rmx_factory_match import new_directory
from tools.rmx_snare_audit import verify_score


def observed_capture(args,normal):
    a=json.loads((normal/'receipt.json').read_text());b=json.loads((args.debugger/'receipt.json').read_text())
    require(b['complete'] and b['role']=='reference' and b['plugin']['binary_files']==a['plugin']['binary_files'],'Debugger identity differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),
                       ('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(args.debugger/name)==b[field]==a[field],'Observed render differs: '+name)
    require(all(b[k]==a[k] for k in ('host_sha256','input_sha256','sample_rate','frames','maximum_block_size','bpm')),'Observed recipe differs')
    return dict(audio_and_auxiliary_files_byte_identical=True,debugger_receipt_sha256=sha256(args.debugger/'receipt.json'),
                trace_sha256=sha256(args.trace),observer_sha256=sha256(args.observer))


def envelope_replay(rows,name,attack,decay):
    f=np.float32;position=value=f(0);rising=True;falling=False;exact=0
    for row in rows:
        if rising:
            value=position;position=f(position+f(f(16)*f(f(1)/f(f(attack)*f(48000)))))
            if position>1:position=f(0);value=f(1);rising=False;falling=True
        if falling:
            value=f(value+f(f(16)*f(-f(1)/f(f(decay)*f(48000)))))
            if value<0:value=f(0);rising=falling=False
        exact+=row['envelopes'][name]==dict(attack=float(f(attack)),decay=float(f(decay)),flags=[int(rising),int(falling)],value=float(value),position=float(position))
    require(exact==len(rows),'Observed envelope replay differs: '+name)
    return dict(blocks=len(rows),exact_blocks=exact,attack=float(f(attack)),decay=float(f(decay)))


def clap_components(args,normal):
    provenance=observed_capture(args,normal);rows=[json.loads(s) for s in args.trace.read_text().splitlines()]
    stages={name:[r for r in rows if r['stage']==name] for name in ('source','filtered','envelope','output')}
    require(len(rows)==512 and all([r['subblock'] for r in v]==list(range(128)) for v in stages.values()),'Incomplete clap trace')
    filters=rows[0]['filters']
    require(all(r['custom']==[3,1,0] and r['pitch_controls']==[11,11,0] and r['pitch_raw']==128 and r['filters']==filters for r in rows),'Observed controls/filters differ')
    envelopes={name:envelope_replay(stages['envelope'],name,.016,decay) for name,decay in [('noise',.24),('tail',1.25)]}
    f=np.float32;phase=f(1);step=f(f(91)*f(f(1)/f(48000)));exact=0
    for count,r in enumerate(stages['source']):
        for _ in range(16):
            phase=f(phase-step)
            if phase<0:phase=f(1)
        exact+=float(phase)==r['saw_phase']
        for name in ('source','filtered','envelope','output'):
            other=stages[name][count]
            require(other['saw_phase']==r['saw_phase'] and other['elapsed_frames']==16*(count+(name in ('envelope','output'))),'Observed clock differs')
    require(exact==128,'Observed saw phase replay differs')
    return provenance|dict(stages=4,subblocks_per_stage=128,envelopes=envelopes,filters=filters,
                            saw_phase_replay=dict(blocks=128,exact_blocks=exact),elapsed_counter_exact=True,
                            scope='Read-only scalar replay; autonomous complete waveform checks are separate. No original audio/buffers or instructions are distributed.')


def audit(args):
    campaign=importlib.import_module('tools.rmx_'+args.drum+'_validate');candidate=importlib.import_module('tools.rmx_'+args.drum)
    campaign.frozen(args);binding=campaign.source_hashes();root=new_directory(args.output);rows=[];scores=0
    compile_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(compile_path.read_text())
    files=(args.drum.capitalize()+'Research.cpp',args.drum+'_research_probe.cpp')
    generator_commands=[c['command'] for c in commands if c['file'].endswith(files)]
    require(len(generator_commands)==2 and all('-fsanitize=address,undefined' in c and '-ffp-contract=off' in c for c in generator_commands),'Missing sanitizer/float compile flags')
    recipes=dict(discovery=[c for c in discovery_recipe() if c['drum']==args.drum],fresh=campaign.recipe())
    require(sorted(d[0] for d in args.dataset)==['discovery','fresh'],'Requires exactly two complete datasets')
    normal=None
    for kind,session_text,comparison_text in args.dataset:
        session=Path(session_text);comparison=Path(comparison_text);report=json.loads(comparison.read_text());cases=recipes[kind]
        expected_sources=binding if kind=='fresh' else candidate.source_hashes()
        require(report['source_sha256']==expected_sources and report['renderer_sha256']==sha256(args.renderer)
                and report['acceptance']==campaign.ACCEPTANCE and report['passed'],'Comparison candidate/gates differ')
        require([r['case'] for r in report['cases']]==[c['name'] for c in cases],'Case set differs')
        if kind=='fresh':
            require(all(r['role']=='fresh_prediction_bound' for r in report['cases']) and report['prediction_sha256']==sha256(args.prediction)
                    and sha256(session/'predictions.json')==sha256(args.prediction)
                    and json.loads((session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Fresh prediction binding differs')
        else:
            require(report['kind']=='rmx220-'+args.drum+'-research-development','Regression role differs');normal=session/('drum-'+args.drum+'-base')
        for c,row in zip(cases,report['cases']):
            original,provenance=checked(session,c);require(all(row[k]==v for k,v in provenance.items()),'Original provenance differs')
            receipt=json.loads((session/c['name']/'receipt.json').read_text());require(receipt['host_sha256']==sha256(args.host),'Reference host differs')
            for binary in receipt['plugin']['binary_files']:
                require(sha256(Path(receipt['plugin']['bundle'])/binary['path'])==binary['sha256'],'Original plug-in differs')
            folder=comparison.parent;output=folder/(c['name']+'.wav');dry=folder/(c['name']+'-dry.wav');plan=folder/(c['name']+'.tsv')
            require(sha256(output)==row['candidate_sha256'] and sha256(dry)==row['dry_trace_sha256'] and sha256(plan)==row['schedule_sha256'],'Candidate artifact differs')
            expected_plan='RMX_DRUM 1\n'+f'{list(("kick","snare","clap","hat")).index(args.drum)} 128 128 {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits'])
            require(plan.read_text()==expected_plan,'Candidate schedule differs')
            rate,audio=float_wav(output);dry_rate,dry_audio=float_wav(dry)
            require(rate==dry_rate==48000 and audio.shape==original.shape==dry_audio.shape and not np.any(dry_audio),'Candidate extent/dry differs')
            a,b=original[32:],audio[32:];verify_score(a,b,row['whole']);scores+=1
            windows=[(label,at,left,min(len(a),right)) for at in c['hits']
                     for label,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)] if min(len(a),right)>left]
            require(len(windows)==len(row['windows']),'Window count differs')
            for (label,at,left,right),w in zip(windows,row['windows']):
                require((w['kind'],w['frame'],w['start'],w['stop'])==(label,at,left,right),'Window boundaries differ')
                verify_score(a[left:right],b[left:right],w['score']);scores+=1
            require(row['passed'],'Stored case failed');sanitized=root/(c['name']+'.wav');sanitized_dry=root/(c['name']+'-dry.wav')
            process=subprocess.run([str(p) for p in [args.sanitized,session/'silence.wav',sanitized,plan,sanitized_dry]],capture_output=True,text=True,
                    timeout=120,env=os.environ|{'ASAN_OPTIONS':'halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
            require(process.returncode==0 and not process.stderr,'Sanitizer reported an error: '+process.stderr)
            require(sha256(sanitized)==sha256(output) and sha256(sanitized_dry)==sha256(dry),'Optimized/sanitized bytes differ')
            rows.append(dict(case=c['name'],role=row.get('role','development_regression'),receipt_sha256=provenance['receipt_sha256'],
                             comparison_sha256=sha256(comparison),candidate_sha256=sha256(output),sanitizer_byte_identical=True))
            print('AUDITED',c['name'],flush=True)
    components=clap_components(args,normal);campaign.frozen(args);require(binding==campaign.source_hashes(),'Candidate source changed during audit')
    save_json(root/'verification.json',dict(kind='rmx220-'+args.drum+'-independent-audit',passed=True,cases=rows,recomputed_stereo_screens=scores,
              component_replay=components,source_sha256=binding,auditor_sha256=sha256(Path(__file__)),score_helper_sha256=sha256(Path('tools/rmx_snare_audit.py')),
              renderer_sha256=sha256(args.renderer),sanitized_sha256=sha256(args.sanitized),sanitizer_compile_commands_sha256=sha256(compile_path),
              sanitizer_compile_commands=generator_commands,sanitizer_stderr_empty=True,prediction_sha256=sha256(args.prediction),acceptance=campaign.ACCEPTANCE,
              scope='Six discovery plus eight new frozen prediction programs; complete score recomputation and optimized/ASan/UBSan byte parity. Neutral factory48k research only; live Engine, broader controls and hardware remain unqualified.'))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--drum',choices=['clap'],required=True)
    for name in ('renderer','sanitized','host','prediction','output','debugger','trace','observer'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--dataset',nargs=3,action='append',required=True,metavar=('KIND','SESSION','COMPARISON'))
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
