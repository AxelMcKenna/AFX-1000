#!/usr/bin/env python3
"""Retain the first frozen kick prediction's failed control check and score valid cases."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_drums import checked, require
from tools.rmx_kick_validate import frozen, recipe, source_hashes, ACCEPTANCE


def audit(args):
    frozen(args);root=new_directory(args.output);rows=[]
    for c in recipe():
        try:raw_a,provenance=checked(args.session,c)
        except ValueError as error:
            require(c['name']=='kick-holdout-0' and str(error)=='Drum immediate readback differs','Unexpected original capture rejection')
            folder=args.session/c['name'];receipt=json.loads((folder/'receipt.json').read_text());plan=json.loads((folder/'plan.json').read_text())
            log=json.loads((folder/'parameter-log.json').read_text())['entries'];expected=[p|dict(frame=-1) for p in plan['parameters']]+plan['events']
            mismatch=[dict(requested=req,actual=actual) for req,actual in zip(expected,log) if abs(actual['immediate_readback']-float(np.float32(req['value'])))>1e-14]
            require(len(mismatch)==1 and mismatch[0]['requested']['frame']==0 and mismatch[0]['requested']['name']=='KickButton'
                    and mismatch[0]['requested']['value']==1 and mismatch[0]['actual']['immediate_readback']==0,'Cold-control rejection differs')
            rows.append(dict(case=c['name'],capture_verified=False,passed=False,waveform_scored=False,receipt_sha256=sha256(folder/'receipt.json'),
                             mismatch=mismatch,output_sha256=receipt['output_sha256']))
            print('REJECTED original frame-zero control',c['name'],flush=True);continue
        plan=root/(c['name']+'.tsv');output=root/(c['name']+'.wav');dry_path=root/(c['name']+'-dry.wav')
        plan.write_text('RMX_DRUM 1\n'+f'0 128 128 {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits']))
        run([args.renderer,args.session/'silence.wav',output,plan,dry_path]);rate,raw_b=float_wav(output);dry_rate,dry=float_wav(dry_path)
        require(rate==dry_rate==48000 and raw_a.shape==raw_b.shape==dry.shape and not np.any(dry),'Candidate extent/rate/dry differs')
        a,b=raw_a[32:].astype(float),raw_b[32:].astype(float)
        row=provenance|dict(capture_verified=True,waveform_scored=True,candidate_sha256=sha256(output),dry_trace_sha256=sha256(dry_path),
                           schedule_sha256=sha256(plan),whole=screen(a,b),windows=[])
        for at in c['hits']:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                right=min(len(a),right)
                if right>left:row['windows'].append(dict(kind=kind,frame=at,start=left,stop=right,score=screen(a[left:right],b[left:right])))
        row['passed']=row['whole']['passed'] and all(w['score']['passed'] for w in row['windows']);rows.append(row)
        print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    frozen(args)
    save_json(root/'verification.json',dict(kind='rmx220-kick-first-prospective-audit',passed=all(row['passed'] for row in rows),
              expected_cases=8,scored_cases=sum(row['waveform_scored'] for row in rows),prediction_sha256=sha256(args.prediction),
              source_sha256=source_hashes(),script_sha256=sha256(Path(__file__)),acceptance=ACCEPTANCE,cases=rows,
              scope='First eight-case frozen prediction does not pass. The frame-zero command was rejected by the original, so that case fails the strict capture contract and is not waveform-scored. Remaining original-verified cases retain every waveform gate. No capture or score threshold is relaxed.'))
    return 0 if all(row['passed'] for row in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('renderer','prediction','session','output'):parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
