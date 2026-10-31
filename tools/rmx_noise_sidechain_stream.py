#!/usr/bin/env python3
"""Compare Noise Sidechain wet audio with bounded captures and retained powers."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

import numpy as np
from tools import rmx_noise_user as noise
from tools import noise_motion_statistics as motion
from tools import rmx_noise_sidechain_controls as controls
from tools.noise_statistics import float_wav, powers, stereo_correlation
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_noise_stream import RenderSpace, summary, screen, drift, verify_original, bindings


def residual(path,pattern):
    rate,audio=float_wav(path)
    if rate!=48000:raise ValueError('Wrong audio sample rate')
    audio=audio.copy()
    # Both transports have a separately checked32-frame dry delay. Subtract
    # known synthetic input only; the random Noise remains independent.
    for start in range(0,len(audio),48000):
        indices=(np.arange(start,min(start+48000,len(audio)))-32)
        dry=pattern[indices%48000].copy();dry[indices<0]=0
        audio[start:start+len(dry)]-=dry
    return audio


def analyze(path,pattern):
    audio=residual(path,pattern)[4*48000:]
    bands,total=powers(audio,48000);stationary=dict(bands=bands,total=total,correlation=stereo_correlation(audio))
    size,step=256,128;epochs=len(audio)//96000;count=(len(audio)-size)//step+1
    window=np.hanning(size);norm=np.sum(window*window);frequencies=np.fft.rfftfreq(size,1/48000)
    masks=[(frequencies>=a)&(frequencies<b) for a,b in zip(motion.EDGES[:-1],motion.EDGES[1:])]
    pb=np.empty((epochs,4,6,2));pt=np.empty((epochs,4,2));exposure=np.empty((epochs,4),dtype=np.int32)
    for epoch in range(epochs):
        first=max(0,epoch*750-1);end=min(count,(epoch+1)*750-1)
        positions=np.arange(first,end)*step
        weighted=np.stack([audio[i:i+size] for i in positions])*window[None,:,None]
        spectrum=np.abs(np.fft.rfft(weighted,axis=1))**2*(2/(size*norm));spectrum[:,0]*=.5;spectrum[:,-1]*=.5
        bp=np.stack([np.sum(spectrum[:,mask],axis=1) for mask in masks],axis=1);tp=np.sum(weighted*weighted,axis=1)/norm
        labels=((positions+size//2)%48000)//12000
        for bin_index in range(4):
            keep=labels==bin_index;exposure[epoch,bin_index]=np.sum(keep)
            pb[epoch,bin_index]=np.mean(bp[keep],axis=0);pt[epoch,bin_index]=np.mean(tp[keep],axis=0)
    return stationary,dict(bands=pb,total=pt,exposure=exposure)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['renderer','sanitizer','host','plugin','template','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--duration',type=int,choices=[180,600],default=180)
    p.add_argument('--stimulus',choices=['low','asymmetric','steps'],action='append')
    a=p.parse_args()
    if a.output.exists() or a.output.with_suffix('.partial.json').exists():raise ValueError('Choose a new report')
    bound=bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_noise_sidechain_stream.py','tools/rmx_noise_sidechain_controls.py','tools/noise_motion_statistics.py','src/core/GateDrive.cpp','include/rmx/CalibratedGateDrive.h']}
    binaries={k:sha256(getattr(a,k)) for k in ['renderer','sanitizer','host']};rows=[]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for name in a.stimulus or ['low','asymmetric','steps']:
        width,main,sub2={'low':(0,73,29),'asymmetric':(1,149,117),'steps':(2,203,223)}[name]
        c=noise.recipe()[0]|dict(name='noise-sidechain-'+name,user=1,width=width,main=main,amount=163,mode=0,wave=4,resonance=0,sub2=sub2,minimum=0,maximum=2,frames=(a.duration+4)*48000,block=[113,509,1021][width])
        pattern=controls.stimulus(name)
        with tempfile.TemporaryDirectory(prefix='rmx-sidechain-audio-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);inventory=json.loads(space.run([a.host,'inventory',a.plugin]))
            rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c));(root/(c['name']+'.bin')).write_bytes(noise.state(a.template.read_bytes(),noise.xml(c),str(rsd),str(root)+'/'))
            # An eight-second zero-Noise-amount control independently verifies
            # dry-stem subtraction for each preset and transport.
            write_wav(root/'silence.wav',48000,np.tile(pattern,(8,1)).reshape(-1))
            dry=c|dict(amount=0,frames=8*48000);program=root/'program.tsv';program.write_text(noise.schedule(dry).replace('RMX_NOISE_USER 2','RMX_NOISE_USER 3'))
            wave=root/'native.wav';space.run([a.renderer,root/'silence.wav',wave,program]);candidate_dry=float(np.max(np.abs(residual(wave,pattern)[4*48000:])));wave.unlink()
            plan=noise.plan(dry,inventory,root);plan['tail_seconds']=0;save_json(root/'plan.json',plan)
            space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']]);dry_receipt,_=verify_original(root,dry,plan,a.host)
            reference_dry=float(np.max(np.abs(residual(root/'original/audio.wav',pattern)[4*48000:])))
            if max(candidate_dry,reference_dry)>1e-6:raise ValueError('Dry stem subtraction failed')
            dry_receipt_hash=sha256(root/'original/receipt.json')
            import shutil
            shutil.rmtree(root/'original');(root/'plan.json').unlink();(root/'silence.wav').unlink()
            write_wav(root/'silence.wav',48000,np.tile(pattern,(a.duration+4,1)).reshape(-1));input_hash=sha256(root/'silence.wav')
            program.write_text(noise.schedule(c).replace('RMX_NOISE_USER 2','RMX_NOISE_USER 3'));space.run([a.renderer,root/'silence.wav',wave,program]);digest=sha256(wave);prediction_time=datetime.now(timezone.utc).isoformat();candidate,cp=analyze(wave,pattern);wave.unlink()
            space.run([a.sanitizer,root/'silence.wav',wave,program],sanitized=True)
            if sha256(wave)!=digest:raise ValueError('Native/ASAN complete WAV differs')
            wave.unlink();plan=noise.plan(c,inventory,root);plan['tail_seconds']=0;save_json(root/'plan.json',plan)
            space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']]);receipt,_=verify_original(root,c,plan,a.host)
            if datetime.fromisoformat(prediction_time)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Prediction followed reference')
            reference,rp=analyze(root/'original/audio.wav',pattern);overall=screen(reference,candidate);profile=motion.measure(rp,cp)
            profile['kind']='noise-stimulus-quarter-conditioned-power-screen'
            profile['scope']='256-frame Hann windows every128 frames, grouped by quarter-second stimulus phase; two-second paired log-power differences with unchanged margins and HAC correction.'
            n=len(rp['total'])//3
            thirds={label:motion.measure({k:v[first:last] for k,v in rp.items()},{k:v[first:last] for k,v in cp.items()})['verdict'] for label,first,last in [('early',0,n),('late',-n,None)]}
            stability=dict(reference=drift(reference),candidate=drift(candidate));stereo=abs(reference['correlation']-candidate['correlation'])<=.02
            gain=reference|dict(bands=reference['bands']*10**.3,total=reference['total']*10**.3)
            negative_gain=screen(reference,gain)['verdict'];inverted=motion.measure(rp,rp|dict(bands=rp['bands'][:,::-1],total=rp['total'][:,::-1]))['verdict']
            profile_gain=motion.measure(rp,rp|dict(bands=rp['bands']*10**.3,total=rp['total']*10**.3))['verdict']
            if negative_gain!=profile_gain or negative_gain!='different':raise ValueError('Gain negative control passed')
            stats=a.output.with_name(a.output.stem+'-'+c['name']+'.npz')
            if stats.exists():raise ValueError('Powers already exist')
            np.savez_compressed(stats,reference_bands=reference['bands'],reference_total=reference['total'],candidate_bands=candidate['bands'],candidate_total=candidate['total'],reference_correlation=reference['correlation'],candidate_correlation=candidate['correlation'],reference_profile_bands=rp['bands'],reference_profile_total=rp['total'],candidate_profile_bands=cp['bands'],candidate_profile_total=cp['total'],profile_exposure=rp['exposure'])
            passed=overall['verdict']==profile['verdict']=='pass' and stereo and all(v=='pass' for v in thirds.values()) and all(v=='pass' for v in stability.values())
            rows.append(c|dict(passed=passed,statistics=overall,profile=profile,profile_thirds=thirds,stationarity=stability,stereo_correlation_passed=stereo,negative_controls=dict(gain3db=negative_gain,profile_gain3db=profile_gain,stimulus_phase_inversion=inverted),summary=dict(path=str(stats.resolve()),sha256=sha256(stats)),prediction_sha256=digest,prediction_created_utc=prediction_time,complete_native_sanitizer_wav_byte_identity=True,original_receipt_sha256=sha256(root/'original/receipt.json'),original_audio_sha256=receipt['output_sha256'],input_sha256=input_hash,dry_subtraction_control=dict(candidate_maximum_residual=candidate_dry,reference_maximum_residual=reference_dry,original_receipt_sha256=dry_receipt_hash),peak_temporary_bytes=space.peak))
            print('SIDECHAIN AUDIO',name,overall['verdict'],profile['verdict'],thirds,stability,'negative',inverted,flush=True)
        if root.exists():raise ValueError('Temporary audio retained')
        tmp=a.output.with_suffix('.writing');tmp.write_text(json.dumps(dict(complete=False,cases=rows),indent=2)+'\n');tmp.replace(a.output.with_suffix('.partial.json'))
    if any(sha256(Path(k))!=v for k,v in bound.items()) or any(sha256(getattr(a,k))!=v for k,v in binaries.items()):raise ValueError('Campaign inputs changed')
    save_json(a.output,dict(kind='bounded-noise-sidechain-audio-validation',passed=all(c['passed'] for c in rows),cases=rows,source_sha256=bound,binary_sha256=binaries,template_sha256=sha256(a.template),stationary_seconds=a.duration,storage_budget_bytes=512*1024**2,peak_temporary_bytes=max(c['peak_temporary_bytes'] for c in rows),raw_audio_retained=False,all_temporary_directories_removed=True,scope='Fixed User Noise Sidechain presets,48k/120BPM, declared repeated synthetic input. Independently checked dry-stem subtraction, native/ASAN byte identity, wet level/spectrum/stereo/stationarity and four stimulus-quarter-conditioned profiles. Does not imply arbitrary music, dynamic controls, Random, other rates/tempos, hardware or perceptual percentage.'))
    a.output.with_suffix('.partial.json').unlink()


if __name__=='__main__':main()
