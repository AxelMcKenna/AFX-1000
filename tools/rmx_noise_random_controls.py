#!/usr/bin/env python3
"""Freeze reference-target-driven Random predictions and check fresh observations."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
import numpy as np
from tools import rmx_noise_user as noise
from tools.rmx_noise_stream import RenderSpace,verify_original
from tools.reference_audio import write_wav,save_json,sha256


def verify_targets(trace,raw,frames=None):
    smooth=max(raw-3,0);period=np.float32(np.float32(9600)+np.float32(np.float32(np.float32(-8640)*np.float32(1/252))*smooth))
    interval=((int(period)+15)//16)*16
    for index,row in enumerate(trace['targets']):
        if row['counter']!=interval or row['period']!=float(period):raise ValueError('Random target period differs')
        if frames is not None and row['control_frame']!=(index+1)*interval:raise ValueError('Random target frame differs')
        expected=float(np.float32(np.float32(row['target']-row['previous'])*np.float32(1/128)))
        if row['step']!=expected or (index and row['previous']!=trace['targets'][index-1]['target']):raise ValueError('Random interpolation differs')
    if frames is not None and len(trace['targets'])!=(frames-1)//interval:raise ValueError('Random event count differs')
    return interval


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['host','plugin','template','probe','sanitizer','prefix-trace','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Choose a new report')
    prefix=json.loads(a.prefix_trace.read_text());targets=[r['target'] for r in prefix['targets']]
    sources={n:sha256(Path(n)) for n in ['include/rmx/NoiseModulator.h','src/core/NoiseModulator.cpp','tools/noise_random_probe.cpp','tools/rmx_noise_random_controls.py','research/audio/experiments/noise_random_observer.py','tools/rmx_noise_user.py']}
    binaries={k:sha256(getattr(a,k)) for k in ['host','probe','sanitizer']};rows=[]
    for raw in [4,117,255]:
        c=noise.recipe()[0]|dict(name='random-fresh-'+str(raw),user=1,width=1,main=149,amount=128,mode=0,wave=3,resonance=0,sub2=raw,minimum=1,maximum=2,frames=96000,block={4:113,117:509,255:1021}[raw])
        with tempfile.TemporaryDirectory(prefix='rmx-random-fresh-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);target_file=root/'targets.txt';target_file.write_text('\n'.join(format(v,'.17g') for v in targets)+'\n')
            prediction=[]
            for probe in [a.probe,a.sanitizer]:
                run=subprocess.run([probe,str(raw),'2849',str(target_file),'controls'],capture_output=True,check=True)
                if run.stderr:raise ValueError('Control replay reported diagnostics')
                prediction.append(run.stdout)
            if prediction[0]!=prediction[1]:raise ValueError('Native/ASAN control predictions differ')
            frozen=datetime.now(timezone.utc).isoformat();digest=hashlib.sha256(prediction[0]).hexdigest()
            write_wav(root/'silence.wav',48000,np.zeros(96000));inventory=json.loads(space.run([a.host,'inventory',a.plugin]));rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c));(root/(c['name']+'.bin')).write_bytes(noise.state(a.template.read_bytes(),noise.xml(c),str(rsd),str(root)+'/'));plan=noise.plan(c,inventory,root);save_json(root/'plan.json',plan);space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']]);receipt,_=verify_original(root,c,plan,a.host)
            if datetime.fromisoformat(frozen)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Prediction followed Original')
            observer=Path('research/audio/experiments/noise_random_observer.py').resolve();args=['render',str(a.plugin),str(root/'silence.wav'),str(root/'plan.json'),str(root/'observed'),str(c['block'])];commands=root/'observe.lldb';commands.write_text('target create "'+str(a.host)+'"\nsettings set target.run-args '+' '.join('"'+v+'"' for v in args)+'\ncommand script import "'+str(observer)+'"\nrun\nscript noise_random_observer.finish()\nquit\n');space.run(['env','RMX_RANDOM_TRACE='+str(root/'trace.json'),'RMX_RANDOM_FULL=1','lldb','--batch','-s',commands])
            hashes={n:sha256(root/'original'/n) for n in ['audio.wav','plan.json','state-before.bin','state-after.bin','parameter-log.json','inventory-after.json']}
            if any(sha256(root/'observed'/n)!=v for n,v in hashes.items()):raise ValueError('Observer altered audio or auxiliary data')
            trace=json.loads((root/'trace.json').read_text());interval=verify_targets(trace,raw,trace['blocks']*32)
            matched=digest==trace['full_control_sha256'] and all(row['target']==targets[i] for i,row in enumerate(trace['targets']))
            rows.append(dict(case=c,passed=matched,prospective_reference_target_driven_prediction=True,prediction_created_utc=frozen,prediction_sha256=digest,blocks=trace['blocks'],controls=trace['blocks']*32,interval_frames=interval,observed_control_sha256=trace['full_control_sha256'],observed_targets=trace['targets'],native_sanitizer_prediction_identity=True,ordinary_and_observed_sha256=hashes,receipt_sha256=sha256(root/'original/receipt.json'),peak_temporary_bytes=space.peak));print('RANDOM CONTROL',raw,matched,flush=True)
        if root.exists():raise ValueError('Temporary audio retained')
    if any(sha256(Path(k))!=v for k,v in sources.items()) or any(sha256(getattr(a,k))!=v for k,v in binaries.items()):raise ValueError('Campaign inputs changed')
    save_json(a.output,dict(kind='reference-target-driven-random-control-validation',verification_passed=True,all_conditional_controls_matched=all(r['passed'] for r in rows),cases=rows,source_sha256=sources,binary_sha256=binaries,prefix_trace_sha256=sha256(a.prefix_trace),raw_audio_retained=False,all_temporary_directories_removed=True,peak_temporary_bytes=max(r['peak_temporary_bytes'] for r in rows),scope='Fresh fixed-control predictions using an earlier observed target prefix. Verifies target scheduling/ramp/float32 output; default production Random retains its independent generator and does not reproduce this reference target sequence.'))


if __name__=='__main__':main()
