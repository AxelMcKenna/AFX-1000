#!/usr/bin/env python3
"""Record original-only callback timing and float32 cold-start observations."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_reverb_motion import checked, recipe


def state_observations(args,audited):
    if args.trace_root is None and args.startup_session is None:return None
    if args.trace_root is None or args.startup_session is None:raise ValueError('Trace root and startup session are required together')
    result=[];waves,cases=recipe('startup-holdout');all_rows={}
    for index,suffix,first_block,main in [(3,'3',1,144),(4,'4c',1,4),(7,'7',2,129)]:
        case=cases[index]
        _,_,provenance=checked(args.startup_session,case,waves[case['source']])
        if provenance['receipt_sha256']!=audited[('startup-holdout',case['name'])]['receipt_sha256']:
            raise ValueError('State fixture differs from audited capture')
        folder=args.trace_root/('reverb-startup-debug-capture-case'+suffix)
        debug=json.loads((folder/'receipt.json').read_text())
        original=json.loads((args.startup_session/case['name']/'receipt.json').read_text())
        keys=['plugin','role','complete','host_sha256','input_sha256','plan_sha256','output_sha256',
              'sample_rate','frames','maximum_block_size','bpm','tail_seconds']
        if not debug['complete'] or any(debug[k]!=original[k] for k in keys):raise ValueError('Debugger run differs from original fixture')
        if sha256(folder/'audio.wav')!=original['output_sha256']:raise ValueError('Debugger audio differs')
        path=args.trace_root/('reverb-startup-debug-case'+suffix+'.jsonl')
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        if len(rows)!=1100 or any(row['call']!=i for i,row in enumerate(rows)):
            raise ValueError('Incomplete room trace')
        a,b=rows[:2]
        if (a['init']!=1 or a['global_block']!=first_block or a['target_main']!=main
                or b['init'] or b['main']!=main or b['period']!=60 or b['warm']!=32):
            raise ValueError('Room initialization observation differs')
        result.append(dict(case=case['name'],trace_sha256=sha256(path),original_receipt_sha256=provenance['receipt_sha256'],
            debugger_receipt_sha256=sha256(folder/'receipt.json'),debugger_audio_sha256=sha256(folder/'audio.wav'),
            debugger_audio_bit_exact=True,first_room_global_block=first_block,initial_main=main,
            initial_period_blocks=60,traced_calls=len(rows)))
        all_rows[index]=rows
    rows=all_rows[3]
    pairs=[(a,b) for a,b in zip(rows,rows[1:]) if not a['warm_done'] and a['ramp_blocks']>1 and a['pending_main']!=a['main']]
    if not pairs or any(b['ramp_blocks']!=a['ramp_blocks']-1 or b['delay']!=a['delay'] or b['feedback']!=a['feedback'] for a,b in pairs):
        raise ValueError('Muted-state countdown/freeze prediction failed')
    normal=next(i for i,row in enumerate(rows) if row['warm_done'])
    if rows[normal]['delay']==rows[normal+1]['delay']:raise ValueError('Normal moving-read positive control is inconclusive')
    return dict(collection_method='LLDB function-entry scalar reads, without DSP state writes',
        collector_sha256=sha256(args.trace_root/'reverb_startup_debug.py'),cases=result,
        warm_ramp_pairs=len(pairs),clock_counts_down_while_delay_and_feedback_stay_fixed=True,
        delay_moves_after_unmuting=True,
        scope='State observations informed the hypothesis; independently captured full audio supplies waveform acceptance.')


def dry_rounding(args,audited):
    if args.startup_v2_session is None and args.model is None:return None
    if args.startup_v2_session is None or args.model is None:raise ValueError('Second startup session and model are required together')
    waves,cases=recipe('startup-v2-holdout');case=cases[2]
    original,source,provenance=checked(args.startup_v2_session,case,waves[case['source']])
    if provenance['receipt_sha256']!=audited[('startup-v2-holdout',case['name'])]['receipt_sha256']:
        raise ValueError('Dry-rounding fixture differs from audit')
    model=json.loads(args.model.read_text());f=np.float32;raw=case['main']
    def gain(raw):
        u=f(f(max(0,raw-3))*f(1/252))
        return f(2-f(u+u)) if u>f(.5) else f(1)
    current=gain(raw);measured=f(model['main_rows'][raw]['dry_gain'])
    start,stop=1000,2000
    # Fixed nominal bypass offset, after cold fades and before any wet output.
    x=source[start-32:stop-32].astype(f)
    if not np.array_equal(f(x*current),original[start:stop]):raise ValueError('Float dry formula is not bit-exact')
    if np.array_equal(f(x*measured),original[start:stop]):raise ValueError('Measured-gain negative control is inconclusive')
    different=[m for m in range(256) if gain(m)!=f(model['main_rows'][m]['dry_gain'])]
    return provenance|dict(model_sha256=sha256(args.model),raw_main=raw,output_frames=[start,stop],
        source_offset_frames=32,formula_gain=float(current),measured_gain=float(measured),
        formula_bit_exact=True,measured_gain_negative_control_rejected=True,
        calibration_rounding_differences=different,
        scope='Independent direct-only prediction at raw 130; other listed rounding differences are not separate measured validations.')


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
        room_state_observations=state_observations(args,audited),
        dry_rounding_observation=dry_rounding(args,audited),
        scope='Original-only component observations, not independent full-render validation.',
        limitations=['Timing lags are direct-input diagnostics and never change the fixed comparison offsets.',
                    'The full candidate still requires fresh validation of combined early state changes.']))
    print('Verified 17 bypass timing observations and two bit-exact 256-frame cold predictions')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('audit','callbacks','initialization','report'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--trace-root',type=Path)
    p.add_argument('--startup-session',type=Path)
    p.add_argument('--startup-v2-session',type=Path)
    p.add_argument('--model',type=Path)
    analyze(p.parse_args())


if __name__=='__main__':main()
