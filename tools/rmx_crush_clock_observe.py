#!/usr/bin/env python3
"""Verify a long original Crush clock replay and reject wrong float grouping."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import checked,recipe


def replay(rows,period):
    f=np.float32;step=f(period-f(np.floor(period)));counter=f(0);fraction=f(0);captures=0;exact=0;first=None
    def advance(value):
        value=f(value+step)
        return f(value-f(1)) if value>=1 else value
    for block,row in enumerate(rows):
        if block:
            for _ in range(32):
                counter=f(counter-f(1))
                if counter<0:
                    counter=f(counter+period)
                    if captures:fraction=advance(fraction)
                    captures+=1
        # A carried fractional interval can be prepared at the next block
        # boundary before its held sample is refreshed. Without the carry,
        # the current fractional state remains visible at this observation.
        prepared=advance(fraction) if block and counter<1 and f(fraction+step)>=1 else fraction
        equal=float(prepared)==row['fraction'];exact+=equal
        if not equal and first is None:first=block
    return dict(period=float(period),exact_blocks=exact,first_mismatch=first)


def analyze(args):
    cases=recipe(args.stage);case=next(c for c in cases if c['name']==args.normal.name)
    require(case['enabled'] and case['effect']==7 and case['route']==0 and case['main'] in (15,31,101),'Requires reviewed input-only Crush case')
    call=copy.copy(args);call.session=args.normal.parent;_,provenance=checked(call,case)
    normal=json.loads((args.normal/'receipt.json').read_text());observed=json.loads((args.observed/'receipt.json').read_text())
    require(observed['complete'] and observed['role']=='reference' and observed['plugin']==normal['plugin'],'Observed identity differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(args.observed/name)==observed[field]==normal[field],'Observed artifact differs: '+name)
    require(all(observed[k]==normal[k] for k in ('input_sha256','host_sha256','maximum_block_size','frames','sample_rate','bpm')),'Observed recipe differs')
    rows=[json.loads(line) for line in args.trace.read_text().splitlines()]
    require(len(rows)==9000 and [r['block'] for r in rows]==list(range(9000)),'Incomplete observation')
    require(rows[0]['held']==[0.,0.],'Initial held sample differs')
    f=np.float32;raw=f(case['main']);scale=f(1/255)
    grouped=replay(rows,max(f(1),f(f(raw*f(24))*scale)))
    rounded=replay(rows,max(f(1),f(f(f(f(raw*f(24))*scale)+f(1))-f(1))))
    former=replay(rows,max(f(1),f(f(raw*scale)*f(24))))
    division=replay(rows,max(f(1),f(f(raw/f(255))*f(24))))
    require(rounded['exact_blocks']==9000,'Corrected clock replay differs')
    rejected=former if case['main']==31 else division if case['main']==101 else grouped
    require(rejected['exact_blocks']<9000,'Wrong grouping was not distinguished')
    save_json(args.report,dict(kind='rmx220-crush-long-clock-scalar-replay',passed=True,original_provenance=provenance,
        observed_receipt_sha256=sha256(args.observed/'receipt.json'),trace_sha256=sha256(args.trace),observer_sha256=sha256(args.observer),analyzer_sha256=sha256(Path(__file__)),
        normal_observed_audio_and_auxiliary_files_byte_identical=True,raw_main=case['main'],blocks=9000,generated_frames=288000,
        float32_grouping='float32(float32(float32(raw *24) * float32(1/255)) +1) -1',rounded_interval=rounded,grouped_without_interval_rounding=grouped,former_normalize_first=former,division_first=division,
        scope='Read-only original scalar component replay for one static48k Crush input-only setting. Main31 distinguishes multiply24-first from normalize-first; Main101 distinguishes reciprocal multiplication from division; Main15 distinguishes the additional interval-boundary rounding. Neither a complete waveform qualification nor a broad-control accuracy claim.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=['fresh-v3','fresh-v4'],default='fresh-v3')
    for key in ('normal','observed','trace','observer','report','host'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(analyze(p.parse_args()))


if __name__=='__main__':main()
