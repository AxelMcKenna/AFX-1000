#!/usr/bin/env python3
"""Freeze and validate the neutral factory hat on new original trigger programs."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_drums import FRAMES, checked, plan_for, require
from tools.rmx_hat import source_hashes as candidate_hashes

ACCEPTANCE = dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,
                  reference_offset_frames=32,candidate_offset_frames=32,gain_fit=False,alignment_search=False)


def recipe():
    specs = [
        (11,[1,109,223,419,12043,48239,96179,192337]),
        (21,[7,151,317,523,839,16061,96079,240197]),
        (41,[19,113,239,431,677,12841,12959,13121,192347]),
        (121,[37,197,367,541,701,48221,144289,288179]),
        (261,[163,349,547,733,16067,16249,16433,96121]),
        (521,[48047,48121,48209,48433,144223,144451,288361]),
        (1543,[65587,65791,66029,96083,144109,288389]),
        (3083,[137,313,487,653,32059,128117,256181]),
    ]
    return [dict(name=f'hat-holdout-{i}',drum='hat',variant='holdout',block=block,hits=hits,level=128,pitch=128)
            for i,(block,hits) in enumerate(specs)]


def source_hashes():
    return candidate_hashes() | {str(Path(__file__).relative_to(Path(__file__).resolve().parents[1])):sha256(Path(__file__)),
                                 'tools/rmx_filter_match.py':sha256(Path('tools/rmx_filter_match.py')),
                                 'tools/noise_statistics.py':sha256(Path('tools/noise_statistics.py')),
                                 'tools/reference_audio.py':sha256(Path('tools/reference_audio.py'))}


def payload(args):
    return dict(kind='rmx220-hat-prospective-prediction',cases=recipe(),source_sha256=source_hashes(),
                renderer_path=str(args.renderer.resolve()),renderer_sha256=sha256(args.renderer),frames=FRAMES,
                input='Exact stereo float32 zeros',acceptance=ACCEPTANCE,
                expected='All eight whole/attack/body/decay per-channel screens pass 1% with fixed32/32 and no gain/alignment fit.',
                scope='Neutral factory hat at stereo48k/120BPM; new cold/retrigger/timing/callback programs. No other drum, settings, Engine or hardware claim.')


def frozen(args):
    prediction=json.loads(args.prediction.read_text())
    require(prediction==payload(args),'Frozen hat prediction differs')
    return prediction


def predict(args):
    save_json(args.report,payload(args));return 0


def capture(args):
    frozen(args);root=new_directory(args.session);(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original plug-in')
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe()
    for c in cases:
        plan=root/(c['name']+'.json');save_json(plan,plan_for(c,inventory))
        run([args.host,'render',args.plugin,source,plan,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('Captured',c['name'],flush=True)
    frozen(args);save_json(root/'matrix.json',dict(kind='rmx220-hat-prospective-captures',cases=cases,
                prediction_sha256=sha256(args.prediction),role='New original captures after frozen candidate.'))
    return 0


def compare(args):
    frozen(args);root=new_directory(args.output);rows=[]
    require(sha256(args.session/'predictions.json')==sha256(args.prediction)
            and json.loads((args.session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Capture prediction copy differs')
    for c in recipe():
        raw_a,provenance=checked(args.session,c);plan=root/(c['name']+'.tsv');output=root/(c['name']+'.wav');dry_path=root/(c['name']+'-dry.wav')
        plan.write_text('RMX_DRUM 1\n'+f'3 128 128 {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits']))
        run([args.renderer,args.session/'silence.wav',output,plan,dry_path]);rate,raw_b=float_wav(output);dry_rate,dry=float_wav(dry_path)
        require(rate==dry_rate==48000 and raw_b.shape==raw_a.shape==dry.shape and not np.any(dry),'Candidate extent/rate/dry differs')
        a,b=raw_a[32:].astype(float),raw_b[32:].astype(float)
        row=provenance | dict(role='fresh_prediction_bound',candidate_sha256=sha256(output),dry_trace_sha256=sha256(dry_path),
                            schedule_sha256=sha256(plan),whole=screen(a,b),windows=[])
        for at in c['hits']:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                right=min(len(a),right)
                if right>left:row['windows'].append(dict(kind=kind,frame=at,start=left,stop=right,score=screen(a[left:right],b[left:right])))
        row['passed']=row['whole']['passed'] and all(w['score']['passed'] for w in row['windows']);rows.append(row)
        print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    frozen(args)
    save_json(root/'comparison.json',dict(kind='rmx220-hat-prospective-comparison',passed=all(r['passed'] for r in rows),
              prediction_sha256=sha256(args.prediction),renderer_sha256=sha256(args.renderer),source_sha256=source_hashes(),
              acceptance=ACCEPTANCE,cases=rows,full_drum_match=False,physical_hardware=False,
              scope='Eight fresh trigger programs after freezing the neutral factory48k hat research candidate. No per-comparison gain or alignment fit.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for command in ('predict','capture','compare'):
        q=commands.add_parser(command);q.add_argument('--renderer',type=Path,required=True)
        if command=='predict':q.add_argument('--report',type=Path,required=True)
        else:
            q.add_argument('--prediction',type=Path,required=True);q.add_argument('--session',type=Path,required=True)
            if command=='capture':
                for name in ('host','plugin'):q.add_argument('--'+name,type=Path,required=True)
            else:q.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
