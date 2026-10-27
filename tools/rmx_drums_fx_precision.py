#!/usr/bin/env python3
"""Diagnose a near-null wet subtraction with independent zero-input captures.

The same known Crush/X-Pad program is frozen with zero external input. This
preserves its FX source while removing the strong unselected bus from the
float32 output sum. The earlier mixed-input failure is never relabeled.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256,write_wav
from tools.rmx_drums import require
from tools.rmx_drums_fx import ACCEPTANCE,FRAMES,checked,frozen as native_frozen,plan_for,recipe,schedule,source_hashes
from tools.rmx_factory_match import IDENTITY,new_directory,run
from tools.rmx_filter_match import screen


def cases():
    base=next(c for c in recipe('live-fresh') if c['name']=='drum-fx-live-effect7-route1')
    dry='crush151-zero-input-dry';on='crush151-zero-input-on'
    return [base|dict(name=dry,baseline=dry,effect=1,enabled=0),base|dict(name=on,baseline=dry)]


def payload(args):
    call=copy.copy(args);call.stage='live-fresh';call.backend='engine';call.prediction=args.native_prediction;native_frozen(call)
    previous=json.loads(args.native_comparison.read_text())
    require(previous['backend']=='engine' and previous['source_sha256']==source_hashes() and previous['renderer_sha256']==sha256(args.renderer) and previous['prediction_sha256']==sha256(args.native_prediction),'Native comparison binding differs')
    failed=next(c for c in previous['cases'] if c['case']=='drum-fx-live-effect7-route1')
    require(not failed['passed'],'Requires retained mixed-input failure')
    return dict(kind='rmx-drums-fx-zero-input-precision-prediction',cases=cases(),source_sha256=source_hashes(),
        script_sha256=sha256(Path(__file__)),renderer_sha256=sha256(args.renderer),sanitized_sha256=sha256(args.sanitized),
        native_prediction_sha256=sha256(args.native_prediction),native_comparison_sha256=sha256(args.native_comparison),
        source_samples_sha256=hashlib.sha256(np.zeros((FRAMES,2),dtype='<f4').tobytes()).hexdigest(),acceptance=ACCEPTANCE,
        expected='Both independent zero-input programs pass unchanged whole/wet/tail and attack/body/decay waveform gates. The late mixed-output float32 sums can be reconstructed from their separate unselected baseline and isolated FX output.',
        scope='Precision diagnostic at one known failed setting, not an unseen-control holdout or a revised acceptance policy. Zero external input is unselected from FX in this route. The original mixed-input failure remains a failure.')


def frozen(args):require(json.loads(args.prediction.read_text())==payload(args),'Precision prediction differs')


def capture(args):
    frozen(args);root=new_directory(args.session);inventory=json.loads(run([args.host,'inventory',args.plugin]))
    require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original')
    save_json(root/'inventory.json',inventory);write_wav(root/'zero.wav',48000,np.zeros(FRAMES*2,dtype='<f4'))
    (root/'predictions.json').write_bytes(args.prediction.read_bytes());rows=[]
    for c in cases():
        plan=root/(c['name']+'.json');save_json(plan,plan_for(c,inventory));run([args.host,'render',args.plugin,root/'zero.wav',plan,root/c['name'],c['block']])
        rows.append(c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json')))
    frozen(args);save_json(root/'matrix.json',dict(kind='rmx-zero-input-precision-originals',prediction_sha256=sha256(args.prediction),cases=rows));return 0


def original(args,c):
    root=args.session;folder=root/c['name'];receipt=json.loads((folder/'receipt.json').read_text());inventory=json.loads((root/'inventory.json').read_text());matrix=json.loads((root/'matrix.json').read_text())
    require(receipt['complete'] and receipt['role']=='reference' and all(receipt['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong original identity')
    require(matrix['prediction_sha256']==sha256(args.prediction)==sha256(root/'predictions.json'),'Original prediction differs')
    require(next(r for r in matrix['cases'] if r['name']==c['name'])==c|dict(receipt_sha256=sha256(folder/'receipt.json')),'Matrix recipe differs')
    require(receipt['host_sha256']==sha256(args.host) and receipt['maximum_block_size']==c['block'] and receipt['frames']==FRAMES and receipt['sample_rate']==48000 and receipt['reported_latency_frames']==0,'Original timing/host differs')
    require(json.loads((folder/'plan.json').read_text())==plan_for(c,inventory) and sha256(root/(c['name']+'.json'))==receipt['plan_sha256'],'Original plan differs')
    for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
        require(sha256(folder/name)==receipt[field],'Original artifact differs: '+name)
    require(sha256(root/'zero.wav')==sha256(Path(receipt['input_path']))==receipt['input_sha256'],'Input binding differs')
    rate,x=float_wav(root/'zero.wav');require(rate==48000 and x.shape==(FRAMES,2) and not np.any(x),'Precision source is not zero')
    for member in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/member['path'])==member['sha256'],'Original binary differs')
    plan=plan_for(c,inventory);requests=[p|dict(frame=-1) for p in plan['parameters']]+plan['events'];log=json.loads((folder/'parameter-log.json').read_text())['entries'];final={}
    require(len(log)==len(requests),'Parameter log count differs')
    for request,actual in zip(requests,log):
        value=float(np.float32(request['value']))
        require(all(request[k]==actual[k] for k in ['frame','name','index','id']) and float(np.float32(actual['requested_value']))==value and abs(actual['immediate_readback']-value)<=1e-14,'Original parameter readback differs')
        final[request['name']]=value
    after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-14 for k,v in final.items()),'Final controls differ')
    rate,a=float_wav(folder/'audio.wav');require(rate==48000 and a.shape==(FRAMES,2),'Original extent differs');return a,receipt


def compare(args):
    frozen(args);root=new_directory(args.output);rows=[];baseline=None;on_audio=None
    for c in cases():
        a,receipt=original(args,c);plan=root/(c['name']+'.tsv');plan.write_text(schedule(c));output=root/(c['name']+'.wav');sanitized=root/(c['name']+'-asan.wav')
        run([args.renderer,args.session/'zero.wav',output,plan]);process=subprocess.run([str(args.sanitized),str(args.session/'zero.wav'),str(sanitized),str(plan)],capture_output=True,text=True,timeout=120,
            env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        require(process.returncode==0 and not process.stderr and sha256(output)==sha256(sanitized),'Sanitizer output/stderr differs')
        rate,b=float_wav(output);require(rate==48000 and b.shape==a.shape,'Candidate extent differs');a=a[32:].astype(float);b=b[32:].astype(float)
        if not c['enabled']:baseline=(a,b)
        da,db=baseline;wa,wb=a-da,b-db;row=dict(case=c['name'],receipt_sha256=sha256(args.session/c['name']/'receipt.json'),candidate_sha256=sha256(output),schedule_sha256=sha256(plan),whole=screen(a,b),wet=screen(wa,wb),tail=screen(a[288000:],b[288000:]),windows=[])
        for at in [0,*c['hits']]:
            for kind,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                row['windows'].append(dict(frame=at,kind=kind,start=left,stop=right,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
        row['passed']=all(row[k]['passed'] for k in ['whole','wet','tail']) and all(w[k]['passed'] for w in row['windows'] for k in ['whole','wet']);rows.append(row)
        if c['enabled']:on_audio=(a,b)
    old=json.loads(args.native_comparison.read_text());failed=next(r for r in old['cases'] if r['case']=='drum-fx-live-effect7-route1');candidate=args.native_comparison.parent/'drum-fx-live-effect7-route1'
    call=copy.copy(args);call.stage='live-fresh';call.session=args.mixed_session
    base=next(c for c in recipe('live-fresh') if c['name']==failed['case']);base_dry=next(c for c in recipe('live-fresh') if c['name']==base['baseline'])
    ma,provenance=checked(call,base);md,dry_provenance=checked(call,base_dry);old_dry=next(r for r in old['cases'] if r['case']==base['baseline'])
    require(failed['receipt_sha256']==provenance['receipt_sha256'] and old_dry['receipt_sha256']==dry_provenance['receipt_sha256'],'Mixed original binding differs')
    require(sha256(candidate.with_suffix('.wav'))==failed['candidate_sha256'] and sha256(candidate.with_name(candidate.name+'-dry').with_suffix('.wav'))==old_dry['candidate_sha256'],'Mixed candidate changed')
    _,mb=float_wav(candidate.with_suffix('.wav'));_,me=float_wav(candidate.with_name(candidate.name+'-dry').with_suffix('.wav'))
    at=cases()[1]['hits'][-1];span=slice(at,at+256);span_full=slice(at+32,at+32+256);a,b=on_audio;da,db=baseline
    require(not np.any(da[span]) and not np.any(db[span]),'Isolated dry tail is not zero')
    reconstruction=dict(frame=at,frames=256,original_mixed_sum_exact=bool(np.array_equal((md[span_full]+a[span].astype('<f4')).astype('<f4'),ma[span_full])),candidate_mixed_sum_exact=bool(np.array_equal((me[span_full]+b[span].astype('<f4')).astype('<f4'),mb[span_full])),
        precision_wet=screen(a[span]-da[span],b[span]-db[span]),raw_mixed_window=next(w for w in failed['windows'] if w['frame']==at and w['kind']=='attack'))
    passed=all(r['passed'] for r in rows) and reconstruction['original_mixed_sum_exact'] and reconstruction['candidate_mixed_sum_exact'] and reconstruction['precision_wet']['passed']
    frozen(args);save_json(root/'comparison.json',dict(kind='rmx-zero-input-precision-diagnostic',passed=passed,cases=rows,reconstruction=reconstruction,prediction_sha256=sha256(args.prediction),
        source_sha256=source_hashes(),script_sha256=sha256(Path(__file__)),renderer_sha256=sha256(args.renderer),sanitized_sha256=sha256(args.sanitized),sanitizer_byte_identical=True,sanitizer_stderr_empty=True,acceptance=ACCEPTANCE,
        original_mixed_case_still_failed=not failed['passed'],scope='Two independent original zero-input fixtures at a known failed Crush/X-Pad setting. Same frozen Engine and controls/events. Unchanged gates, fixed32/32, no gain/alignment fitting. Precision evidence and float32 sum reconstruction do not retroactively pass the retained mixed-input failure.'))
    return 0 if passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['predict','capture','compare'])
    for name in ['renderer','sanitized','native-prediction','native-comparison']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['prediction','report','session','host','plugin','output','mixed-session']:p.add_argument('--'+name,type=Path)
    args=p.parse_args()
    if args.command=='predict':save_json(args.report,payload(args));return
    raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
