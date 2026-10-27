#!/usr/bin/env python3
"""Measure live factory drum pitch/level gestures without fitting gain or timing."""
import argparse
import json
from pathlib import Path
import subprocess
import os

import numpy as np

from tools.reference_audio import save_json,sha256,write_wav
from tools.noise_statistics import float_wav
from tools.rmx_drums import DRUMS,FRAMES,checked,plan_for,require
from tools.rmx_drums_fx import source_hashes as core_hashes
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE


def recipe(stage):
    rows=[]
    for pad,drum in enumerate(DRUMS):
        specs=[('static',128,128,128,[48000,192000,336000],[]),
          ('level',37,128,128,[48037,192079,336113],[(48113,'L',17),(48437,'L',239),(49109,'L',0),(50137,'L',128),(192193,'L',255),(193033,'L',41),(336281,'L',113)]),
          ('pitch',131,128,128,[48043,192089,336127],[(48117,'P',64),(48653,'P',192),(49123,'P',120),(49409,'P',121),(49691,'P',136),(50017,'P',255),(192211,'P',23),(193049,'P',173)]),
          ('level-fast',29,255,113,[19,251,487,12097,96113,240257],[(1,'L',0),(47,'L',255),(79,'L',17),(113,'L',239),(139,'L',3),(173,'L',191),(229,'L',37),(12371,'L',128)]),
          ('pitch-fast',563,191,128,[23,257,503,16097,128143,256219],[(1,'P',1),(43,'P',255),(67,'P',35),(101,'P',207),(151,'P',119),(197,'P',137),(293,'P',121),(353,'P',135),(16099,'P',73)]),
          ('sweep',97,128,0,[48031,192067,336109],[(48073+i*97,'P',i*3) for i in range(86)]),
          ('mixed',1597,239,173,[17,193,401,48059,96103,192157],[(31,'L',19),(79,'P',47),(127,'L',255),(211,'P',237),(307,'L',128),(49111,'P',101),(49933,'L',73)])]
        if stage=='fresh':
            specs=[('fresh-level',53,17+pad*41,101,[7,277,619,12071,96073,240289],[(3,'L',213),(61,'L',4),(109,'L',133),(181,'L',252),(12097,'L',39),(12313,'L',193),(96203,'L',113)]),
              ('fresh-pitch',293,213,35+pad*47,[11,283,643,16087,128129,256237],[(5,'P',249),(83,'P',117),(157,'P',123),(233,'P',139),(397,'P',207),(16123,'P',3),(128257,'P',173)]),
              ('fresh-combined',3203,133,128,[13,307,683,48083,144179,288367],[(2,'L',0),(71,'P',27),(137,'L',254),(199,'P',203),(367,'L',19),(487,'P',134),(48097,'L',211),(48439,'P',67)])]
        for variant,block,level,pitch,hits,changes in specs:
            events=[dict(frame=at,type=kind,value=value) for at,kind,value in changes]
            for i,at in enumerate(hits):
                instrument=(pad+i)%4 if variant=='mixed' else pad
                events.extend([dict(frame=at,type='H',value=instrument),dict(frame=at+32,type='R',value=instrument)])
            events.sort(key=lambda e:e['frame'])
            rows.append(dict(name=f'motion-{drum}-{variant}',drum=drum,variant=variant,block=block,level=level,pitch=pitch,hits=hits,changes=events))
    return rows


def source_hashes():
    return core_hashes()|{n:sha256(Path(n)) for n in ['tools/rmx_drums_motion.py','tools/drum_motion_probe.cpp','src/plugin/Plugin.cpp']}


def original_plan(c,inventory):
    plan=plan_for(c,inventory);events=[]
    for e in c['changes']:
        name=list(DRUMS.values())[e['value']] if e['type'] in ('H','R') else 'XpadLevelVolume' if e['type']=='L' else 'PitchVolume'
        p=next(p for p in inventory['parameters'] if p['name']==name)
        value=1 if e['type']=='H' else 0 if e['type']=='R' else e['value']/255
        events.append({k:p[k] for k in ['index','id','name']}|dict(frame=e['frame'],type='parameter',value=value))
    plan['events']=events;return plan


def schedule(c):
    return f'RMX_DRUM_MOTION 1\n{c["level"]} {c["pitch"]} {c["block"]}\n'+''.join(f'{e["frame"]} {e["type"]} {e["value"]}\n' for e in c['changes'])


def payload(args):
    return dict(kind='rmx220-drums-motion-prediction',stage=args.stage,cases=recipe(args.stage),source_sha256=source_hashes(),renderer_sha256=sha256(args.renderer),
      acceptance=ACCEPTANCE,expected='All12 fresh programs pass unchanged1% whole/attack/body/decay and control-event windows, fixed32/32, no gain or alignment fitting.',
      scope='Factory default profiles at48k/120BPM; live Engine pitch/level gestures only. No custom profile, rolls, other effects, rates or hardware claim.')


def predict(args):require(args.stage=='fresh','Only fresh sets are predictions');save_json(args.report,payload(args));return 0


def capture(args):
    binding=source_hashes();root=new_directory(args.session)
    if args.stage=='fresh':
        require(json.loads(args.prediction.read_text())==payload(args),'Frozen prediction differs');(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original')
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe(args.stage)
    for c in cases:
        p=root/(c['name']+'.json');save_json(p,original_plan(c,inventory));run([args.host,'render',args.plugin,source,p,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('CAPTURED',c['name'],flush=True)
    require(binding==source_hashes(),'Sources changed during capture')
    save_json(root/'matrix.json',dict(kind='rmx220-drums-motion-captures',stage=args.stage,cases=cases,source_sha256=binding,
      prediction_sha256=sha256(args.prediction) if args.stage=='fresh' else None));return 0


def compare(args):
    binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    if args.stage=='fresh':require(json.loads(args.prediction.read_text())==payload(args) and sha256(args.prediction)==sha256(args.session/'predictions.json'),'Frozen prediction differs')
    for c in recipe(args.stage):
        a,provenance=checked(args.session,c,plan_builder=original_plan);receipt=json.loads((args.session/c['name']/'receipt.json').read_text())
        require(receipt['host_sha256']==sha256(args.host),'Original host differs')
        for p in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/p['path'])==p['sha256'],'Original binary differs')
        path=root/(c['name']+'.tsv');path.write_text(schedule(c));out=root/(c['name']+'.wav');dry=root/(c['name']+'-dry.wav')
        run([args.renderer,args.session/'silence.wav',out,path,dry]);rate,b=float_wav(out);dryrate,d=float_wav(dry)
        require(rate==dryrate==48000 and a.shape==b.shape==d.shape==(FRAMES,2) and not np.any(d),'Candidate extent/rate/dry differs')
        sanitized=None
        if args.sanitized:
            san=root/(c['name']+'-asan.wav');sd=root/(c['name']+'-asan-dry.wav')
            r=subprocess.run([str(args.sanitized),str(args.session/'silence.wav'),str(san),str(path),str(sd)],capture_output=True,text=True,timeout=120,
              env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            sanitized=r.returncode==0 and not r.stderr and sha256(san)==sha256(out) and sha256(sd)==sha256(dry);require(sanitized,'Sanitizer differs')
        a,b=a[32:].astype(float),b[32:].astype(float);windows=[]
        for at in c['hits']:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                right=min(len(a),right)
                if right>left:windows.append(dict(kind=kind,frame=at,start=left,stop=right,score=screen(a[left:right],b[left:right])))
        for e in c['changes']:
            if e['type'] in ('L','P'):
                at=e['frame'];windows.append(dict(kind='level-change' if e['type']=='L' else 'pitch-change',frame=at,start=at,stop=min(len(a),at+1024),score=screen(a[at:at+1024],b[at:at+1024])))
        row=provenance|dict(candidate_sha256=sha256(out),dry_sha256=sha256(dry),schedule_sha256=sha256(path),whole=screen(a,b),windows=windows,sanitizer_byte_identical=sanitized)
        row['passed']=row['whole']['passed'] and all(w['score']['passed'] for w in windows);rows.append(row)
        print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Sources/renderer changed')
    save_json(root/'comparison.json',dict(kind='rmx220-drums-motion-comparison',passed=all(r['passed'] for r in rows),stage=args.stage,cases=rows,source_sha256=binding,renderer_sha256=binary,
      sanitized_sha256=sha256(args.sanitized) if args.sanitized else None,acceptance=ACCEPTANCE,prediction_sha256=sha256(args.prediction) if args.stage=='fresh' else None,
      scope='Live Engine default-profile48k pitch/level gestures; original provenance/readbacks verified, fixed32/32, no gain/alignment fitting. Discovery cases are regressions rather than fresh predictions.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ['predict','capture','compare']:
        q=s.add_parser(name);q.add_argument('--stage',choices=['discovery','fresh'],default='discovery');q.add_argument('--renderer',type=Path,required=True);q.add_argument('--prediction',type=Path)
        if name=='predict':q.add_argument('--report',type=Path,required=True)
        else:
            q.add_argument('--session',type=Path,required=True);q.add_argument('--host',type=Path,required=True)
            if name=='capture':q.add_argument('--plugin',type=Path,required=True)
            else:q.add_argument('--output',type=Path,required=True);q.add_argument('--sanitized',type=Path)
    args=p.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
