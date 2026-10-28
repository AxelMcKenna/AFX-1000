#!/usr/bin/env python3
"""Recheck prior original drum corpora after a sound-model change; never rebind old predictions."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_default_parity import DATASETS
from tools import rmx_drums_engine as dry
from tools import rmx_drums_motion as motion
from tools import rmx_drums_fx as fx
from tools.rmx_drums_roll import source_hashes
from tools.rmx_factory_match import new_directory


def run(args):
    binding=source_hashes();script=sha256(Path(__file__));root=new_directory(args.output);records=[]
    jobs=[]
    if args.group in ['all','dry']:
        for name,_,session in DATASETS:jobs.append(('dry',name,args.prior_root/session,None))
    if args.group in ['all','motion']:
        for name,session in [('discovery','rmx-drums-motion-discovery-20261028'),('fresh','rmx-drums-motion-holdout-20261028')]:
            jobs.append(('motion',name,args.prior_root/session,args.prior_root/'drums-motion-predictions-v1.json' if name=='fresh' else None))
    if args.group in ['all','fx']:
        jobs.append(('fx','discovery',args.prior_root/'rmx-drums-fx-discovery-20261027',None))
        for i,stage in enumerate(['fresh','fresh-v2','fresh-v3','fresh-v4','fresh-v5','fresh-v6'],1):
            suffix='' if i==1 else str(i);date='20261027' if i==1 else '20261028'
            jobs.append(('fx',stage,args.prior_root/f'rmx-drums-fx-shared-holdout{suffix}-{date}',args.prior_root/f'drums-fx-shared-predictions-v{i}.json'))
        base=args.prior_root/'rmx-live-integration-20261028'
        jobs.append(('fx','live-fresh',base/'originals/rmx-drums-fx-live-holdout-20261028',base/'live-engine-predictions-v1.json'))
    for group,name,session,prediction in jobs:
        out=root/(group+'-'+name)
        if group=='dry':
            call=SimpleNamespace(session=session,renderer=args.core/'rmx_drum_probe',output=out)
            dry.compare_cases(call,dry.recipe() if name=='fresh' else dry.cases_for(name),'development_regression')
        elif group=='motion':
            call=SimpleNamespace(session=session,host=args.host,stage=name,renderer=args.core/'rmx_drum_motion_probe',sanitized=args.asan/'rmx_drum_motion_probe',output=out,
              prediction=prediction,regression=name=='fresh')
            motion.compare(call)
        else:
            call=SimpleNamespace(session=session,host=args.host,stage=name,renderer=args.core/'rmx_drums_fx_probe',output=out,prediction=prediction,regression=name!='discovery',backend='engine')
            fx.compare(call)
        path=out/'comparison.json';d=json.loads(path.read_text());cases=d['cases']
        records.append(dict(group=group,stage=name,session=str(session),comparison=str(path),comparison_sha256=sha256(path),passed=d['passed'],
          programs=len(cases),passed_programs=sum(c['passed'] for c in cases),failures=[dict(case=c['case'],whole=c['whole'],**({k:c[k] for k in ['wet','tail']} if group=='fx' else {}),
            failed_windows=[w for w in c['windows'] if (not w['score']['passed'] if 'score' in w else not w['whole']['passed'] or not w['wet']['passed'])]) for c in cases if not c['passed']]))
        print('DATASET_COMPLETE',group,name,records[-1]['passed_programs'],'/',len(cases),flush=True)
    require(binding==source_hashes() and script==sha256(Path(__file__)),'Regression source changed')
    save_json(root/'verification.json',dict(kind='rmx-drums-roll-prior-original-regressions',passed=all(d['passed'] for d in records),programs=sum(d['programs'] for d in records),passed_programs=sum(d['passed_programs'] for d in records),datasets=records,
      source_sha256=binding,script_sha256=script,scope='Prior original corpora rescored with unchanged gates after the kick filter-state correction. Old predictions retain their recipe/gate checks and historical identity; these are regressions, not newly frozen holdouts or byte-parity claims. Per-dataset full comparisons are hashed and retained locally.'))
    return 0 if all(d['passed'] for d in records) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['core','asan','host','prior-root','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--group',choices=['all','dry','motion','fx'],default='all')
    raise SystemExit(run(p.parse_args()))


if __name__=='__main__':main()
