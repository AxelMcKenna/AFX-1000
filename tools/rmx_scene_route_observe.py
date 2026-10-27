#!/usr/bin/env python3
"""Verify an unchanged debugger render and replay scalar source/Scene startup ramps."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require


def analyze(args):
    normal=json.loads((args.normal/'receipt.json').read_text());observed=json.loads((args.observed/'receipt.json').read_text())
    require(normal['complete'] and observed['complete'] and normal['role']==observed['role']=='reference','Incomplete original capture')
    require(observed['plugin']==normal['plugin'],'Observed original identity differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(args.normal/name)==normal[field]==sha256(args.observed/name)==observed[field],'Observed artifact differs: '+name)
    require(all(normal[k]==observed[k] for k in ('input_sha256','host_sha256','maximum_block_size','frames','sample_rate','bpm')),'Observed recipe differs')
    for member in normal['plugin']['binary_files']:require(sha256(Path(normal['plugin']['bundle'])/member['path'])==member['sha256'],'Original binary differs')
    rows=[json.loads(line) for line in args.trace.read_text().splitlines()];stages={name:[r for r in rows if r['stage']==name] for name in ('source','scene','scene_end')}
    require(len(rows)==192 and all([r['block'] for r in group]==list(range(64)) for group in stages.values()),'Incomplete scalar observation')
    plan=json.loads((args.normal/'plan.json').read_text());values={p['name']:p['value'] for p in plan['parameters']}
    require(values['HpfEchoButton']==1 and values['InputButton']==0 and values['XpadButton']==1 and normal['maximum_block_size']==521,'Requires reviewed HPF/X-Pad startup case')
    f=np.float32;unit=f(.00625);progress=f(0);source_exact=0;source_values=[]
    for i,r in enumerate(stages['scene']):
        if i<5:
            for _ in range(32):progress=f(progress+unit)
            if i==4:progress=f(1)
        expected=[float(progress),0.,0.,float(progress)];actual=[r['source_gains'][j] for j in (1,4,7,10)]
        source_exact+=expected==actual;source_values.append(actual)
    require(source_exact==64,'Source ramp replay differs')
    mix=f(0);step=unit;wet_exact=0;wet_values=[]
    for i,r in enumerate(stages['scene_end']):
        if i==1:step=f(f(f(1)-mix)*unit)
        if i<=5:
            for _ in range(32):mix=f(mix+step)
            if i==5:mix=f(1);step=f(0)
        wet_exact+=r['scene_mix'][4:]==[float(mix),float(step)];wet_values.append(r['scene_mix'][4:])
    require(wet_exact==64,'Scene wet ramp replay differs')
    target=f(stages['scene_end'][1]['scene_direct'][1]);current=f(1);step=f(0);direct_exact=0;direct_values=[]
    for i,r in enumerate(stages['scene_end']):
        if i in (1,2):step=f(f(target-current)*unit)
        if 1<=i<=6:
            for _ in range(32):current=f(current+step)
            if i==6:current=target;step=f(0)
        expected=[float(current),1. if i==0 else float(target),float(step)]
        direct_exact+=r['scene_direct']==expected;direct_values.append(r['scene_direct'])
    require(direct_exact==64,'Scene direct ramp replay differs')
    save_json(args.report,dict(kind='rmx220-source-scene-startup-scalar-replay',passed=True,normal_receipt_sha256=sha256(args.normal/'receipt.json'),
        observed_receipt_sha256=sha256(args.observed/'receipt.json'),trace_sha256=sha256(args.trace),observer_sha256=sha256(args.observer),analyzer_sha256=sha256(Path(__file__)),
        normal_observed_audio_and_auxiliary_files_byte_identical=True,stages=3,blocks_per_stage=64,
        source=dict(exact_blocks=source_exact,order=['unselected_input','unselected_pad','selected_input','selected_pad'],block_end_gains=source_values),
        wet_mix=dict(exact_blocks=wet_exact,block_end_value_step=wet_values),
        direct_mix=dict(exact_blocks=direct_exact,observed_target=float(target),block_end_current_target_step=direct_values,uses_observed_target=True),
        scope='Read-only component observation and exact float32 ramp replay for one HPF/X-Pad cold case,521-frame callbacks. Direct replay uses its observed target; this is not autonomous coefficient prediction or complete waveform acceptance. Original audio, binaries, raw scalar trace and instruction listings remain local ignored artifacts.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('normal','observed','trace','observer','report'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(analyze(p.parse_args()))


if __name__=='__main__':main()
