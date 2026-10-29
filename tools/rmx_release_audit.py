#!/usr/bin/env python3
"""Recompute Release scores independently and require instrumented byte parity."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory
from tools import rmx_release as release


def score(a,b):
    # Deliberately separate from the comparison's screen function.
    values=[]
    for channel in range(2):
        reference=a[:,channel].astype(np.float64);candidate=b[:,channel].astype(np.float64)
        energy=float(np.dot(reference,reference));error=reference-candidate
        absolute=float(np.sqrt(np.mean(error*error)))
        relative=float(np.linalg.norm(error)/np.sqrt(energy)) if energy>1e-20 else None
        values.append(dict(relative_rms_error=relative,absolute_error_rms=absolute,
                           passed=(relative<=.01 if relative is not None else absolute<=1e-8)))
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['session','host','renderer','sanitizer','commands','comparison','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage',choices=['discovery','fresh','fresh-v2'],required=True);p.add_argument('--prediction',type=Path)
    p.add_argument('--regression',action='store_true');args=p.parse_args();root=new_directory(args.output);binding=release.source_hashes();verifier=sha256(Path(__file__))
    report=json.loads(args.comparison.read_text());require(report['source_sha256']==binding and report['renderer_sha256']==sha256(args.renderer),'Comparison source/binary changed')
    require(report['acceptance']==release.ACCEPTANCE,'Gates changed')
    recipe=release.recipe(args.stage);require([r['case'] for r in report['cases']]==[c['name'] for c in recipe],'Coverage differs')
    if args.stage!='discovery' and not args.regression:
        prediction=release.frozen(args);require(report['prediction_sha256']==sha256(args.prediction),'Prediction binding differs')
    commands=json.loads(args.commands.read_text());suffixes=['/Engine.cpp','/FactoryRelease.cpp','/Scene.cpp','/ReverbDown.cpp','/ReverbUp.cpp','/Isolator.cpp','/Wav.cpp','/release_probe.cpp']
    selected=[c for c in commands if any(c['file'].endswith(s) for s in suffixes) and 'RMX_RELEASE_RESEARCH' not in c['command']]
    require(len(selected)==len(suffixes) and all('-fsanitize=address,undefined' in c['command'] for c in selected),'Missing instrumented processing units')
    require(all('-ffp-contract=off' in c['command'] for c in selected if c['file'].endswith(('/FactoryRelease.cpp','/ReverbDown.cpp','/ReverbUp.cpp'))),'Identified arithmetic flags changed')
    symbols=subprocess.check_output(['nm','-C',str(args.sanitizer)],text=True)
    require('rmx::Engine::process(' in symbols and 'rmx::FactoryRelease::process(' in symbols,'Sanitizer lacks live engine/Release')
    binaries={str(path):sha256(path) for path in [args.renderer,args.sanitizer]};rows=[]
    for c,row in zip(recipe,report['cases'],strict=True):
        a,provenance=release.original(args,c);require(all(row[k]==v for k,v in provenance.items()),'Original provenance differs')
        schedule=args.comparison.parent/(c['name']+'.tsv');output=args.comparison.parent/(c['name']+'.wav')
        require(schedule.read_text()==release.schedule(c) and sha256(schedule)==row['schedule_sha256'] and sha256(output)==row['candidate_sha256'],'Candidate changed')
        if args.stage!='discovery' and not args.regression:
            require(row['candidate_sha256']==prediction['outputs_sha256'][c['name']],'Fresh prediction changed')
            receipt=json.loads((args.session/c['name']/'receipt.json').read_text())
            require(datetime.fromisoformat(prediction['created_utc'])<datetime.fromisoformat(receipt['created_at_utc']),'Original predates prediction')
        rate,b=float_wav(output);require(rate==48000 and a.shape==b.shape==(release.FRAMES,2),'Extent differs');a,b=a[32:],b[32:]
        intervals=([('pre-control',256,96000),('active',96079,240173),('return',240173,release.FRAMES-32)] if args.stage=='discovery' else [('segment',e['frame'],c['changes'][i+1]['frame'] if i+1<len(c['changes']) else release.FRAMES-32) for i,e in enumerate(c['changes'])])
        if args.stage!='discovery' and c['changes'] and c['changes'][0]['frame']>256:intervals.insert(0,('pre-control',256,c['changes'][0]['frame']))
        intervals += [('edge',e['frame'],min(release.FRAMES-32,e['frame']+2048)) for e in c['changes']]
        require([(w['kind'],w['start'],w['stop']) for w in row['windows']]==intervals,'Window coverage differs')
        groups=[(score(a,b),row['whole'])]+[(score(a[s:t],b[s:t]),w['score']) for (_,s,t),w in zip(intervals,row['windows'],strict=True)]
        verdict=True
        for measured,saved in groups:
            require(all(all(m[k]==v[k] for k in m) for m,v in zip(measured,saved['channels'],strict=True)),'Independent score differs')
            passed=all(v['passed'] for v in measured);require(passed==saved['passed'],'Window verdict differs');verdict &= passed
        require(verdict==row['passed'],'Program verdict differs')
        san=root/(c['name']+'-asan.wav');r=subprocess.run([str(args.sanitizer),str(args.session/(c['source']+'.wav')),str(san),str(schedule)],capture_output=True,text=True,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),timeout=120)
        require(r.returncode==0 and not r.stderr,'Instrumented replay failed: '+r.stderr);require(sha256(san)==row['candidate_sha256'],'Sanitizer audio differs')
        rows.append(provenance|dict(passed=verdict,candidate_sha256=sha256(output),sanitizer_byte_identical=True,windows=1+len(intervals)));print('AUDITED',c['name'],verdict,flush=True)
    require(binding==release.source_hashes() and verifier==sha256(Path(__file__)) and all(sha256(Path(path))==value for path,value in binaries.items()),'Audit inputs changed')
    save_json(root/'verification.json',dict(kind='rmx220-release-independent-audit',stage=args.stage,passed=all(r['passed'] for r in rows),programs=len(rows),programs_passed=sum(r['passed'] for r in rows),cases=rows,source_sha256=binding,verifier_sha256=verifier,binary_sha256=binaries,comparison_sha256=sha256(args.comparison),prediction_sha256=sha256(args.prediction) if args.stage!='discovery' and not args.regression else None,acceptance=release.ACCEPTANCE,sanitizer_compile_commands=selected,commands_sha256=sha256(args.commands),scope='Independent raw score recomputation, exact coverage/provenance checks and sanitizer/optimized byte identity. Retains failed windows. Default48k/120BPM only; no listening/hardware or whole-device claim.'))


if __name__=='__main__':main()
