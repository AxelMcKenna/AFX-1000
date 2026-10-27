#!/usr/bin/env python3
"""Independently recompute live drum gesture gates and sanitizer output parity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from tools.reference_audio import save_json,sha256
from tools.noise_statistics import float_wav
from tools.rmx_drums import FRAMES,checked,require
from tools.rmx_drums_motion import ACCEPTANCE,original_plan,payload,recipe,source_hashes
from tools.rmx_factory_match import new_directory


def measure(a,b):
    result=[]
    for i,name in enumerate(['left','right']):
        ref=a[:,i].astype(np.float64);err=b[:,i].astype(np.float64)-ref
        energy=float(np.sum(ref*ref));absolute=float(np.sqrt(np.sum(err*err)/len(err)))
        relative=float(np.sqrt(np.sum(err*err)/energy)) if energy>1e-20 else None
        result.append(dict(channel=name,relative_rms_error=relative,absolute_error_rms=absolute,
          passed=relative<=.01 if relative is not None else absolute<=1e-8))
    return dict(passed=all(c['passed'] for c in result),channels=result)


def same_score(a,b):
    require(a['passed']==b['passed'] and len(a['channels'])==len(b['channels'])==2,'Gate result differs')
    for x,y in zip(a['channels'],b['channels']):
        require(x['channel']==y['channel'] and x['passed']==y['passed'],'Channel result differs')
        for key in ['absolute_error_rms','relative_rms_error']:
            require((x[key] is None and y[key] is None) or (x[key] is not None and y[key] is not None and abs(x[key]-y[key])<=1e-13*max(1,abs(x[key]))),'Independent score differs')


def verify(args):
    script=sha256(Path(__file__));binding=source_hashes();args.stage='fresh'
    require(json.loads(args.prediction.read_text())==payload(args),'Frozen prediction differs')
    datasets=[('discovery',*args.discovery),('fresh',*args.fresh)];reports=[]
    for stage,session,path in datasets:
        d=json.loads(path.read_text());require(d['source_sha256']==binding and d['renderer_sha256']==sha256(args.renderer) and d['sanitized_sha256']==sha256(args.sanitized) and d['acceptance']==ACCEPTANCE and d['stage']==stage,'Comparison source/binary/gates differ')
        if stage=='fresh':require(d['prediction_sha256']==sha256(args.prediction)==sha256(session/'predictions.json'),'Fresh prediction copy differs')
        require([r['case'] for r in d['cases']]==[c['name'] for c in recipe(stage)],'Recipe differs');reports.append(d)
    commands_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(commands_path.read_text())
    suffixes=('/Engine.cpp','/Scene.cpp','/ReverbUp.cpp','/ReverbDown.cpp','/drums/Kick.cpp','/drums/Snare.cpp','/drums/Clap.cpp','/drums/Hat.cpp','/Wav.cpp','/drum_motion_probe.cpp')
    units=[c for c in commands if c['file'].endswith(suffixes)]
    require(len(units)==10 and all('-fsanitize=address,undefined' in c['command'] for c in units),'Missing sanitized native units')
    require(all('-ffp-contract=off' in c['command'] for c in units if '/drums/' in c['file'] or '/Reverb' in c['file']),'Identified float flags missing')
    symbols={}
    for binary in [args.renderer,args.sanitized]:
        text=subprocess.check_output(['nm','-C',str(binary)],text=True);require('rmx::Engine::process(' in text,'Fixture lacks actual Engine')
        symbols[str(binary)]=hashlib.sha256(text.encode()).hexdigest()
    root=new_directory(args.output);rows=[];screens=0;guard=None
    for (stage,session,path),d in zip(datasets,reports):
        for c,row in zip(recipe(stage),d['cases']):
            a,provenance=checked(session,c,plan_builder=original_plan);require(all(row[k]==v for k,v in provenance.items()),'Original comparison provenance differs')
            receipt=json.loads((session/c['name']/'receipt.json').read_text());require(receipt['host_sha256']==sha256(args.host),'Original host changed')
            for member in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/member['path'])==member['sha256'],'Original binary changed')
            out=path.parent/(c['name']+'.wav');dry=path.parent/(c['name']+'-dry.wav');plan=path.parent/(c['name']+'.tsv')
            expected=f'RMX_DRUM_MOTION 1\n{c["level"]} {c["pitch"]} {c["block"]}\n'+''.join(f'{e["frame"]} {e["type"]} {e["value"]}\n' for e in c['changes'])
            require(sha256(out)==row['candidate_sha256'] and sha256(dry)==row['dry_sha256'] and sha256(plan)==row['schedule_sha256'] and plan.read_text()==expected,'Candidate artifact changed')
            rate,b=float_wav(out);drate,dry_audio=float_wav(dry)
            require(rate==drate==48000 and a.shape==b.shape==dry_audio.shape==(FRAMES,2) and not np.any(dry_audio),'Candidate extent/rate/dry differs')
            a,b=a[32:],b[32:];whole=measure(a,b);same_score(whole,row['whole']);screens+=1
            expected_windows=[]
            for at in c['hits']:
                for kind,start,stop in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                    stop=min(len(a),stop)
                    if stop>start:expected_windows.append(dict(kind=kind,frame=at,start=start,stop=stop))
            for e in c['changes']:
                if e['type'] in ('L','P'):
                    at=e['frame'];expected_windows.append(dict(kind='level-change' if e['type']=='L' else 'pitch-change',frame=at,start=at,stop=min(len(a),at+1024)))
            require([{k:w[k] for k in ['kind','frame','start','stop']} for w in row['windows']]==expected_windows,'Window coverage differs')
            passes=[whole['passed']]
            for w in row['windows']:
                score=measure(a[w['start']:w['stop']],b[w['start']:w['stop']]);same_score(score,w['score']);screens+=1;passes.append(score['passed'])
            require(row['passed']==all(passes),'Program verdict differs')
            san=root/(c['name']+'.wav');san_dry=root/(c['name']+'-dry.wav')
            r=subprocess.run([str(args.sanitized),str(session/'silence.wav'),str(san),str(plan),str(san_dry)],capture_output=True,text=True,timeout=120,
              env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            require(r.returncode==0 and not r.stderr and sha256(san)==sha256(out) and sha256(san_dry)==sha256(dry),'Independent sanitizer replay differs')
            if guard is None:
                gain=measure(a,b.astype(float)*1.1);shift=measure(a[1:],b[:-1]);require(not gain['passed'] and not shift['passed'],'Invalid audio guard was accepted')
                alias=root/'alias.wav';bad=subprocess.run([str(args.renderer),str(session/'silence.wav'),str(alias),str(plan),str(alias)],capture_output=True,text=True)
                require(bad.returncode!=0 and not alias.exists(),'Aliased outputs were accepted')
                guard=dict(ten_percent_gain_rejected=True,one_frame_shift_rejected=True,aliased_output_rejected_without_write=True,gain_result=gain,shift_result=shift)
            rows.append(dict(stage=stage,case=c['name'],passed=all(passes),receipt_sha256=provenance['receipt_sha256'],candidate_sha256=sha256(out),comparison_sha256=sha256(path),sanitizer_byte_identical=True))
            print('VERIFIED',stage,c['name'],flush=True)
    require(binding==source_hashes() and script==sha256(Path(__file__)),'Audit source changed')
    save_json(root/'verification.json',dict(kind='rmx220-drums-motion-independent-audit',evidence_verified=True,audio_passed=all(r['passed'] for r in rows),programs=len(rows),stereo_screens=screens,cases=rows,
      source_sha256=binding,auditor_sha256=script,renderer_sha256={str(p):sha256(p) for p in [args.renderer,args.sanitized]},prediction_sha256=sha256(args.prediction),
      sanitizer_compile_commands_sha256=sha256(commands_path),sanitizer_compile_commands=[c['command'] for c in units],engine_symbol_sha256=symbols,sanitizer_stderr_empty=True,guards=guard,acceptance=ACCEPTANCE,
      scope='28 discovery and16 frozen fresh live Engine drum gesture programs at48k/default profiles. Independently recomputed whole/event/attack/body/decay screens and complete sanitized audio/dry byte parity. No AU/VST3 motion, custom profiles, FX during gestures, rolls, other rates or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['prediction','renderer','sanitized','host','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--discovery',nargs=2,type=Path,required=True);p.add_argument('--fresh',nargs=2,type=Path,required=True)
    raise SystemExit(verify(p.parse_args()))


if __name__=='__main__':main()
