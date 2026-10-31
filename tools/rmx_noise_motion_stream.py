#!/usr/bin/env python3
"""Compare deterministic Noise motion using bounded audio and retained powers."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

import numpy as np

from tools import rmx_noise_user as noise
from tools import noise_motion_statistics as motion
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import require
from tools.rmx_noise_stream import RenderSpace, BUDGET, bindings as static_bindings, summary, screen, drift, verify_original


def bindings():
    return static_bindings() | {name:sha256(Path(name)) for name in [
        'tools/rmx_noise_motion_stream.py','tools/noise_motion_statistics.py','tools/noise_motion_probe.cpp']}


def analyze(path, case, probe):
    stationary=summary(path)
    rate,audio=float_wav(path)
    require(rate==48000,'Wrong modulation sample rate')
    return stationary,motion.profile(audio,case,probe)


def subset(profile, first, last):
    return {key:value[first:last] for key,value in profile.items()}


def run(args):
    require(args.duration in [180,600,1196], 'Choose180,600 or1196 stationary seconds')
    require(not args.output.exists() and not args.output.with_suffix('.partial.json').exists(),'Choose a new report')
    cases=json.loads(args.recipe.read_text())
    require(cases and len({c['name'] for c in cases})==len(cases),'Invalid/duplicate recipe')
    for c in cases:
        require(c['name'].replace('-','').isalnum(),'Unsafe case name')
        for key,limit in [('user',1),('main',255),('amount',255),('width',2),('minimum',3),('maximum',3),('wave',2),('sub2',255)]:
            require(type(c[key]) is int and 0<=c[key]<=limit,'Invalid control: '+key)
        require(c['user']==1 and c['sub2']>=4 and c.get('mode',0)==0 and 8<=c['block']<=4096,'Wrong modulation controls')
    cases=[c|dict(frames=(args.duration+4)*48000) for c in cases]
    bound=bindings();binaries={key:sha256(getattr(args,key)) for key in ['renderer','sanitizer','probe','host']}
    template=args.template.read_bytes();recipe_hash=sha256(args.recipe);rows=[]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='rmx-noise-motion-audio-',dir='/private/tmp') as session:
        session=Path(session)
        for c in cases:
            print('START',c['name'],args.duration,'seconds',flush=True)
            with tempfile.TemporaryDirectory(prefix='case-',dir=session) as directory:
                root=Path(directory);space=RenderSpace(root);write_wav(root/'silence.wav',48000,np.zeros(96000))
                program=root/'program.tsv';program.write_text(noise.schedule(c));wave=root/'native.wav'
                space.run([args.renderer,root/'silence.wav',wave,program]);digest=sha256(wave)
                prediction_time=datetime.now(timezone.utc).isoformat()
                candidate,candidate_profile=analyze(wave,c,args.probe);wave.unlink()
                # Save powers first and delete the native WAV before ASAN.
                # One whole render at a time halves the previous audio peak.
                sanitized=root/'sanitized.wav';space.run([args.sanitizer,root/'silence.wav',sanitized,program],sanitized=True)
                require(sha256(sanitized)==digest,'Native/ASAN complete WAV differs');sanitized.unlink()
                inventory=json.loads(space.run([args.host,'inventory',args.plugin]))
                rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c))
                (root/(c['name']+'.bin')).write_bytes(noise.state(template,noise.xml(c),str(rsd),str(root)+'/'))
                plan=noise.plan(c,inventory,root);save_json(root/'plan.json',plan)
                space.run([args.host,'render',args.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']])
                receipt,parameter_log=verify_original(root,c,plan,args.host)
                require(datetime.fromisoformat(prediction_time)<datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')),'Prediction did not precede reference')
                reference,reference_profile=analyze(root/'original/audio.wav',c,args.probe)
                stationary=screen(reference,candidate);profile=motion.measure(reference_profile,candidate_profile)
                n=len(reference_profile['total'])//3
                profile_thirds={label:motion.measure(subset(reference_profile,a,b),subset(candidate_profile,a,b))['verdict'] for label,a,b in [('early',0,n),('late',-n,None)]}
                stationarity=dict(reference=drift(reference),candidate=drift(candidate))
                polarity=reference_profile|dict(bands=reference_profile['bands'][:,::-1],total=reference_profile['total'][:,::-1])
                inverted=motion.measure(reference_profile,polarity)['verdict']
                gain=reference|dict(bands=reference['bands']*10**.3,total=reference['total']*10**.3)
                gain_negative=screen(reference,gain)['verdict']
                require(inverted==gain_negative=='different','A motion negative control was accepted')
                correlation=abs(reference['correlation']-candidate['correlation'])<=.02
                stats=args.output.with_name(args.output.stem+'-'+c['name']+'.npz');require(not stats.exists(),'Powers already exist')
                np.savez_compressed(stats,reference_bands=reference['bands'],reference_total=reference['total'],candidate_bands=candidate['bands'],candidate_total=candidate['total'],
                    reference_correlation=reference['correlation'],candidate_correlation=candidate['correlation'],
                    reference_profile_bands=reference_profile['bands'],reference_profile_total=reference_profile['total'],
                    candidate_profile_bands=candidate_profile['bands'],candidate_profile_total=candidate_profile['total'],profile_exposure=reference_profile['exposure'])
                passed=stationary['verdict']==profile['verdict']=='pass' and correlation and all(v=='pass' for v in stationarity.values()) and all(v=='pass' for v in profile_thirds.values())
                rows.append(c|dict(passed=passed,statistics=stationary,profile=profile,profile_thirds=profile_thirds,stationarity=stationarity,stereo_correlation_passed=correlation,
                    negative_controls=dict(gain3db=gain_negative,control_polarity_inversion=inverted),summary=dict(path=str(stats.resolve()),sha256=sha256(stats)),
                    prediction_sha256=digest,prediction_created_utc=prediction_time,complete_native_sanitizer_wav_byte_identity=True,
                    original_receipt=receipt,original_receipt_sha256=sha256(root/'original/receipt.json'),original_plan=plan,parameter_log=parameter_log,peak_temporary_bytes=space.peak))
                partial=args.output.with_suffix('.partial.json');writing=partial.with_suffix('.writing');save_json(writing,dict(kind='bounded-noise-motion-partial',complete=False,cases=rows,source_sha256=bound,raw_audio_retained=False));writing.replace(partial)
                print('RESULT',c['name'],'overall',stationary['verdict'],'motion',profile['verdict'],'thirds',profile_thirds,'stability',stationarity,flush=True)
            require(not root.exists(),'Case audio retained')
    require(not session.exists(),'Session audio retained')
    require(bound==bindings() and recipe_hash==sha256(args.recipe) and all(sha256(getattr(args,k))==v for k,v in binaries.items()),'Campaign inputs changed')
    save_json(args.output,dict(kind='bounded-noise-motion-validation',passed=all(c['passed'] for c in rows),cases=rows,source_sha256=bound,binary_sha256=binaries,
        recipe_sha256=recipe_hash,template_sha256=sha256(args.template),stationary_seconds=args.duration,storage_budget_bytes=BUDGET,
        peak_temporary_bytes=max(c['peak_temporary_bytes'] for c in rows),raw_audio_retained=False,all_temporary_directories_removed=True,
        scope='Declared stationary-control Triangle/Saw/Square Noise at48k/120BPM, silent input. Predictions frozen before fresh Original captures, full native/ASAN WAV identity, whole spectral/level/stereo and early/late stability plus control-conditioned short-window powers and early/late matching. No perceptual percentage, random/sidechain, dynamic settings, general tempo/rate or hardware qualification.'))
    args.output.with_suffix('.partial.json').unlink()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['renderer','sanitizer','probe','host','plugin','template','recipe','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--duration',type=int,default=180)
    run(p.parse_args())


if __name__=='__main__':main()
