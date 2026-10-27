#!/usr/bin/env python3
"""Compare and prospectively validate factory48k drum control hypotheses."""
import argparse
import importlib
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import DRUMS, FRAMES, checked, plan_for, require
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE

SETS={'controls':'rmx_drum_controls','discovery':'rmx_drums','kick-first':'rmx_kick_validate',
      'kick-cold':'rmx_kick_cold','snare':'rmx_snare_validate','clap':'rmx_clap_validate','hat':'rmx_hat_validate','control-first':'rmx_drums_control_match'}


def regression_cases(name):
    return first_recipe() if name=='control-first' else importlib.import_module('tools.'+SETS[name]).recipe()


def first_recipe():
    specs=[(13,2,2,[1,101,271,547,12067,48277,96203,192373]),
           (27,3,33,[3,173,349,571,877,16073,96097,240229]),
           (45,123,118,[23,127,257,461,709,12853,12977,13147,192383]),
           (119,132,122,[43,211,383,563,727,48253,144313,288223]),
           (263,253,134,[167,373,571,757,16079,16267,16469,96149]),
           (523,17,138,[48061,48143,48239,48463,144239,144479,288397]),
           (1549,211,203,[65609,65813,66053,96103,144131,288421]),
           (3089,255,253,[139,331,503,683,32083,128143,256219])]
    return [dict(name=f'control-holdout-{drum}-{i}',drum=drum,variant='control-holdout',block=block,level=level,pitch=pitch,hits=hits)
            for drum in DRUMS for i,(block,level,pitch,hits) in enumerate(specs)]


def recipe():
    specs=[(14,0,1,[1,107,281,569,12083,48301,96229,192401]),
           (29,4,35,[5,179,359,593,907,16091,96113,240257]),
           (47,121,117,[29,139,269,487,739,12871,13001,13181,192419]),
           (117,133,123,[47,227,397,587,751,48271,144347,288251]),
           (265,254,133,[173,389,599,787,16097,16289,16493,96173]),
           (527,19,139,[48073,48161,48259,48487,144269,144503,288431]),
           (1553,213,207,[65633,65837,66083,96127,144157,288449]),
           (3097,252,251,[149,347,521,709,32107,128167,256243])]
    return [dict(name=f'control-cold-holdout-{drum}-{i}',drum=drum,variant='control-cold-holdout',block=block,level=level,pitch=pitch,hits=hits)
            for drum in DRUMS for i,(block,level,pitch,hits) in enumerate(specs)]


def source_hashes():
    names=['CMakeLists.txt','tools/rmx_drums_control_match.py','tools/rmx_drums.py','tools/rmx_drum_controls.py',
           'tools/rmx_factory_match.py','tools/rmx_filter_match.py','tools/reference_audio.py','tools/noise_statistics.py',
           'tools/rmx_kick_validate.py','research/audio/experiments/drums_control_probe.cpp',
           'research/audio/experiments/DrumResearchControls.h','research/audio/experiments/DrumControlTables.h',
           'research/audio/experiments/KickResearchCalibration.h','src/core/Wav.cpp','include/rmx/Wav.h','include/rmx/Dsp.h']
    for drum in ('Kick','Snare','Clap','Hat'):
        names += [f'research/audio/experiments/{drum}Research.{suffix}' for suffix in ('h','cpp')]
    return {name:sha256(Path(name)) for name in names}


def payload(args):
    return dict(kind='rmx220-drums-controls-prospective-prediction',cases=recipe(),source_sha256=source_hashes(),
                renderer_sha256=sha256(args.renderer),frames=FRAMES,acceptance=ACCEPTANCE,input='Exact stereo float32 zeros',
                expected='All32 complete whole/attack/body/decay per-channel screens pass1% with fixed32/32 timing and no gain/alignment fit.',
                scope='Static pitch and level, factory neutral profiles/ranges, four drums at stereo48k/120BPM. No control automation, alternate profiles, Engine or hardware claim.')


def frozen(args):
    prediction=json.loads(args.prediction.read_text());require(prediction==payload(args),'Frozen drum control prediction differs');return prediction


def predict(args):save_json(args.report,payload(args));return 0


def capture(args):
    frozen(args);root=new_directory(args.session);(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original plug-in')
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe()
    for c in cases:
        plan=root/(c['name']+'.json');save_json(plan,plan_for(c,inventory))
        run([args.host,'render',args.plugin,source,plan,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('Captured',c['name'],flush=True)
    frozen(args);save_json(root/'matrix.json',dict(kind='rmx220-drums-controls-prospective-captures',cases=cases,prediction_sha256=sha256(args.prediction)))
    return 0


def score(args,cases,role):
    binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    for c in cases:
        raw_a,provenance=checked(args.session,c,cold_kick=c['drum']=='kick')
        plan=root/(c['name']+'.tsv');output=root/(c['name']+'.wav');dry_path=root/(c['name']+'-dry.wav')
        plan.write_text('RMX_DRUM 1\n'+f'{list(DRUMS).index(c["drum"])} {c["level"]} {c["pitch"]} {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits']))
        run([args.renderer,args.session/'silence.wav',output,plan,dry_path]);rate,raw_b=float_wav(output);dry_rate,dry=float_wav(dry_path)
        require(rate==dry_rate==48000 and raw_a.shape==raw_b.shape==dry.shape and not np.any(dry),'Candidate extent/rate/dry differs')
        a,b=raw_a[32:].astype(float),raw_b[32:].astype(float)
        row=provenance|dict(drum=c['drum'],level=c['level'],pitch=c['pitch'],role=role,candidate_sha256=sha256(output),
                           dry_trace_sha256=sha256(dry_path),schedule_sha256=sha256(plan),whole=screen(a,b),windows=[])
        for at in c['hits']:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                right=min(len(a),right)
                if right>left:row['windows'].append(dict(kind=kind,frame=at,start=left,stop=right,score=screen(a[left:right],b[left:right])))
        row['passed']=row['whole']['passed'] and all(w['score']['passed'] for w in row['windows']);rows.append(row)
        print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Candidate changed during comparison')
    report=dict(kind='rmx220-drums-controls-comparison',passed=all(r['passed'] for r in rows),source_sha256=binding,renderer_sha256=binary,
                role=role,acceptance=ACCEPTANCE,cases=rows,full_drum_match=False,live_engine=False,physical_hardware=False)
    if role=='fresh_prediction_bound':frozen(args);report['prediction_sha256']=sha256(args.prediction)
    save_json(root/'comparison.json',report);return 0 if report['passed'] else 1


def regress(args):return score(args,regression_cases(args.case_set),'development_regression')


def compare(args):
    frozen(args);require(sha256(args.session/'predictions.json')==sha256(args.prediction)
            and json.loads((args.session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Capture prediction copy differs')
    return score(args,recipe(),'fresh_prediction_bound')


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for command in ('regress','predict','capture','compare'):
        q=commands.add_parser(command);q.add_argument('--renderer',type=Path,required=True)
        if command=='predict':q.add_argument('--report',type=Path,required=True)
        else:
            q.add_argument('--session',type=Path,required=True)
            if command=='regress':q.add_argument('--case-set',choices=list(SETS),required=True)
            else:q.add_argument('--prediction',type=Path,required=True)
            if command=='capture':
                for name in ('host','plugin'):q.add_argument('--'+name,type=Path,required=True)
            else:q.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
