#!/usr/bin/env python3
"""Validate the actual Engine's factory drums, including simultaneous instruments."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_drums import DRUMS, FRAMES, plan_for, require
from tools.rmx_drums_control_match import ACCEPTANCE, SETS, recipe as cold_recipe, regression_cases, score, source_hashes as base_hashes

DATASETS=[*SETS,'control-cold']


def cases_for(name):return cold_recipe() if name=='control-cold' else regression_cases(name)


def recipe():
    specs=[(15,0,3,[1,113,307,787,1609,48079,144293]),(37,255,249,[7,179,367,809,1627,96089,240181]),
           (129,133,116,[48043,48127,48283,49559,144149,288331]),(1023,37,141,[19,191,389,887,1649,128057,256127])]
    rows=[dict(name=f'engine-drum-{drum}-{i}',drum=drum,variant='engine-holdout',block=block,level=level,pitch=pitch,hits=hits)
          for drum in DRUMS for i,(block,level,pitch,hits) in enumerate(specs)]
    mixed=[(31,128,128,[(at,pad) for at in [48000,96037,192079] for pad in range(4)]),
           (131,255,203,[(1,0),(10,1),(19,2),(28,3),(83,0),(101,2),(149,1),(179,3),(48043,0),(48059,1),(48071,2),(48089,3)]),
           (509,191,64,[(17,0),(17,1),(73,2),(73,3),(161,0),(161,3),(337,1),(337,2),(96047,0),(96047,1),(96047,2),(96047,3)]),
           (2053,3,128,[(at,pad) for at in [3,197,401,12029,128053] for pad in range(4)])]
    for i,(block,level,pitch,events) in enumerate(mixed):
        rows.append(dict(name=f'engine-drums-mixed-{i}',drum='kick',variant='engine-mixed',block=block,level=level,pitch=pitch,
                         hits=[at for at,pad in events],pads=[pad for at,pad in events]))
    return rows


def source_hashes():
    names=['tools/rmx_drums_engine.py','include/rmx/Parameters.h','include/rmx/Sequencer.h','include/rmx/FactoryDrums.h']
    return base_hashes()|{name:sha256(Path(name)) for name in names}


def original_plan(c,inventory):
    plan=plan_for(c,inventory)
    if 'pads' not in c:return plan
    require(len(c['pads'])==len(c['hits']),'Pad schedule length differs');events=[]
    for at,pad in zip(c['hits'],c['pads']):
        parameter=next(p for p in inventory['parameters'] if p['name']==list(DRUMS.values())[pad])
        events.extend({k:parameter[k] for k in ('index','id','name')}|dict(frame=at+offset,type='parameter',value=value)
                      for offset,value in [(0,1),(32,0)])
    plan['events']=sorted(events,key=lambda e:e['frame']);return plan


def schedule(c):
    version=2 if 'pads' in c else 1
    header=f'RMX_DRUM {version}\n{list(DRUMS).index(c["drum"])} {c["level"]} {c["pitch"]} {c["block"]}\n'
    return header+(''.join(f'{at} {pad}\n' for at,pad in zip(c['hits'],c['pads'])) if version==2 else ''.join(f'{at}\n' for at in c['hits']))


def payload(args):
    return dict(kind='rmx220-engine-drums-prospective-prediction',cases=recipe(),frames=FRAMES,source_sha256=source_hashes(),
        renderer_sha256=sha256(args.renderer),acceptance=ACCEPTANCE,input='Exact stereo float32 zeros',
        expected='All20 Engine whole/attack/body/decay per-channel screens pass1%, including four simultaneous/staggered multi-drum programs. Fixed32/32; no gain/alignment fit.',
        scope='Actual Engine factory48k default profiles/ranges, Scene/Isolator/Release off, software float output protection disabled as in plug-in. Static pitch/level and declared triggers only; FX routing, alternate profiles, other rates and device sound remain unqualified.')


def frozen(args):
    prediction=json.loads(args.prediction.read_text());require(prediction==payload(args),'Frozen Engine drum prediction differs');return prediction


def predict(args):save_json(args.report,payload(args));return 0


def capture(args):
    frozen(args);root=new_directory(args.session);(root/'predictions.json').write_bytes(args.prediction.read_bytes())
    inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original plug-in')
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe()
    for c in cases:
        plan=root/(c['name']+'.json');save_json(plan,original_plan(c,inventory))
        run([args.host,'render',args.plugin,source,plan,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('Captured',c['name'],flush=True)
    frozen(args);save_json(root/'matrix.json',dict(kind='rmx220-engine-drums-prospective-captures',cases=cases,prediction_sha256=sha256(args.prediction)))
    return 0


def compare_cases(args,cases,role):
    return score(args,cases,role,hashes=source_hashes,validate=frozen,plan_builder=original_plan,schedule=schedule,
                 metadata=dict(kind='rmx220-engine-drums-comparison',live_engine=True,
                               scope='Actual Engine factory48k default profiles/ranges; static pitch/level, effects off, software float output. Other profiles/rates, control automation and FX-coupled drum routing remain unqualified.'))


def regress(args):return compare_cases(args,cases_for(args.case_set),'development_regression')


def compare(args):
    frozen(args);require(sha256(args.session/'predictions.json')==sha256(args.prediction)
        and json.loads((args.session/'matrix.json').read_text())['prediction_sha256']==sha256(args.prediction),'Engine capture prediction copy differs')
    return compare_cases(args,recipe(),'fresh_prediction_bound')


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for command in ('regress','predict','capture','compare'):
        q=commands.add_parser(command);q.add_argument('--renderer',type=Path,required=True)
        if command=='predict':q.add_argument('--report',type=Path,required=True)
        else:
            q.add_argument('--session',type=Path,required=True)
            if command=='regress':q.add_argument('--case-set',choices=DATASETS,required=True)
            else:q.add_argument('--prediction',type=Path,required=True)
            if command=='capture':
                for name in ('host','plugin'):q.add_argument('--'+name,type=Path,required=True)
            else:q.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
