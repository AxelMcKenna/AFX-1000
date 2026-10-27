#!/usr/bin/env python3
"""Check that shared-FX API changes preserve all224 previously qualified dry Engine programs."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import source_hashes
from tools.rmx_factory_match import new_directory,run

DATASETS=[
    ('controls','drums-engine-controls-v2','rmx-drum-controls-20261027'),
    ('discovery','drums-engine-discovery-v2','rmx-drums-discovery-20261027'),
    ('kick-first','drums-engine-kick-first-v2','rmx-kick-holdout-20261027'),
    ('kick-cold','drums-engine-kick-cold-v2','rmx-kick-cold-holdout-20261027'),
    ('snare','drums-engine-snare-v2','rmx-snare-holdout-20261027'),
    ('clap','drums-engine-clap-v2','rmx-clap-holdout-20261027'),
    ('hat','drums-engine-hat-v2','rmx-hat-holdout-20261027'),
    ('control-first','drums-engine-control-first-v2','rmx-drums-controls-holdout-20261027'),
    ('control-cold','drums-engine-control-cold-v2','rmx-drums-controls-cold-holdout-20261027'),
    ('fresh','drums-engine-validation-v1','rmx-drums-engine-holdout-20261027')]


def audit(args):
    root=new_directory(args.output);binding=source_hashes();binary=sha256(args.renderer);rows=[]
    for name,folder,session in DATASETS:
        filename='2026-10-27-drums-engine-'+('holdout' if name=='fresh' else 'regression-'+name)+'.json'
        report_path=Path('research/audio/measurements')/filename;d=json.loads(report_path.read_text())
        require(d['passed'] and d['live_engine'],'Prior Engine report not qualified')
        for old in d['cases']:
            case=old['case'];plan=args.prior_root/folder/(case+'.tsv');prior=args.prior_root/folder/(case+'.wav');source=args.prior_root/session/'silence.wav'
            require(sha256(plan)==old['schedule_sha256'] and sha256(prior)==old['candidate_sha256'] and sha256(source)==old['input_sha256'],'Prior artifacts differ')
            output=root/(case+'.wav');dry=root/(case+'-dry.wav');run([args.renderer,source,output,plan,dry])
            rate,a=float_wav(prior);other_rate,b=float_wav(output);dry_rate,trace=float_wav(dry)
            require(rate==other_rate==dry_rate==48000 and a.shape==b.shape==trace.shape and not np.any(trace),'New Engine extent/dry differs')
            require(np.array_equal(a,b),'Default dry Engine audio changed')
            rows.append(dict(case=case,prior_report_sha256=sha256(report_path),prior_candidate_sha256=old['candidate_sha256'],candidate_sha256=sha256(output),
                dry_sha256=sha256(dry),numeric_exact=True,byte_exact=sha256(output)==old['candidate_sha256']))
            print('UNCHANGED',case,flush=True)
    require(len(rows)==224 and binding==source_hashes() and binary==sha256(args.renderer),'Coverage/candidate changed')
    save_json(root/'verification.json',dict(kind='rmx-drums-default-engine-parity',passed=True,cases=rows,numeric_exact_programs=len(rows),byte_exact_programs=sum(r['byte_exact'] for r in rows),
        source_sha256=binding,renderer_sha256=binary,auditor_sha256=sha256(Path(__file__)),scope='PCM parity against all224 previously qualified dry Engine renders, using their committed report hashes and verified old local artifacts. Confirms default-path compatibility; not224 new originals, a new sound-match claim or combined live Engine FX qualification.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('renderer','prior-root','output'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(audit(p.parse_args()))


if __name__=='__main__':main()
