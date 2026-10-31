#!/usr/bin/env python3
"""Bounded prospective Sidechain detector/control checks against the Original."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from tools import rmx_noise_user as noise
from tools.rmx_noise_stream import RenderSpace, verify_original
from tools.reference_audio import save_json, sha256, write_wav


def stimulus(name):
    t=np.arange(48000)/48000
    active=((t>=.173)&(t<.319))|((t>=.517)&(t<.743))
    x=np.zeros((48000,2),dtype='<f4')
    if name in ['low','high','right']:
        y=np.sin(2*np.pi*(137 if name=='low' else 7127)*t)*.271*active
        if name=='right':x[:,1]=y
        else:x[:,0]=y;x[:,1]=y*.63
    elif name=='steps':x[active]=-.237
    elif name=='asymmetric':
        x[:,0]=np.sin(2*np.pi*93*t)*(.071+active*.243)
        x[:,1]=np.sin(2*np.pi*6311*t)*.417
    elif name!='silence':raise ValueError('Unknown stimulus')
    return x


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['host','plugin','template','probe','sanitizer','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--stimulus',choices=['silence','low','high','right','steps','asymmetric'],action='append')
    a=p.parse_args()
    if a.output.exists() or a.output.with_suffix('.partial.json').exists():raise ValueError('Choose a new report')
    sources={n:sha256(Path(n)) for n in ['include/rmx/NoiseModulator.h','include/rmx/CalibratedGateDrive.h','src/core/GateDrive.cpp','tools/noise_sidechain_probe.cpp','tools/rmx_noise_sidechain_controls.py','research/audio/experiments/noise_sidechain_observer.py','tools/rmx_noise_user.py','tools/rmx_noise_stream.py','tools/reference_audio.py']}
    binaries={k:sha256(getattr(a,k)) for k in ['host','probe','sanitizer']}
    observer=Path('research/audio/experiments/noise_sidechain_observer.py').resolve();rows=[]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for index,name in enumerate(a.stimulus or ['silence','low','high','right','steps','asymmetric']):
        sub2={'silence':255,'low':117,'high':4,'right':223,'steps':29,'asymmetric':201}[name]
        c=noise.recipe()[0]|dict(name='sidechain-fresh-'+name,user=1,width=index%3,main=173,amount=119,mode=0,wave=4,resonance=0,sub2=sub2,minimum=0,maximum=3,frames=48000,block=[113,509,1021][index%3])
        x=stimulus(name)
        native=subprocess.run([a.probe,'--chain',str(sub2)],input=x.tobytes(),capture_output=True,check=True)
        san=subprocess.run([a.sanitizer,'--chain',str(sub2)],input=x.tobytes(),capture_output=True,check=True,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        if native.stdout!=san.stdout or native.stderr or san.stderr:raise ValueError('Native/ASAN driver prediction differs')
        prediction_time=datetime.now(timezone.utc).isoformat();prediction_hash=hashlib.sha256(native.stdout).hexdigest()
        predicted=np.frombuffer(native.stdout,dtype='<f4').reshape(-1,65)
        with tempfile.TemporaryDirectory(prefix='rmx-sidechain-holdout-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);write_wav(root/'silence.wav',48000,x.reshape(-1))
            inv=json.loads(space.run([a.host,'inventory',a.plugin]));rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c))
            (root/(c['name']+'.bin')).write_bytes(noise.state(a.template.read_bytes(),noise.xml(c),str(rsd),str(root)+'/'))
            plan=noise.plan(c,inv,root);save_json(root/'plan.json',plan)
            space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']]);receipt,_=verify_original(root,c,plan,a.host)
            if datetime.fromisoformat(prediction_time)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Prediction followed reference')
            args=['render',str(a.plugin),str(root/'silence.wav'),str(root/'plan.json'),str(root/'observed'),str(c['block'])]
            commands=root/'observe.lldb';commands.write_text('target create "'+str(a.host)+'"\nsettings set target.run-args '+' '.join('"'+v+'"' for v in args)+'\ncommand script import "'+str(observer)+'"\nrun\nscript noise_sidechain_observer.finish()\nquit\n')
            space.run(['env','RMX_NOISE_SIDECHAIN_TRACE='+str(root/'trace.f32'),'lldb','--batch','-s',commands])
            hashes={n:sha256(root/'original'/n) for n in ['audio.wav','plan.json','state-before.bin','state-after.bin','parameter-log.json','inventory-after.json']}
            if any(sha256(root/'observed'/n)!=v for n,v in hashes.items()):raise ValueError('Observation altered audio/auxiliaries')
            observed=np.fromfile(root/'trace.f32',dtype='<f4').reshape(-1,65)
            if predicted.shape!=observed.shape or not np.isfinite(observed).all():raise ValueError('Wrong control extent')
            errors=np.max(np.abs(predicted-observed),axis=0)
            driver_error=float(errors[:33].max());control_error=float(errors[33:].max())
            component=subprocess.run([a.probe,'--component',str(sub2)],input=observed[:,:33].copy().tobytes(),capture_output=True,check=True)
            component_error=float(np.max(np.abs(np.frombuffer(component.stdout,dtype='<f4').reshape(-1,32)-observed[:,33:])))
            row=dict(case=c,blocks=len(observed),prediction_created_utc=prediction_time,prediction_sha256=prediction_hash,
                maximum_detector_error=driver_error,maximum_control_error=control_error,maximum_component_replay_error=component_error,
                complete_driver_and_control_f32_identity=native.stdout==observed.tobytes(),native_asan_prediction_identity=True,
                observed_control_sha256=hashlib.sha256(observed[:,33:].copy().tobytes()).hexdigest(),observed_trace_sha256=sha256(root/'trace.f32'),
                original_receipt_sha256=sha256(root/'original/receipt.json'),ordinary_and_observed_sha256=hashes,input_sha256=sha256(root/'silence.wav'),peak_temporary_bytes=space.peak)
            row['passed']=driver_error==control_error==component_error==0
            rows.append(row);print('SIDECHAIN',name,driver_error,control_error,component_error,flush=True)
        if root.exists():raise ValueError('Temporary capture retained')
        temporary=a.output.with_suffix('.writing');temporary.write_text(json.dumps(dict(complete=False,cases=rows),indent=2)+'\n');temporary.replace(a.output.with_suffix('.partial.json'))
    if any(sha256(Path(k))!=v for k,v in sources.items()) or any(sha256(getattr(a,k))!=v for k,v in binaries.items()):raise ValueError('Campaign inputs changed')
    save_json(a.output,dict(kind='bounded-noise-sidechain-control-validation',verification_passed=True,all_declared_cases_matched=all(r['passed'] for r in rows),cases=rows,source_sha256=sources,binary_sha256=binaries,template_sha256=sha256(a.template),raw_audio_retained=False,all_temporary_directories_removed=True,peak_temporary_bytes=max(r['peak_temporary_bytes'] for r in rows),scope='Prospective fixed-control Sidechain driver/envelope checks at48k/120BPM, one-second synthetic inputs and frame4800 activation. Full detector/threshold/control comparisons, native/ASAN identity and ordinary/observed audio invariance. Does not qualify generated Noise audio, other inputs/settings/rates/tempos, adaptive long-history transitions or hardware.'))
    a.output.with_suffix('.partial.json').unlink()


if __name__=='__main__':main()
