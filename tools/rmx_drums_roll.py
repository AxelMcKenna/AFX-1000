#!/usr/bin/env python3
"""Capture and compare original factory X-Pad drum rolls at fixed timing/gain."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256,write_wav
from tools.noise_statistics import float_wav
from tools.rmx_drums import DRUMS,FRAMES,checked,plan_for,require
from tools.rmx_drums_fx import source_hashes as core_hashes
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE


def recipe(stage='discovery'):
    rows=[]
    for pad,drum in enumerate(DRUMS):
        if stage=='fresh-v3':
            for index,variant in enumerate(['cold-quarter','warm-two','reselect-position','rearm-prior','no-rearm']):
                position=[102,255,[51,102,153,204][pad],153,204][index]
                hit=48089 if variant=='warm-two' else 13+pad*2
                touches=[(96131,1),(336619,0)] if variant=='warm-two' else [(83+pad*6,1),(150389,0)]
                changes=[dict(frame=1,type='X',value=position),dict(frame=hit,type='H',value=pad),dict(frame=hit+32,type='R',value=pad)];hits=[hit]
                if index>=2:
                    if variant!='rearm-prior':
                        hits.append(240173);changes += [dict(frame=240173,type='H',value=(pad+1)%4),dict(frame=240205,type='R',value=(pad+1)%4)]
                    if variant!='no-rearm':changes.append(dict(frame=240251,type='X',value=position))
                    touches += [(240433,1),(390587,0)]
                changes += [dict(frame=at,type='T',value=value) for at,value in touches];changes.sort(key=lambda e:e['frame'])
                rows.append(dict(name=f'roll-fresh3-{drum}-{variant}',drum=drum,variant=variant,block=[61,277,1559,101,313][index]+pad*2,
                  level=[227,7,43,181,251][index],pitch=[109,239,29,147,203][index],hits=hits,position=position,bpm=120,quantize=0,changes=changes))
            continue
        if stage=='fresh-v2':
            specs=[('cold-one',53,113,101,204,137,5,[(109,1),(193117,0)]),
              ('warm-two',269,3,249,255,91,48061,[(96113,1),(336379,0)]),
              ('cold-quarter',107,193,117,102,160,11,[(59,1),(144313,0)]),
              ('reselect',[1571,311,89,1499][pad],[37,191,253,19][pad],[17,139,213,35][pad],[51,102,153,204][pad],120,179,[(65591,1),(145033,0),(192409,1),(336457,0)])]
            for variant,block,level,pitch,position,bpm,hit,touches in specs:
                changes=[dict(frame=1,type='X',value=position),dict(frame=hit,type='H',value=pad),dict(frame=hit+32,type='R',value=pad)]
                hits=[hit]
                if variant=='reselect':
                    hits.append(192233);changes += [dict(frame=192233,type='H',value=(pad+1)%4),dict(frame=192265,type='R',value=(pad+1)%4)]
                changes += [dict(frame=at,type='T',value=value) for at,value in touches];changes.sort(key=lambda e:e['frame'])
                rows.append(dict(name=f'roll-fresh2-{drum}-{variant}',drum=drum,variant=variant,block=block,level=level,pitch=pitch,hits=hits,position=position,bpm=bpm,quantize=0,changes=changes))
            continue
        if stage=='fresh':
            specs=[('cold-one',37,239,173,204,7,[(97,1),(192241,0)]),
              ('warm-two',293,17,73,255,48043,[(96079,1),(336271,0)]),
              ('cold-quarter',79,255,116,102,3,[(43,1),(144197,0)]),
              ('restart',1597,128,141,[51,102,153,204][pad],173,[(65573,1),(145007,0),(192193,1),(336421,0)])]
            for variant,block,level,pitch,position,hit,touches in specs:
                changes=[dict(frame=1,type='X',value=position),dict(frame=hit,type='H',value=pad),dict(frame=hit+32,type='R',value=pad)]
                changes += [dict(frame=at,type='T',value=value) for at,value in touches];changes.sort(key=lambda e:e['frame'])
                rows.append(dict(name=f'roll-fresh-{drum}-{variant}',drum=drum,variant=variant,block=block,level=level,pitch=pitch,hits=[hit],position=position,bpm=120,quantize=0,changes=changes))
            continue
        for position in [-1,*range(6)]:
            changes=[dict(frame=1,type='X',value=max(0,position)*51),dict(frame=9600,type='H',value=pad),dict(frame=9632,type='R',value=pad)]
            if position>=0:changes.extend([dict(frame=96000,type='T',value=1),dict(frame=336000,type='T',value=0)])
            rows.append(dict(name=f'roll-{drum}-'+('baseline' if position<0 else f'position{position}'),drum=drum,variant='roll-discovery',block=128,
              level=128,pitch=128,hits=[9600],position=max(0,position)*51,bpm=120,quantize=0,changes=changes))
    if stage in ('fresh-v2','fresh-v3'):rows.append(dict(name=('roll-fresh3-no-selection' if stage=='fresh-v3' else 'roll-fresh2-no-selection'),drum='kick',variant='no-selection',block=71,level=255,pitch=249,hits=[],position=153,bpm=120,quantize=0,
      changes=[dict(frame=1,type='X',value=153),dict(frame=48097,type='T',value=1),dict(frame=144227,type='T',value=0),dict(frame=192313,type='T',value=1),dict(frame=336509,type='T',value=0)]))
    return rows


def source_hashes():
    return core_hashes()|{n:sha256(Path(n)) for n in ['tools/rmx_drums_roll.py','tools/drum_roll_probe.cpp','tools/rmx_kick_validate.py']}


def original_plan(c,inventory):
    plan=plan_for(c,inventory)
    def setting(name,value):
        p=next(p for p in inventory['parameters'] if p['name']==name);return {k:p[k] for k in ['name','id','index']}|dict(value=value)
    plan['bpm']=c['bpm'];plan['parameters']=[p|dict(value=c['quantize']) if p['name']=='QuantizeButton' else p for p in plan['parameters']]
    events=[]
    for e in c['changes']:
        kind=e['type'];raw=e['value'];name=list(DRUMS.values())[raw] if kind in ('H','R') else dict(T='XpadTouch',X='XpadPosition',F='HoldButton')[kind]
        value=1 if kind=='H' else 0 if kind=='R' else raw/255 if kind=='X' else raw
        events.append(setting(name,value)|dict(frame=e['frame'],type='parameter'))
    plan['events']=events;return plan


def schedule(c):
    return f'RMX_DRUM_ROLL 1\n{c["level"]} {c["pitch"]} {c["position"]} {c["block"]} {c["bpm"]} {c["quantize"]}\n'+''.join(f'{e["frame"]} {e["type"]} {e["value"]}\n' for e in c['changes'])


def payload(args):
    return dict(kind='rmx220-drums-roll-prospective-prediction',stage=args.stage,cases=recipe(args.stage),source_sha256=source_hashes(),renderer_sha256=sha256(args.renderer),acceptance=ACCEPTANCE,
      expected=f'All{len(recipe(args.stage))} fresh full-program, selection/touch/roll/tail windows pass unchanged1% per channel, fixed32/32, no gain or alignment fitting.',
      scope='Factory default48k unquantized roll programs with fixed32/32 and unchanged gates. Fresh-v3 is120BPM: cold/warm, same-position refresh, rearming the prior drum, new selection without position refresh and no-selection silence. Failed fresh-v2 requested91/137/160BPM without effective reference tempo setup and remains unqualified. Extra strip assignments/geometry, moving positions, Hold, Quantize, other settings, wrappers and hardware remain separate.')


def frozen(args):
    require(args.prediction is not None and json.loads(args.prediction.read_text())==payload(args),'Frozen roll prediction differs')


def predict(args):
    require(args.stage!='discovery','Only fresh programs can be predicted');save_json(args.report,payload(args));return 0


def capture(args):
    if args.stage!='discovery':frozen(args)
    binding=source_hashes();root=new_directory(args.session);inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original')
    if args.stage!='discovery':(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe(args.stage)
    for c in cases:
        path=root/(c['name']+'.json');save_json(path,original_plan(c,inventory));run([args.host,'render',args.plugin,source,path,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('CAPTURED',c['name'],flush=True)
    require(binding==source_hashes(),'Capture source changed')
    if args.stage!='discovery':frozen(args)
    save_json(root/'matrix.json',dict(kind='rmx220-drums-roll-captures',stage=args.stage,cases=cases,source_sha256=binding,prediction_sha256=sha256(args.prediction) if args.stage!='discovery' else None,
      scope='Original factory48k/120BPM unquantized warmed canonical roll controls. Discovery and fresh roles are separate.'));return 0


def original(args,c):
    a,provenance=checked(args.session,c,plan_builder=original_plan);receipt=json.loads((args.session/c['name']/'receipt.json').read_text())
    require(receipt['host_sha256']==sha256(args.host),'Original host differs')
    for member in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/member['path'])==member['sha256'],'Original binary differs')
    return a,provenance


def attack_starts(a):
    # Original-only diagnostic: find exact repetitions of the isolated hit's
    # first64 nonzero samples. Never used to shift or score a candidate.
    x=a[:,0];indices=np.flatnonzero(np.abs(x[:96000])>1e-12)
    if not len(indices):return []
    first=int(indices[0]);template=x[first:first+64].view(np.uint32);possible=np.flatnonzero(x.view(np.uint32)==template[0])
    return [int(i) for i in possible if i+64<=len(x) and np.array_equal(x[i:i+64].view(np.uint32),template)]


def compare(args):
    if args.stage!='discovery':
        if args.regression:
            old=json.loads(args.prediction.read_text());require(old['kind']=='rmx220-drums-roll-prospective-prediction' and old['cases']==recipe(args.stage) and old['acceptance']==ACCEPTANCE,'Former roll recipe/gates differ')
        else:frozen(args)
        manifest=json.loads((args.session/'matrix.json').read_text());require(manifest['prediction_sha256']==sha256(args.prediction)==sha256(args.session/'predictions.json'),'Fresh prediction copy differs')
    binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    for c in recipe(args.stage):
        a,provenance=original(args,c);plan=root/(c['name']+'.tsv');plan.write_text(schedule(c));out=root/(c['name']+'.wav');dry=root/(c['name']+'-dry.wav')
        run([args.renderer,args.session/'silence.wav',out,plan,dry]);rate,b=float_wav(out);drate,d=float_wav(dry)
        require(rate==drate==48000 and a.shape==b.shape==d.shape==(FRAMES,2) and not np.any(d),'Candidate extent/rate/dry differs')
        starts=attack_starts(a);candidate_starts=attack_starts(b);a,b=a[32:],b[32:];windows=[]
        intervals=[('selection',9600,9600+120000),('touch-attack',96000,96256),('roll-stop',336000,337024),('tail',336000,FRAMES-32)]
        intervals += [('roll-window',at,at+24000) for at in range(96000,336000,24000)]
        if args.stage!='discovery':
            touches=[e for e in c['changes'] if e['type']=='T'];last=max(e['frame'] for e in touches)
            intervals=[('selection',at,at+120000) for at in c['hits']]+[('tail',last,FRAMES-32)]
            for e in touches:intervals.append(('touch-attack' if e['value'] else 'roll-stop',e['frame'],e['frame']+(256 if e['value'] else 1024)))
            for on,off in zip(touches[::2],touches[1::2]):intervals += [('roll-window',at,min(at+24000,off['frame'])) for at in range(on['frame'],off['frame'],24000)]
        for kind,start,stop in intervals:
            stop=min(stop,len(a));require(stop>start,'Invalid roll window')
            windows.append(dict(kind=kind,start=start,stop=stop,score=screen(a[start:stop],b[start:stop])))
        whole=screen(a,b);passed=whole['passed'] and all(w['score']['passed'] for w in windows)
        rows.append(provenance|dict(passed=passed,candidate_sha256=sha256(out),dry_sha256=sha256(dry),schedule_sha256=sha256(plan),whole=whole,windows=windows,
          original_attack_starts=starts,candidate_attack_starts=candidate_starts,original_inter_attack_frames=np.diff(starts).tolist(),candidate_inter_attack_frames=np.diff(candidate_starts).tolist()))
        print('PASS' if passed else 'FAIL',c['name'],'original_attacks',starts[:5],'candidate_attacks',candidate_starts[:5],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Source/binary changed')
    if args.stage!='discovery' and not args.regression:frozen(args)
    save_json(root/'comparison.json',dict(kind='rmx220-drums-roll-comparison',passed=all(r['passed'] for r in rows),stage=args.stage,role='fresh_prediction_bound' if args.stage!='discovery' and not args.regression else 'development_regression',
      prediction_sha256=sha256(args.prediction) if args.stage!='discovery' else None,cases=rows,source_sha256=binding,renderer_sha256=binary,acceptance=ACCEPTANCE,
      scope='Discovery whole/touch/roll/tail comparisons at48k/default profiles. Exact attack-template matches are reference timing diagnostics, not candidate alignment or fitting. No full roll, profile, gesture, tempo, quantize, wrapper or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ['predict','capture','compare']:
        q=s.add_parser(name);q.add_argument('--stage',choices=['discovery','fresh','fresh-v2','fresh-v3'],default='discovery');q.add_argument('--prediction',type=Path)
        if name=='predict':
            q.add_argument('--renderer',type=Path,required=True);q.add_argument('--report',type=Path,required=True);continue
        for key in ['session','host']:q.add_argument('--'+key,type=Path,required=True)
        if name=='capture':q.add_argument('--plugin',type=Path,required=True)
        else:
            q.add_argument('--renderer',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--regression',action='store_true')
        if name=='capture':q.add_argument('--renderer',type=Path)
    args=p.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
