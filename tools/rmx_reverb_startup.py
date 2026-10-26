#!/usr/bin/env python3
"""Record original-only callback timing and float32 cold-start observations."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_reverb_motion import checked, recipe


def analyze(args):
    audit=json.loads(args.audit.read_text())
    if not audit['passed']:raise ValueError('Requires completed capture audit')
    audited={(row['stage'],row['case']):row for row in audit['capture_cases']}
    observations=[]
    for stage,session in [('callback-probes',args.callbacks),('initialization-probes',args.initialization)]:
        waves,cases=recipe(stage)
        for case in cases:
            original,source,provenance=checked(session,case,waves[case['source']])
            if audited[(stage,case['name'])]['receipt_sha256']!=provenance['receipt_sha256']:
                raise ValueError('Capture differs from audited provenance')
            if stage=='callback-probes' and not case['enabled']:
                # Bypass-only source equality, reported separately from every
                # fixed-offset wet/whole acceptance test. No gain is fitted.
                start,stop=24000,26000
                lags=[lag for lag in range(65) if np.array_equal(original[start+lag:stop+lag],source[start:stop])]
                predicted=32 if not case['events'] else case['events'][0]['frame']%32 or 32
                if lags!=[predicted]:raise ValueError('Callback timing prediction failed')
                observations.append(provenance|dict(stage=stage,maximum_block_size=case['block'],
                    first_event_frame=case['events'][0]['frame'] if case['events'] else None,
                    direct_input_frames=[start,stop],bit_exact_direct_input_lags=lags,
                    predicted_lag_frames=predicted,scope='Bypass timing diagnostic; acceptance offsets remain 32.'))

    f=np.float32
    q=np.ones(256,dtype=f);value=f(0)
    for n in range(160):value=f(value+f(.00625));q[n]=value
    dry=np.ones(256,dtype=f);value=f(1)
    for n in range(32,64):value=f(value-f(.00625));dry[n]=value
    step=f((f(0)-value)/f(160))
    for n in range(64,224):value=f(value+step);dry[n]=value
    dry[224:]=0
    cold=[]
    waves,cases=recipe('initialization-probes')
    for case in cases:
        original,source,provenance=checked(args.initialization,case,waves[case['source']])
        x=source[:256].astype(f)
        routed=f(f(x*q[:,None])*q[:,None])
        rendered=f(routed*(dry[:,None] if case['main']==255 else f(1)))
        predicted=rendered.copy();predicted[96:128]=x[96:128];predicted[128:]=rendered[96:224]
        if not np.array_equal(predicted,original[:256]):raise ValueError('Cold dry prediction is not bit-exact')
        combined=f(x*f(q*q)[:,None])
        if case['main']==255:combined=f(combined*dry[:,None])
        if np.array_equal(combined[:96],original[:96]):raise ValueError('Combined-multiply negative control is inconclusive')
        restart_rejected=None
        if case['main']==255:
            wrong=np.ones(256,dtype=f);value=f(1)
            for n in range(32,192):value=f(value-f(.00625));wrong[n]=value
            wrong[192:]=0
            restart_rejected=not np.array_equal(f(routed[:96]*wrong[:96,None]),original[:96])
            if not restart_rejected:raise ValueError('Dry restart negative control is inconclusive')
        cold.append(provenance|dict(predicted_frames=[0,256],bit_exact=True,
            two_float32_multiplications_required=True,combined_multiply_negative_control_rejected=True,
            unprocessed_first_callback_frames=[96,128],callback_size=128,
            dry_restart_input_frame=64 if case['main']==255 else None))
        cold[-1]['dry_restart_negative_control_rejected']=restart_rejected
    save_json(args.report,dict(kind='rmx220-original-reverb-startup-observations',sample_rate=48000,
        full_reverb_match=False,physical_hardware=False,audit_sha256=sha256(args.audit),
        script_sha256=sha256(Path(__file__)),callback_timing=observations,cold_dry_predictions=cold,
        scope='Original-only component observations, not independent full-render validation.',
        limitations=['Timing lags are direct-input diagnostics and never change the fixed comparison offsets.',
                    'The full candidate still requires fresh validation of combined early state changes.']))
    print('Verified 17 bypass timing observations and two bit-exact 256-frame cold predictions')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('audit','callbacks','initialization','report'):p.add_argument('--'+name,type=Path,required=True)
    analyze(p.parse_args())


if __name__=='__main__':main()
