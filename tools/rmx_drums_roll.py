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


def recipe():
    rows=[]
    for pad,drum in enumerate(DRUMS):
        for position in [-1,*range(6)]:
            changes=[dict(frame=1,type='X',value=max(0,position)*51),dict(frame=9600,type='H',value=pad),dict(frame=9632,type='R',value=pad)]
            if position>=0:changes.extend([dict(frame=96000,type='T',value=1),dict(frame=336000,type='T',value=0)])
            rows.append(dict(name=f'roll-{drum}-'+('baseline' if position<0 else f'position{position}'),drum=drum,variant='roll-discovery',block=128,
              level=128,pitch=128,hits=[9600],position=max(0,position)*51,bpm=120,quantize=0,changes=changes))
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


def capture(args):
    binding=source_hashes();root=new_directory(args.session);inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original')
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe()
    for c in cases:
        path=root/(c['name']+'.json');save_json(path,original_plan(c,inventory));run([args.host,'render',args.plugin,source,path,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('CAPTURED',c['name'],flush=True)
    require(binding==source_hashes(),'Capture source changed');save_json(root/'matrix.json',dict(kind='rmx220-drums-roll-discovery',cases=cases,source_sha256=binding,
      scope='Original factory48k/120BPM unquantized six warmed canonical roll positions; four independent no-touch baselines. Discovery only.'));return 0


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
    binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    for c in recipe():
        a,provenance=original(args,c);plan=root/(c['name']+'.tsv');plan.write_text(schedule(c));out=root/(c['name']+'.wav');dry=root/(c['name']+'-dry.wav')
        run([args.renderer,args.session/'silence.wav',out,plan,dry]);rate,b=float_wav(out);drate,d=float_wav(dry)
        require(rate==drate==48000 and a.shape==b.shape==d.shape==(FRAMES,2) and not np.any(d),'Candidate extent/rate/dry differs')
        starts=attack_starts(a);candidate_starts=attack_starts(b);a,b=a[32:],b[32:];windows=[]
        for kind,start,stop in [('selection',9600,9600+120000),('touch-attack',96000,96256),('roll-stop',336000,337024),('tail',336000,FRAMES-32)]:
            windows.append(dict(kind=kind,start=start,stop=stop,score=screen(a[start:stop],b[start:stop])))
        for at in range(96000,336000,24000):windows.append(dict(kind='roll-window',start=at,stop=at+24000,score=screen(a[at:at+24000],b[at:at+24000])))
        whole=screen(a,b);passed=whole['passed'] and all(w['score']['passed'] for w in windows)
        rows.append(provenance|dict(passed=passed,candidate_sha256=sha256(out),dry_sha256=sha256(dry),schedule_sha256=sha256(plan),whole=whole,windows=windows,
          original_attack_starts=starts,candidate_attack_starts=candidate_starts,original_inter_attack_frames=np.diff(starts).tolist(),candidate_inter_attack_frames=np.diff(candidate_starts).tolist()))
        print('PASS' if passed else 'FAIL',c['name'],'original_attacks',starts[:5],'candidate_attacks',candidate_starts[:5],flush=True)
    require(binding==source_hashes() and binary==sha256(args.renderer),'Source/binary changed')
    save_json(root/'comparison.json',dict(kind='rmx220-drums-roll-discovery-comparison',passed=all(r['passed'] for r in rows),cases=rows,source_sha256=binding,renderer_sha256=binary,acceptance=ACCEPTANCE,
      scope='Discovery whole/touch/roll/tail comparisons at48k/default profiles. Exact attack-template matches are reference timing diagnostics, not candidate alignment or fitting. No full roll, profile, gesture, tempo, quantize, wrapper or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    for name in ['capture','compare']:
        q=s.add_parser(name)
        for key in ['session','host']:q.add_argument('--'+key,type=Path,required=True)
        if name=='capture':q.add_argument('--plugin',type=Path,required=True)
        else:
            q.add_argument('--renderer',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    args=p.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
