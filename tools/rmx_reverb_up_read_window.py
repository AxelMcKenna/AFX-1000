#!/usr/bin/env python3
"""Corroborate the Up read-window edge with scalar state and retained waveform tests."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256


def emitted_frame(internal_frame,case,extent):
    # Propagate sample labels through the callback adapter. Untouched fallback
    # output has no processed label. Future event frames split callbacks just
    # as in the fixture; no waveform alignment is estimated.
    received=available=head=processed=pending=start=event=0
    while start<extent:
        while event<len(case['events']) and case['events'][event]['frame']==start:event+=1
        count=min(case['block'],extent-start)
        if event<len(case['events']):count=min(count,case['events'][event]['frame']-start)
        read=written=0
        while read<count:
            take=min(32-received,count-read);received+=take;read+=take
            emit=min(available,count-written)
            for index in range(emit):
                if pending+head+index>=internal_frame:return start+written+index
            written+=emit;available-=emit;head+=emit
            if received==32:pending=processed;processed+=32;received=0;available=32;head=0
        start+=count
    raise ValueError('Predicted sample was not emitted')


def verify(args):
    geometry=json.loads(args.geometry.read_text());prediction=json.loads(args.prediction.read_text())
    if geometry['kind']!='rmx220-reverb-up-settled-fractional-scalar-calibration' or not geometry['passed']:raise ValueError('Wrong verified geometry')
    case=next(c for c in prediction['cases'] if c['name']==args.case)
    event=next(e for e in case['events'] if e['frame']==args.event_frame and e['control']=='main')
    previous=[e['value'] for e in case['events'] if e['control']=='main' and e['frame']<args.event_frame]
    if not previous or previous[-1]!=0 or event['value']<=3:raise ValueError('Component replay requires a settled Main0 re-entry')
    padding=[json.loads(line) for line in args.padding_log.read_text().splitlines()]
    transfers=[json.loads(line) for line in args.transfer_log.read_text().splitlines()]
    if len(padding)!=350 or any(c['cache_padding_nonzero'] or c['cache_padding_maximum'] for c in padding):raise ValueError('Cache padding observation differs')
    if len(transfers)!=8 or any(c['samples']!=40 or c['element_bytes']!=4 or c['destination_offset_in_slot'] for c in transfers) or {c['cache_slot'] for c in transfers}!=set(range(4)):raise ValueError('Read transfer observation differs')
    original_receipt=json.loads((args.original/'receipt.json').read_text());original_audio=sha256(args.original/'audio.wav')
    for folder in (args.padding_debugger,args.transfer_debugger):
        receipt=json.loads((folder/'receipt.json').read_text())
        if not receipt['complete'] or any(receipt[k]!=original_receipt[k] for k in ('input_sha256','plan_sha256','output_sha256','host_sha256')) or sha256(folder/'audio.wav')!=original_audio:raise ValueError('Debugger original audio/plan/input/host differs')
    initial=padding[0]
    if initial['main']!=0 or initial['pending_main']!=0 or initial['ramp_blocks']:raise ValueError('Replay initial state is not settled Main0')
    cur=np.array(geometry['cases'][0]['delays'],dtype=np.float32);period=initial['period'];slow=pending=0;blocks=remaining=0;first=None;count=0;maximum=0
    first_block=args.event_frame//32
    for block in range(first_block,first_block+250):
        if not blocks and slow!=event['value']:
            desired=15-min(5,abs(event['value']-slow));period+=-1 if period>desired else 1 if period<desired else 0
            pending=slow+(1 if slow<event['value'] else -1);blocks=period;remaining=period*32
            target=np.array(geometry['cases'][pending]['delays'],dtype=np.float32);step=(target-cur)*np.float32(1/remaining)
        start=cur.astype(int)
        for sample in range(32):
            indices=1+sample+start-cur.astype(int);outside=indices>=40;maximum=max(maximum,int(indices.max()))
            if np.any(outside):
                if first is None:first=block*32+sample
                count+=int(np.count_nonzero(outside))
            if remaining:
                cur=(cur+step).astype(np.float32);remaining-=1
                if not remaining:cur=target.copy()
        if blocks:
            blocks-=1
            if not blocks:slow=pending
    reports=[json.loads(p.read_text()) for p in (args.before,args.after)];records=[next(c for c in d['cases'] if c['case']==args.case and c['stage']=='holdout') for d in reports]
    audio=[]
    for path,row in zip((args.before,args.after),records):
        wav=path.parent/('holdout-'+args.case+'.wav')
        if sha256(wav)!=row['candidate_sha256']:raise ValueError('Candidate output hash differs')
        audio.append(float_wav(wav)[1][32:])
    physical=emitted_frame(first,case,len(audio[0])+32);aligned=physical-32
    differences=np.flatnonzero(np.any(audio[0].view(np.uint32)!=audio[1].view(np.uint32),axis=1))
    if not len(differences) or int(differences[0])!=aligned:raise ValueError(f'Predicted first sample {aligned} differs from observed {int(differences[0]) if len(differences) else None}')
    windows=[next(w for w in row['event_windows'] if w['frame']==args.event_frame)['wet'] for row in records]
    if windows[0]['passed'] or not windows[1]['passed']:raise ValueError('Retained negative/corrected waveform gates differ')
    save_json(args.report,dict(kind='rmx220-reverb-up-read-window-corroboration',passed=True,script_sha256=sha256(Path(__file__)),
        geometry_sha256=sha256(args.geometry),prediction_sha256=sha256(args.prediction),case=args.case,event_frame=args.event_frame,
        reference_receipt_sha256=sha256(args.original/'receipt.json'),original_audio_sha256=original_audio,
        padding=dict(script_sha256=sha256(args.padding_script),log_sha256=sha256(args.padding_log),receipt_sha256=sha256(args.padding_debugger/'receipt.json'),observed_blocks=len(padding),cache_slots=4,checked_padding_values_per_block=96,all_zero=True,audio_byte_identical=True),
        read_operations=dict(script_sha256=sha256(args.transfer_script),log_sha256=sha256(args.transfer_log),receipt_sha256=sha256(args.transfer_debugger/'receipt.json'),observations=transfers,audio_byte_identical=True),
        initial_main_period_blocks=initial['period'],read_window_frames=40,internal_block_frames=32,
        predicted_first_outside_window_internal_frame=first,predicted_first_changed_physical_frame=physical,
        predicted_first_changed_frame_after_declared_crop=aligned,observed_first_changed_frame=int(differences[0]),
        candidate_offset_frames=32,callback_timing_generated_from_declared_schedule=True,wet_alignment_search=False,
        replayed_blocks=250,outside_window_tap_samples=count,maximum_read_index=maximum,
        old_comparison_sha256=sha256(args.before),corrected_comparison_sha256=sha256(args.after),
        old_candidate_sha256=records[0]['candidate_sha256'],corrected_candidate_sha256=records[1]['candidate_sha256'],
        rejected_old_event_wet=windows[0],corrected_event_wet=windows[1],
        scope='Independent numeric read-window observation and a replay from separate settled geometry predict the exact first output changed by the correction. The first holdout becomes regression evidence for the corrected candidate; further fresh waveforms remain required. No original instructions, binary or raw debugger output is distributed.'))
    print('40-sample read window; first overrun at internal',first,'emits at physical',physical,'and matches cropped output frame',aligned)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('geometry','prediction','original','padding-log','padding-script','padding-debugger','transfer-log','transfer-script','transfer-debugger','before','after','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--case',required=True);p.add_argument('--event-frame',type=int,required=True)
    verify(p.parse_args())


if __name__=='__main__':main()
