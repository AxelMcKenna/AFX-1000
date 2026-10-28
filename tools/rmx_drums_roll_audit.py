#!/usr/bin/env python3
"""Independently verify roll windows, original provenance and sanitizer parity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import FRAMES,require
from tools.rmx_drums_motion_audit import measure,same_score
from tools.rmx_drums_roll import original,payload,recipe,schedule,source_hashes
from tools.rmx_factory_match import new_directory
from tools.rmx_drums_strip_motion import recipe as strip_recipe

GATES=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,
           reference_offset_frames=32,candidate_offset_frames=32,gain_fit=False,alignment_search=False)


def windows(c,stage):
    if stage=='discovery':
        result=[('selection',9600,129600),('touch-attack',96000,96256),('roll-stop',336000,337024),('tail',336000,FRAMES-32)]
        result += [('roll-window',at,at+24000) for at in range(96000,336000,24000)]
    else:
        touches=[e for e in c['changes'] if e['type']=='T'];last=max(e['frame'] for e in touches)
        result=[('selection',at,at+120000) for at in c['hits']]+[('tail',last,FRAMES-32)]
        result += [('touch-attack' if e['value'] else 'roll-stop',e['frame'],e['frame']+(256 if e['value'] else 1024)) for e in touches]
        for on,off in zip(touches[::2],touches[1::2]):
            result += [('roll-window',at,min(at+24000,off['frame'])) for at in range(on['frame'],off['frame'],24000)]
    result += [('strip-change',e['frame'],e['frame']+24000) for e in c['changes'] if e['type']=='X' and e['frame']>1]
    return [dict(kind=kind,start=start,stop=min(stop,FRAMES-32)) for kind,start,stop in result]


def verify(args):
    binding=source_hashes();script=sha256(Path(__file__));binaries={str(p):sha256(p) for p in [args.renderer,args.sanitized]}
    expected=payload(SimpleNamespace(stage='fresh-v4',renderer=args.renderer))
    require(json.loads(args.prediction.read_text())==expected,'Fresh frozen prediction differs')
    require(expected['acceptance']==GATES,'Acceptance contract changed')
    commands_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(commands_path.read_text())
    suffixes=('/Engine.cpp','/Scene.cpp','/ReverbUp.cpp','/ReverbDown.cpp','/drums/Kick.cpp','/drums/Snare.cpp','/drums/Clap.cpp','/drums/Hat.cpp','/Wav.cpp','/drum_roll_probe.cpp')
    units=[c for c in commands if c['file'].endswith(suffixes)]
    require(len(units)==10 and all('-fsanitize=address,undefined' in c['command'] for c in units),'Missing instrumented Engine units')
    require(all('-ffp-contract=off' in c['command'] for c in units if '/drums/' in c['file'] or '/Reverb' in c['file']),'Identified float flags changed')
    symbols={}
    for binary in [args.renderer,args.sanitized]:
        text=subprocess.check_output(['nm','-C',str(binary)],text=True);require('rmx::Engine::process(' in text,'Fixture lacks actual Engine')
        symbols[str(binary)]=hashlib.sha256(text.encode()).hexdigest()
    root=new_directory(args.output);rows=[];screens=0;guard=None
    require([d[0] for d in args.dataset]==['discovery','fresh','fresh-v3','strip-discovery','fresh-v4'],'Expected complete discovery, former and prospective corpora')
    for stage,session_text,path_text in args.dataset:
        session=Path(session_text);path=Path(path_text);d=json.loads(path.read_text());cases=strip_recipe() if stage=='strip-discovery' else recipe(stage)
        require(d['source_sha256']==binding and d['renderer_sha256']==binaries[str(args.renderer)] and d['acceptance']==GATES and d['stage']==stage,'Comparison source/binary/gates differ')
        require([c['name'] for c in cases]==[r['case'] for r in d['cases']],'Incomplete comparison recipe')
        if stage=='fresh-v4':require(d['role']=='fresh_prediction_bound' and d['prediction_sha256']==sha256(args.prediction)==sha256(session/'predictions.json'),'Fresh prediction binding differs')
        for c,row in zip(cases,d['cases'],strict=True):
            a,provenance=original(SimpleNamespace(session=session,host=args.host),c)
            require(all(row[k]==v for k,v in provenance.items()),'Original provenance differs')
            plan=path.parent/(c['name']+'.tsv');out=path.parent/(c['name']+'.wav');dry=path.parent/(c['name']+'-dry.wav')
            require(plan.read_text()==schedule(c) and sha256(plan)==row['schedule_sha256'] and sha256(out)==row['candidate_sha256'] and sha256(dry)==row['dry_sha256'],'Candidate artifact changed')
            rate,b=float_wav(out);drate,dry_audio=float_wav(dry)
            require(rate==drate==48000 and a.shape==b.shape==dry_audio.shape==(FRAMES,2) and not np.any(dry_audio),'Candidate rate/extent/dry differs')
            a,b=a[32:],b[32:];whole=measure(a,b);same_score(whole,row['whole']);screens+=1;passes=[whole['passed']]
            require([{k:w[k] for k in ['kind','start','stop']} for w in row['windows']]==windows(c,stage),'Window geometry differs')
            for w in row['windows']:
                score=measure(a[w['start']:w['stop']],b[w['start']:w['stop']]);same_score(score,w['score']);passes.append(score['passed']);screens+=1
            require(row['passed']==all(passes),'Program verdict differs')
            folder=root/stage;folder.mkdir(exist_ok=True);san=folder/(c['name']+'.wav');san_dry=folder/(c['name']+'-dry.wav')
            r=subprocess.run([str(args.sanitized),str(session/'silence.wav'),str(san),str(plan),str(san_dry)],capture_output=True,text=True,timeout=120,
              env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            require(r.returncode==0 and not r.stderr and sha256(san)==sha256(out) and sha256(san_dry)==sha256(dry),'Independent sanitizer replay differs')
            if guard is None:
                gain=measure(a,b.astype(float)*1.1);shift=measure(a[1:],b[:-1]);require(not gain['passed'] and not shift['passed'],'Bad audio guard accepted')
                alias=root/'alias.wav';bad=subprocess.run([str(args.renderer),str(session/'silence.wav'),str(alias),str(plan),str(alias)],capture_output=True,text=True)
                require(bad.returncode!=0 and not alias.exists(),'Aliased outputs accepted')
                guard=dict(ten_percent_gain_rejected=True,one_frame_shift_rejected=True,aliased_output_rejected_without_write=True,gain_result=gain,shift_result=shift)
            rows.append(dict(stage=stage,case=c['name'],passed=all(passes),receipt_sha256=provenance['receipt_sha256'],candidate_sha256=sha256(out),comparison_sha256=sha256(path),sanitizer_byte_identical=True))
            print('VERIFIED',stage,c['name'],flush=True)
    require(binding==source_hashes() and script==sha256(Path(__file__)) and all(sha256(Path(p))==v for p,v in binaries.items()),'Audit source/binary changed')
    save_json(root/'verification.json',dict(kind='rmx220-drums-roll-independent-audit',evidence_verified=True,audio_passed=all(r['passed'] for r in rows),programs=len(rows),stereo_screens=screens,cases=rows,
      source_sha256=binding,auditor_sha256=script,renderer_sha256=binaries,prediction_sha256=sha256(args.prediction),sanitizer_compile_commands_sha256=sha256(commands_path),
      sanitizer_compile_commands=[c['command'] for c in units],engine_symbol_sha256=symbols,sanitizer_stderr_empty=True,strip_discovery_helper_sha256=sha256(Path('tools/rmx_drums_strip_motion.py')),guards=guard,acceptance=GATES,
      scope='28 static-roll discovery,16 first prediction regressions,21 third prediction regressions,12 held-strip discovery and12 frozen fresh moving-strip programs at48k/default profiles/120BPM. Independent whole/selection/touch/roll/stop/tail gates and complete sanitizer byte parity. No other tempos, strip geometry/extra assignments, Hold, Quantize, custom profiles, effects during rolls, wrappers or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['prediction','renderer','sanitized','host','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--dataset',nargs=3,action='append',required=True)
    raise SystemExit(verify(p.parse_args()))


if __name__=='__main__':main()
