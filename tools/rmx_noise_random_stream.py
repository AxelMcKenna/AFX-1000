#!/usr/bin/env python3
"""Bounded Random Noise audio checks with source-specific control profiles."""
import argparse
from datetime import datetime,timezone
import hashlib,json,subprocess,tempfile
from pathlib import Path
import numpy as np
from tools import rmx_noise_user as noise
from tools import noise_random_statistics as random_stats
from tools.noise_statistics import float_wav
from tools.reference_audio import write_wav,save_json,sha256
from tools.rmx_noise_stream import RenderSpace,summary,screen,drift,verify_original,bindings
from tools.rmx_noise_random_controls import verify_targets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['renderer','sanitizer','probe','host','plugin','template','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--duration',type=int,choices=[600,1190],default=600)
    p.add_argument('--width',type=int,choices=[0,1,2],action='append')
    a=p.parse_args()
    if a.output.exists() or a.output.with_suffix('.partial.json').exists():raise ValueError('Choose a new report')
    sources=bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_noise_random_stream.py','tools/noise_random_statistics.py','tools/noise_random_probe.cpp','tools/rmx_noise_random_controls.py','research/audio/experiments/noise_random_observer.py']}
    binaries={k:sha256(getattr(a,k)) for k in ['renderer','sanitizer','probe','host']};rows=[]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for width in a.width or [0,1,2]:
        raw=[29,117,223][width]
        c=noise.recipe()[0]|dict(name='noise-random-w'+str(width),user=1,width=width,main=173,amount=128,mode=0,wave=3,resonance=0,sub2=raw,minimum=1,maximum=2,frames=(a.duration+4)*48000,block=[113,509,1021][width])
        print('START RANDOM',c['name'],a.duration,flush=True)
        with tempfile.TemporaryDirectory(prefix='rmx-random-audio-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);write_wav(root/'silence.wav',48000,np.zeros(96000));program=root/'program.tsv';program.write_text(noise.schedule(c));wave=root/'native.wav'
            space.run([a.renderer,root/'silence.wav',wave,program]);digest=sha256(wave);frozen=datetime.now(timezone.utc).isoformat();candidate=summary(wave);rate,audio=float_wav(wave);candidate_profile=random_stats.profile(audio,raw,a.probe);del audio;wave.unlink()
            space.run([a.sanitizer,root/'silence.wav',wave,program],sanitized=True)
            if sha256(wave)!=digest:raise ValueError('Native/ASAN complete audio differs')
            wave.unlink();inventory=json.loads(space.run([a.host,'inventory',a.plugin]));rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c));(root/(c['name']+'.bin')).write_bytes(noise.state(a.template.read_bytes(),noise.xml(c),str(rsd),str(root)+'/'));plan=noise.plan(c,inventory,root);save_json(root/'plan.json',plan)
            space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']]);receipt,_=verify_original(root,c,plan,a.host)
            if datetime.fromisoformat(frozen)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Prediction followed Original')
            reference=summary(root/'original/audio.wav');ordinary={n:sha256(root/'original'/n) for n in ['audio.wav','plan.json','state-before.bin','state-after.bin','parameter-log.json','inventory-after.json']};receipt_hash=sha256(root/'original/receipt.json');(root/'original/audio.wav').unlink()
            observer=Path('research/audio/experiments/noise_random_observer.py').resolve();args=['render',str(a.plugin),str(root/'silence.wav'),str(root/'plan.json'),str(root/'observed'),str(c['block']),'600'];commands=root/'observe.lldb';commands.write_text('target create "'+str(a.host)+'"\nsettings set target.run-args '+' '.join('"'+v+'"' for v in args)+'\ncommand script import "'+str(observer)+'"\nrun\nscript noise_random_observer.finish()\nquit\n');debugger_output=space.run(['env','RMX_RANDOM_TRACE='+str(root/'trace.json'),'RMX_RANDOM_FULL=0','lldb','--batch','-s',commands])
            missing=[n for n in [*ordinary,'receipt.json'] if not (root/'observed'/n).is_file()]
            if missing:
                save_json(a.output.with_suffix('.failed.json'),dict(kind='incomplete-random-observation',case=c,missing=missing,debugger_output_tail=debugger_output[-5000:],raw_audio_retained=False))
                raise ValueError('Observed host capture incomplete: '+', '.join(missing))
            observed_receipt=json.loads((root/'observed/receipt.json').read_text())
            if not observed_receipt['complete'] or observed_receipt['frames']!=c['frames']:raise ValueError('Observed host receipt incomplete')
            observed_hashes={n:sha256(root/'observed'/n) for n in ordinary}
            if observed_hashes!=ordinary:
                failure=dict(kind='rejected-random-observation',case=c,ordinary_sha256=ordinary,observed_sha256=observed_hashes,different=[n for n in ordinary if ordinary[n]!=observed_hashes[n]],raw_audio_retained=False,scope='Observation invariance failed; not a candidate fidelity result. Temporary captures are removed on unwinding.')
                save_json(a.output.with_suffix('.failed.json'),failure)
                raise ValueError('Target observation altered: '+', '.join(failure['different']))
            trace=json.loads((root/'trace.json').read_text());control_frames=(c['frames']-4832)//32*32;interval=verify_targets(trace,raw)
            if len(trace['targets'])!=(control_frames-1)//interval:raise ValueError('Long Random event count differs')
            observed_targets=np.asarray([t['target'] for t in trace['targets']],dtype='<f4');target_file=root/'targets.txt';target_file.write_text('\n'.join(format(v,'.17g') for v in observed_targets)+'\n')
            rate,audio=float_wav(root/'observed/audio.wav');reference_profile=random_stats.profile(audio,raw,a.probe,target_file);del audio
            own=subprocess.run([a.probe,str(raw),str(control_frames//32),'own','targets'],capture_output=True,check=True)
            own_targets=np.frombuffer(own.stdout,dtype='<f4')
            if own.stderr or len(own_targets)!=len(observed_targets):raise ValueError('Own target count differs')
            overall=screen(reference,candidate);profile=random_stats.measure(reference_profile,candidate_profile);n=len(reference_profile['total'])//3
            thirds={label:random_stats.measure({k:v[first:last] for k,v in reference_profile.items()},{k:v[first:last] for k,v in candidate_profile.items()})['verdict'] for label,first,last in [('early',0,n),('late',-n,None)]}
            stability=dict(reference=drift(reference),candidate=drift(candidate));stereo=abs(reference['correlation']-candidate['correlation'])<=.02
            gain=screen(reference,reference|dict(bands=reference['bands']*10**.3,total=reference['total']*10**.3))['verdict'];profile_gain=random_stats.measure(reference_profile,reference_profile|dict(bands=reference_profile['bands']*10**.3,total=reference_profile['total']*10**.3))['verdict'];reversed_bins=random_stats.measure(reference_profile,reference_profile|dict(bands=reference_profile['bands'][:,::-1],total=reference_profile['total'][:,::-1],exposure=reference_profile['exposure'][:,::-1]))['verdict']
            if gain!=profile_gain or gain!='different':raise ValueError('Random gain negative passed')
            stats=a.output.with_name(a.output.stem+'-'+c['name']+'.npz')
            if stats.exists():raise ValueError('Powers already exist')
            np.savez_compressed(stats,reference_bands=reference['bands'],reference_total=reference['total'],candidate_bands=candidate['bands'],candidate_total=candidate['total'],reference_correlation=reference['correlation'],candidate_correlation=candidate['correlation'],reference_profile_bands=reference_profile['bands'],reference_profile_total=reference_profile['total'],candidate_profile_bands=candidate_profile['bands'],candidate_profile_total=candidate_profile['total'],reference_profile_exposure=reference_profile['exposure'],candidate_profile_exposure=candidate_profile['exposure'],reference_targets=observed_targets,candidate_targets=own_targets)
            target_stats={name:dict(count=len(v),mean=float(v.mean(dtype=np.float64)),variance=float(v.var(dtype=np.float64)),range=[float(v.min()),float(v.max())],histogram16=np.histogram(v,bins=np.linspace(-1,1,17))[0].tolist(),lag1=float(np.corrcoef(v[:-1],v[1:])[0,1])) for name,v in [('reference',observed_targets),('candidate',own_targets)]}
            passed=overall['verdict']==profile['verdict']=='pass' and stereo and all(v=='pass' for v in thirds.values()) and all(v=='pass' for v in stability.values())
            rows.append(c|dict(passed=passed,statistics=overall,profile=profile,profile_thirds=thirds,stationarity=stability,stereo_correlation_passed=stereo,negative_controls=dict(gain3db=gain,profile_gain3db=profile_gain,reversed_control_bins=reversed_bins),summary=dict(path=str(stats.resolve()),sha256=sha256(stats)),prediction_sha256=digest,prediction_created_utc=frozen,complete_native_sanitizer_wav_byte_identity=True,original_receipt_sha256=receipt_hash,ordinary_and_observed_sha256=ordinary,reference_target_controls_sha256=hashlib.sha256(observed_targets.tobytes()).hexdigest(),candidate_target_controls_sha256=hashlib.sha256(own_targets.tobytes()).hexdigest(),target_statistics=target_stats,interval_frames=interval,peak_temporary_bytes=space.peak));print('RANDOM AUDIO',width,overall['verdict'],profile['verdict'],thirds,stability,flush=True)
        if root.exists():raise ValueError('Temporary audio retained')
        tmp=a.output.with_suffix('.writing');tmp.write_text(json.dumps(dict(complete=False,cases=rows),indent=2)+'\n');tmp.replace(a.output.with_suffix('.partial.json'))
    if any(sha256(Path(k))!=v for k,v in sources.items()) or any(sha256(getattr(a,k))!=v for k,v in binaries.items()):raise ValueError('Campaign inputs changed')
    save_json(a.output,dict(kind='bounded-noise-random-audio-validation',passed=all(c['passed'] for c in rows),cases=rows,source_sha256=sources,binary_sha256=binaries,template_sha256=sha256(a.template),stationary_seconds=a.duration,storage_budget_bytes=512*1024**2,peak_temporary_bytes=max(c['peak_temporary_bytes'] for c in rows),raw_audio_retained=False,all_temporary_directories_removed=True,scope='Fixed User Random Noise at48k/120BPM, silent input; own production target and stereo excitation generators. Source-specific conditional profiles use separate target sequences and unequal exposures. Reference targets are observed read-only and ordinary/observed audio is byte-identical. No waveform-null or identical default random sequence, arbitrary inputs/dynamics/rates/tempos, hardware or perceptual percentage.'))
    a.output.with_suffix('.partial.json').unlink()


if __name__=='__main__':main()
