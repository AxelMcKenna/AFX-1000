#!/usr/bin/env python3
"""Independently score Trans/Roll renders and replay under ASAN/UBSAN."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from tools import rmx_isolate_modes as modes
from tools import rmx_trans_match as trans
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory


def score(reference,candidate):
    rows=[]
    for channel in range(2):
        a=reference[:,channel].astype(np.float64);b=candidate[:,channel].astype(np.float64)
        energy=float(np.sum(a*a));error=a-b;absolute=float(np.sqrt(np.mean(error*error)))
        relative=float(np.sqrt(np.sum(error*error)/energy)) if energy>1e-20 else None
        rows.append(dict(relative_rms_error=relative,absolute_error_rms=absolute,
                         passed=relative<=.01 if relative is not None else absolute<=1e-8))
    return rows


def intervals(case,stage):
    values=[(256,96000),(96079,98127),(98127,240173),(240173,242221),(242221,modes.FRAMES-32)]
    if stage!='discovery':
        points=sorted(set(e['frame'] for e in case['changes']))
        for index,frame in enumerate(points):
            stop=points[index+1] if index+1<len(points) else modes.FRAMES-32
            values.extend((a,b) for a,b in [(max(0,frame-64),min(stop,frame+2048)),(min(stop,frame+2048),stop)] if b>a)
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['session','host','renderer','comparison','sanitizer-core','compile-commands','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--stage',choices=['discovery','fresh','lifecycle','fresh2','lifecycle2'],required=True)

    parser.add_argument('--live',action='store_true')
    args=parser.parse_args();root=new_directory(args.output);binding=trans.bindings();verifier=sha256(Path(__file__))
    report=json.loads(args.comparison.read_text());require(report['source_sha256']==binding and report['renderer_sha256']==sha256(args.renderer),'Compared candidate changed')
    require(report['kind']=='rmx220-transroll-research','Wrong comparison')
    recipe=trans.recipe(args.stage);require([r['case'] for r in report['cases']]==[c['name'] for c in recipe],'Case coverage changed')
    selected=recipe;require(len(selected)==(26 if args.stage=='discovery' else 32 if args.stage in ['lifecycle','lifecycle2'] else 28),'Trans/Roll coverage differs')
    commands=json.loads(args.compile_commands.read_text());units=[c for c in commands if '/src/core/' in c['file']]
    require(units and all('-fsanitize=address,undefined' in c['command'] for c in units),'Core is not instrumented')
    if args.live:require(any(c['file'].endswith('/TransRoll.cpp') and '-ffp-contract=off' in c['command'] for c in units),'Gate/Drive instrumentation/arithmetic flags missing')
    sanitizer=root/'sanitizer-probe';command=['c++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-ffp-contract=off']+([] if args.live else ['-DRMX_ISOLATE_RESEARCH=1'])+['-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk','-I','include',('tools/isolate_modes_probe.cpp' if args.live else 'tools/isolate_trans_probe.cpp'),str(args.sanitizer_core),'-o',str(sanitizer)]
    inputs={str(p):sha256(p) for p in [args.sanitizer_core,args.compile_commands,args.renderer,args.comparison]}
    subprocess.run(command,check=True,capture_output=True,text=True)
    symbols=subprocess.check_output(['nm','-C',str(sanitizer)],text=True);require('___asan_init' in symbols and '___ubsan_handle_' in symbols,'Probe lacks sanitizer runtime')
    if args.live:require('rmx::Engine::process(' in symbols and 'rmx::CalibratedTransRoll::process(' in symbols,'Instrumented live path missing')
    rows=[]
    for case in selected:
        reference,provenance=modes.original(args,case,expected_source=trans.source(args.stage)[case['source']]);row=next(r for r in report['cases'] if r['case']==case['name'])
        output=args.comparison.parent/(case['name']+'.wav');require(sha256(output)==row['candidate_sha256'],'Compared audio changed')
        rate,candidate=float_wav(output);require(rate==48000 and candidate.shape==reference.shape,'Output extent differs')
        expected=intervals(case,args.stage);require([(w['start'],w['stop']) for w in row['windows']]==expected,'Window coverage differs')
        a=reference[32:];b=candidate[32:];scores=[score(a,b)]+[score(a[start:stop],b[start:stop]) for start,stop in expected]
        recorded=[row['whole']]+[w['score'] for w in row['windows']]
        for computed,original in zip(scores,recorded,strict=True):
            for value,prior in zip(computed,original['channels'],strict=True):
                for name in ['relative_rms_error','absolute_error_rms']:
                    require(value[name] is prior[name] if value[name] is None else np.isclose(value[name],prior[name],rtol=1e-12,atol=1e-15),'Independent score differs')
                require(value['passed']==prior['passed'],'Independent verdict differs')
        passed=all(v['passed'] for s in scores for v in s);require(passed==row['passed'],'Case verdict differs')
        schedule=root/(case['name']+'.tsv');schedule.write_text(modes.schedule(case));san=root/(case['name']+'.wav')
        run=subprocess.run([str(sanitizer),str(args.session/(case['source']+'.wav')),str(san),str(schedule)],capture_output=True,text=True,timeout=120,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        require(run.returncode==0 and not run.stderr,'Sanitizer failed: '+run.stderr);require(sha256(san)==row['candidate_sha256'],'Sanitizer output differs')
        rows.append(provenance|dict(passed=passed,windows=len(scores),candidate_sha256=sha256(output),sanitizer_byte_identical=True));print('AUDITED',case['name'],passed,flush=True)
    require(binding==trans.bindings() and verifier==sha256(Path(__file__)) and all(sha256(Path(p))==v for p,v in inputs.items()),'Audit inputs changed')
    save_json(root/'verification.json',dict(kind='rmx220-transroll-independent-audit',stage=args.stage,live_engine=args.live,passed=all(r['passed'] for r in rows),cases=rows,source_sha256=binding,verifier_sha256=verifier,comparison_sha256=sha256(args.comparison),binary_sha256=inputs|{str(sanitizer):sha256(sanitizer)},sanitizer_compile_command=command,sanitizer_core_commands=units,scope='Input-only Default48k/120BPM. Independent waveform scores and complete optimized/sanitized WAV byte identity; no wrapper or hardware qualification.'))


if __name__=='__main__':main()
