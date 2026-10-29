#!/usr/bin/env python3
"""Verify complete float32 sample-bit identity across the three Release corpora."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tools import rmx_release as release
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',nargs=5,action='append',metavar=('STAGE','SESSION','COMPARISON','AUDIT','PREDICTION'),required=True)
    for key in ['host','renderer','report']:p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();binding=release.source_hashes();script=sha256(Path(__file__));rows=[];reports={}
    require([d[0] for d in args.dataset]==['discovery','fresh','fresh-v2'],'Expected all three complete corpora')
    for stage,session,comparison,audit,prediction in args.dataset:
        path=Path(comparison);d=json.loads(path.read_text());ap=Path(audit);v=json.loads(ap.read_text());reports[str(path)]=sha256(path);reports[str(ap)]=sha256(ap)
        require(d['passed'] and v['passed'] and d['source_sha256']==v['source_sha256']==binding and d['renderer_sha256']==sha256(args.renderer) and v['comparison_sha256']==sha256(path),'Qualified comparison/audit differs')
        cases=release.recipe(stage);require([c['name'] for c in cases]==[r['case'] for r in d['cases']],'Coverage differs')
        call=SimpleNamespace(stage=stage,session=Path(session),host=args.host,prediction=Path(prediction) if stage!='discovery' else None)
        for c,row in zip(cases,d['cases'],strict=True):
            a,provenance=release.original(call,c);require(all(row[k]==v for k,v in provenance.items()),'Original binding differs');out=path.parent/(c['name']+'.wav');require(sha256(out)==row['candidate_sha256'],'Candidate changed');rate,b=float_wav(out)
            require(rate==48000 and a.shape==b.shape==(release.FRAMES,2),'Extent differs');require(np.array_equal(a.view('<u4'),b.view('<u4')),'Sample bits differ: '+c['name'])
            rows.append(provenance|dict(stage=stage,candidate_sha256=row['candidate_sha256'],frames=release.FRAMES,float32_sample_bits_identical=True,pcm_sha256=hashlib.sha256(a.tobytes()).hexdigest()))
    require(len(rows)==216 and binding==release.source_hashes() and script==sha256(Path(__file__)),'Coverage/source changed')
    save_json(args.report,dict(kind='rmx220-release-complete-float32-bit-identity',passed=True,programs=216,frames_per_program=release.FRAMES,stereo_screens=1848,source_sha256=binding,verifier_sha256=script,renderer_sha256=sha256(args.renderer),reports_sha256=reports,cases=rows,scope='Every float32 sample bit in each complete stereo native render equals the original, including the first32 startup frames. No trim, gain fit, alignment search or tolerance is used for this extra identity check. 40 discovery,88 development/former-fresh and88 prospectively frozen unseen programs; default48k/120BPM only. WAV container bytes differ; wrappers use separately declared delivery tolerances.'))


if __name__=='__main__':main()
