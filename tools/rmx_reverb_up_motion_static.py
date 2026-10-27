#!/usr/bin/env python3
"""Regress the settled static Up matrix through the stateful motion processor."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_factory_match import new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_characterize import checked
from tools.rmx_reverb_up_model import model_checked,session_recipe
from tools.rmx_reverb_up_motion import source_hashes


def compare(args):
    model_checked(args);root=new_directory(args.output);rows=[];binding=source_hashes();binary=sha256(args.renderer)
    for stage,directory in args.session:
        waves,cases=session_recipe(stage)
        for c in cases:
            receipt,a,x,provenance=checked(directory,c,waves[c['source']]);prefix=stage+'-'+c['name']
            output=root/(prefix+'.wav');dry=root/(prefix+'-dry.wav');schedule=root/(prefix+'.tsv')
            schedule.write_text('RMX_REVERB_MOTION 1\n'+f'initial {c["main"]} {c["amount"]} {c["cutoff"]} 1\n'+f'tail {c["tail"]}\nblock 128\n')
            run([args.renderer,receipt['input_path'],output,schedule,dry]);rate,b=float_wav(output);dry_rate,d=float_wav(dry)
            if rate!=48000 or dry_rate!=rate or len(b)!=len(a)+32 or d.shape!=b.shape:raise ValueError('Static motion fixture extent differs')
            expected=np.zeros_like(d);expected[32:32+len(x)]=x
            if not np.array_equal(d.view(np.uint32),expected.view(np.uint32)):raise ValueError('Settled static dry trace differs from input delayed by 32')
            b=b[32:].astype(float);d=d[32:].astype(float)
            row=provenance|dict(stage=stage,role='prior_static_regression',candidate_sha256=sha256(output),dry_trace_sha256=sha256(dry),schedule_sha256=sha256(schedule),
                whole=screen(a,b),wet=screen(a-d,b-d),post_input_tail=screen(a[len(x):],b[len(x):]),dry_input_delay_bit_exact=True)
            row['passed']=all(row[k]['passed'] for k in ('whole','wet','post_input_tail'));rows.append(row)
            print('PASS' if row['passed'] else 'FAIL',stage,c['name'],flush=True)
    if not rows or source_hashes()!=binding or sha256(args.renderer)!=binary:raise ValueError('Empty or changed static motion candidate')
    save_json(root/'comparison.json',dict(kind='rmx220-reverb-up-motion-static-regressions',passed=all(row['passed'] for row in rows),
        full_reverb_match=False,physical_hardware=False,model_sha256=sha256(args.model),calibration_sha256=sha256(args.calibration),renderer_sha256=binary,
        source_sha256=binding,script_sha256=sha256(Path(__file__)),cases=rows,
        acceptance=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,reference_offset_frames=32,candidate_offset_frames=32,gain_fit=False,wet_alignment_search=False),
        scope='Prior/calibration static Up recordings through the stateful research processor at callback128, with settled silent pre-roll. These are regressions, not new original captures.'))
    return 0 if all(row['passed'] for row in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('model','calibration','renderer','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--session',nargs=2,action='append',required=True)
    args=parser.parse_args();args.session=[(s,Path(d)) for s,d in args.session];raise SystemExit(compare(args))


if __name__=='__main__':main()
