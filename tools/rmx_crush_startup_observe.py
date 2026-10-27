#!/usr/bin/env python3
"""Verify original Crush startup scalars and its prepared fractional hold clock."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import checked,recipe


def analyze(args):
    case=next(c for c in recipe('fresh') if c['name']==args.normal.name)
    require(case['effect']==7 and case['route']==1 and case['block']==3089,'Requires reviewed Crush/X-Pad case')
    call=copy.copy(args);call.session=args.normal.parent;call.stage='fresh';_,provenance=checked(call,case)
    normal=json.loads((args.normal/'receipt.json').read_text());observed=json.loads((args.observed/'receipt.json').read_text())
    require(observed['complete'] and observed['role']=='reference' and observed['plugin']==normal['plugin'],'Observed identity differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(args.observed/name)==observed[field]==normal[field],'Observed artifact differs: '+name)
    require(all(observed[k]==normal[k] for k in ('input_sha256','host_sha256','maximum_block_size','frames','sample_rate','bpm')),'Observed recipe differs')
    rows=[json.loads(line) for line in args.trace.read_text().splitlines()];stages={name:[r for r in rows if r['stage']==name] for name in ('source','scene','scene_end','return_input')}
    require(len(rows)==256 and all([r['block'] for r in group]==list(range(64)) for group in stages.values()),'Incomplete observation')
    f=np.float32;period=max(f(1),f(f(f(case['main'])*f(1/255))*f(24)));fraction_step=f(period-f(np.floor(period)));fraction=counter=progress=f(0);captures=plain_exact=prepared_exact=startup_exact=input_exact=0;states=[]
    def advance(value):
        value=f(value+fraction_step)
        if value>=1:value=f(value-f(1))
        return value
    for block,row in enumerate(stages['scene_end']):
        if block:
            for _ in range(32):
                counter=f(counter-f(1))
                if counter<0:
                    counter=f(counter+period)
                    if captures:fraction=advance(fraction)
                    captures+=1
        prepared=advance(fraction) if block and counter<1 else fraction
        observed_fraction=row['crush_hold'][0];plain_exact+=float(fraction)==observed_fraction;prepared_exact+=float(prepared)==observed_fraction
        step=f(.00625) if 1<=block<5 else f(0)
        if 1<=block<=5:
            for _ in range(32):progress=f(progress+f(.00625))
            if block==5:progress=f(1)
        startup_exact+=row['effect_startup']==[float(step),float(progress)]
        input_exact+=row['effect_input_gain']==float(progress)
        states.append(dict(block=block,observed_fraction=observed_fraction,plain_prediction=float(fraction),prepared_prediction=float(prepared),countdown=float(counter),observed_effect_startup=row['effect_startup'],observed_input_gain=row['effect_input_gain']))
    require(prepared_exact==startup_exact==input_exact==64 and plain_exact==60,'Hold/startup replay differs')
    require(stages['scene_end'][0]['crush_hold'][1:]==[0.,0.],'Initial held sample is not reset')
    save_json(args.report,dict(kind='rmx220-crush-startup-scalar-replay',passed=True,original_provenance=provenance,observed_receipt_sha256=sha256(args.observed/'receipt.json'),
        trace_sha256=sha256(args.trace),observer_sha256=sha256(args.observer),analyzer_sha256=sha256(Path(__file__)),normal_observed_audio_and_auxiliary_files_byte_identical=True,
        stages=4,blocks_per_stage=64,raw_main=case['main'],fractional_hold_period=float(period),float32_grouping='float32(float32(raw * float32(1/255)) *24)',
        plain_fraction_exact_blocks=plain_exact,prepared_fraction_exact_blocks=prepared_exact,effect_startup_exact_blocks=startup_exact,effect_input_gain_exact_blocks=input_exact,states=states,
        scope='Read-only scalar replay for one Crush/X-Pad cold case. The fractional state prepares the following interval when its next capture falls at the block boundary; the unprepared interpretation fails four states. Initial held state is zero. Separate input gain and effect-startup gain each follow the same160-sample ramp in this activation. This establishes clock/startup component facts, not a complete audio or broad-control match.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('normal','observed','trace','observer','report','host'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(analyze(p.parse_args()))


if __name__=='__main__':main()
