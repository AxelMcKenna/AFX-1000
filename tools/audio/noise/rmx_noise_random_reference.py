#!/usr/bin/env python3
"""Fresh default-Random audio checks after verifying the reconstructed trajectory."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from tools.audio.noise import rmx_noise_user as noise
from tools.audio.noise import noise_random_statistics as random_stats
from tools.audio.noise import noise_reference_trajectory_statistics as paired
from tools.audio.common.reference_audio import write_wav,save_json,sha256
from tools.audio.noise.rmx_noise_stream import RenderSpace,summary,screen,drift,verify_original,bindings
from tools.audio.noise.noise_statistics import float_wav


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['renderer','sanitizer','probe','host','plugin','template','observed-report','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Choose a new report')
    prior=json.loads(a.observed_report.read_text());rows=[]
    bound=bindings()|{n:sha256(Path(n)) for n in ['tools/audio/noise/rmx_noise_random_reference.py','tools/audio/noise/noise_random_statistics.py','tools/audio/noise/noise_reference_trajectory_statistics.py','tools/probes/noise_random_probe.cpp']};binary={k:sha256(getattr(a,k)) for k in ['renderer','sanitizer','probe','host']};prior_hash=sha256(a.observed_report)
    for old in prior['cases']:
        keys=['user','width','main','amount','mode','wave','resonance','sub2','minimum','maximum','frames','block'];c={k:old[k] for k in keys};c['name']=old['name']+'-reconstructed';seconds=c['frames']//48000-4
        path=Path(old['summary']['path'])
        if not path.is_absolute():path=a.observed_report.parent/path
        if sha256(path)!=old['summary']['sha256']:raise ValueError('Observed target summary changed')
        with np.load(path,allow_pickle=False) as z:targets=z['reference_targets'].copy()
        control_blocks=(c['frames']-4832)//32
        replay=subprocess.run([a.probe,str(c['sub2']),str(control_blocks),'own','targets'],capture_output=True,check=True)
        if replay.stderr or replay.stdout!=targets.astype('<f4').tobytes():raise ValueError('Default target trajectory differs from the Original observation')
        print('START RECONSTRUCTED RANDOM',c['width'],seconds,flush=True)
        with tempfile.TemporaryDirectory(prefix='rmx-random-reference-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);write_wav(root/'silence.wav',48000,np.zeros(96000));program=root/'program.tsv';program.write_text(noise.schedule(c));wave=root/'candidate.wav'
            # No target file is passed: this is the actual default generator.
            space.run([a.renderer,root/'silence.wav',wave,program]);digest=sha256(wave);frozen=datetime.now(timezone.utc).isoformat();candidate=summary(wave);rate,audio=float_wav(wave);cp=random_stats.profile(audio,c['sub2'],a.probe);del audio;wave.unlink()
            space.run([a.sanitizer,root/'silence.wav',wave,program],sanitized=True)
            if sha256(wave)!=digest:raise ValueError('Default native/ASAN audio differs')
            wave.unlink();inv=json.loads(space.run([a.host,'inventory',a.plugin]));rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c));(root/(c['name']+'.bin')).write_bytes(noise.state(a.template.read_bytes(),noise.xml(c),str(rsd),str(root)+'/'));plan=noise.plan(c,inv,root);save_json(root/'plan.json',plan);space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block'],'600']);receipt,_=verify_original(root,c,plan,a.host)
            if datetime.fromisoformat(frozen)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Prediction followed fresh Original')
            if receipt['output_sha256']!=old['ordinary_and_observed_sha256']['audio.wav']:raise ValueError('Fresh Original audio differs from the target-observed recording')
            reference=summary(root/'original/audio.wav');rate,audio=float_wav(root/'original/audio.wav');rp=random_stats.profile(audio,c['sub2'],a.probe);del audio
            if not np.array_equal(rp['exposure'],cp['exposure']):raise ValueError('Shared trajectory exposures differ')
            overall=paired.measure(reference,candidate);legacy=screen(reference,candidate);profile=random_stats.measure(rp,cp);n=len(rp['total'])//3;no=len(reference['total'])//3
            thirds={label:random_stats.measure({k:v[first:last] for k,v in rp.items()},{k:v[first:last] for k,v in cp.items()})['verdict'] for label,first,last in [('early',0,n),('late',-n,None)]}
            whole_thirds={label:paired.measure({k:(v[first:last] if k in ['bands','total'] else v) for k,v in reference.items()},{k:(v[first:last] if k in ['bands','total'] else v) for k,v in candidate.items()})['verdict'] for label,first,last in [('early',0,no),('late',-no,None)]}
            self_diagnostic=dict(reference=drift(reference),candidate=drift(candidate));stereo=abs(reference['correlation']-candidate['correlation'])<=.02
            gain=paired.measure(reference,reference|dict(bands=reference['bands']*10**.3,total=reference['total']*10**.3))['verdict'];pg=random_stats.measure(rp,rp|dict(bands=rp['bands']*10**.3,total=rp['total']*10**.3))['verdict']
            if gain!=pg or gain!='different':raise ValueError('Paired gain negative passed')
            stats=a.output.with_name(a.output.stem+'-'+c['name']+'.npz')
            if stats.exists():raise ValueError('Powers already exist')
            np.savez_compressed(stats,reference_bands=reference['bands'],reference_total=reference['total'],candidate_bands=candidate['bands'],candidate_total=candidate['total'],reference_correlation=reference['correlation'],candidate_correlation=candidate['correlation'],reference_profile_bands=rp['bands'],reference_profile_total=rp['total'],candidate_profile_bands=cp['bands'],candidate_profile_total=cp['total'],profile_exposure=rp['exposure'],default_targets=targets)
            passed=overall['verdict']==profile['verdict']=='pass' and stereo and all(v=='pass' for v in thirds.values()) and all(v=='pass' for v in whole_thirds.values())
            rows.append(c|dict(passed=passed,statistics=overall,conservative_independent_screen=legacy,profile=profile,profile_thirds=thirds,overall_thirds=whole_thirds,self_stationarity_diagnostic=self_diagnostic,stereo_correlation_passed=stereo,default_trajectory_matches_observed_original=True,fresh_original_complete_wav_identical_to_prior_observation=True,required_gain_negatives_rejected=True,prediction_sha256=digest,prediction_created_utc=frozen,complete_native_sanitizer_wav_byte_identity=True,original_wav_sha256=receipt['output_sha256'],original_receipt_sha256=sha256(root/'original/receipt.json'),summary=dict(path=str(stats.resolve()),sha256=sha256(stats)),peak_temporary_bytes=space.peak));print('RECONSTRUCTED RANDOM',c['width'],passed,overall['verdict'],profile['verdict'],whole_thirds,thirds,flush=True)
        if root.exists():raise ValueError('Temporary audio retained')
        tmp=a.output.with_suffix('.writing');tmp.write_text(json.dumps(dict(complete=False,cases=rows),indent=2)+'\n');tmp.replace(a.output.with_suffix('.partial.json'))
    if bound!=bindings()|{n:sha256(Path(n)) for n in ['tools/audio/noise/rmx_noise_random_reference.py','tools/audio/noise/noise_random_statistics.py','tools/audio/noise/noise_reference_trajectory_statistics.py','tools/probes/noise_random_probe.cpp']} or prior_hash!=sha256(a.observed_report) or any(sha256(getattr(a,k))!=v for k,v in binary.items()):raise ValueError('Reference campaign inputs changed')
    save_json(a.output,dict(kind='verified-reference-trajectory-random-noise-validation',verification_passed=True,passed=all(c['passed'] for c in rows),cases=rows,source_sha256=bound,binary_sha256=binary,observed_report_sha256=prior_hash,raw_audio_retained=False,all_temporary_directories_removed=True,peak_temporary_bytes=max(c['peak_temporary_bytes'] for c in rows),scope='Actual default reconstructed modulation generator, independent white excitation, fixed User48k/120BPM silent-input programs. Exact target trajectory and repeated Original WAV justify paired covariance for the unchanged ratio-of-mean-power estimand and margins. Full/early/late between-source overall and conditional-profile gates; self-stationarity retained as a time-varying-trajectory diagnostic. Earlier independent-generator and conservative screens remain explicit. No hardware, broad controls/rates/tempos or perceptual percentage.'))
    a.output.with_suffix('.partial.json').unlink()


if __name__=='__main__':main()
