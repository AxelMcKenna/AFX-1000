#!/usr/bin/env python3
"""Diagnostic: compare the filter using a previously observed Random trajectory."""
import argparse
from datetime import datetime,timezone
import json,tempfile
from pathlib import Path
import numpy as np
from tools import rmx_noise_user as noise
from tools import noise_random_statistics as random_stats
from tools.reference_audio import write_wav,save_json,sha256
from tools.rmx_noise_stream import RenderSpace,summary,screen,drift,verify_original,bindings
from tools.noise_statistics import float_wav


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['renderer','sanitizer','probe','host','plugin','template','target-report','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Choose a new report')
    target_report=json.loads(a.target_report.read_text());bound=bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_noise_random_matched.py','tools/noise_random_statistics.py','tools/noise_random_probe.cpp']}
    binaries={k:sha256(getattr(a,k)) for k in ['renderer','sanitizer','probe','host']};target_report_hash=sha256(a.target_report);rows=[]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for old in target_report['cases']:
        keys=['user','width','main','amount','mode','wave','resonance','sub2','minimum','maximum','frames','block'];c={k:old[k] for k in keys};c['name']=old['name']+'-matched';seconds=(c['frames']//48000)-4
        power_path=Path(old['summary']['path'])
        if not power_path.is_absolute():power_path=a.target_report.parent/power_path
        if sha256(power_path)!=old['summary']['sha256']:raise ValueError('Prior target summary changed')
        with np.load(power_path) as z:targets=z['reference_targets'].copy()
        with tempfile.TemporaryDirectory(prefix='rmx-random-matched-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);write_wav(root/'silence.wav',48000,np.zeros(96000));target_file=root/'targets.txt';target_file.write_text('\n'.join(format(v,'.17g') for v in targets)+'\n');program=root/'program.tsv';program.write_text(noise.schedule(c));wave=root/'candidate.wav'
            space.run([a.renderer,root/'silence.wav',wave,program,target_file]);digest=sha256(wave);frozen=datetime.now(timezone.utc).isoformat();candidate=summary(wave);rate,audio=float_wav(wave);cp=random_stats.profile(audio,c['sub2'],a.probe,target_file);del audio;wave.unlink()
            space.run([a.sanitizer,root/'silence.wav',wave,program,target_file],sanitized=True)
            if sha256(wave)!=digest:raise ValueError('Matched native/ASAN audio differs')
            wave.unlink();inventory=json.loads(space.run([a.host,'inventory',a.plugin]));rsd=root/(c['name']+'.RSD');rsd.write_text(noise.xml(c));(root/(c['name']+'.bin')).write_bytes(noise.state(a.template.read_bytes(),noise.xml(c),str(rsd),str(root)+'/'));plan=noise.plan(c,inventory,root);save_json(root/'plan.json',plan);space.run([a.host,'render',a.plugin,root/'silence.wav',root/'plan.json',root/'original',c['block']]);receipt,_=verify_original(root,c,plan,a.host)
            if datetime.fromisoformat(frozen)>=datetime.fromisoformat(receipt['created_at_utc'].replace('Z','+00:00')):raise ValueError('Conditional prediction followed capture')
            if receipt['output_sha256']!=old['ordinary_and_observed_sha256']['audio.wav']:raise ValueError('New Original audio does not reproduce the trajectory-observed capture')
            reference=summary(root/'original/audio.wav');rate,audio=float_wav(root/'original/audio.wav');rp=random_stats.profile(audio,c['sub2'],a.probe,target_file);del audio
            if not np.array_equal(rp['exposure'],cp['exposure']):raise ValueError('Matched trajectory exposures differ')
            overall=screen(reference,candidate);profile=random_stats.measure(rp,cp);n=len(rp['total'])//3;no=len(reference['total'])//3
            profile_thirds={label:random_stats.measure({k:v[first:last] for k,v in rp.items()},{k:v[first:last] for k,v in cp.items()})['verdict'] for label,first,last in [('early',0,n),('late',-n,None)]}
            overall_thirds={label:screen({k:(v[first:last] if k in ['bands','total'] else v) for k,v in reference.items()},{k:(v[first:last] if k in ['bands','total'] else v) for k,v in candidate.items()})['verdict'] for label,first,last in [('early',0,no),('late',-no,None)]}
            stationary=dict(reference=drift(reference),candidate=drift(candidate));stereo=abs(reference['correlation']-candidate['correlation'])<=.02
            gain=screen(reference,reference|dict(bands=reference['bands']*10**.3,total=reference['total']*10**.3))['verdict'];pg=random_stats.measure(rp,rp|dict(bands=rp['bands']*10**.3,total=rp['total']*10**.3))['verdict']
            if gain!=pg or gain!='different':raise ValueError('Matched gain negative passed')
            stats=a.output.with_name(a.output.stem+'-'+c['name']+'.npz')
            if stats.exists():raise ValueError('Summary already exists')
            np.savez_compressed(stats,reference_bands=reference['bands'],reference_total=reference['total'],candidate_bands=candidate['bands'],candidate_total=candidate['total'],reference_correlation=reference['correlation'],candidate_correlation=candidate['correlation'],reference_profile_bands=rp['bands'],reference_profile_total=rp['total'],candidate_profile_bands=cp['bands'],candidate_profile_total=cp['total'],profile_exposure=rp['exposure'],common_targets=targets)
            passed=overall['verdict']==profile['verdict']=='pass' and stereo and all(v=='pass' for v in profile_thirds.values()) and all(v=='pass' for v in overall_thirds.values())
            rows.append(c|dict(conditional_filter_comparison_passed=passed,statistics=overall,profile=profile,profile_thirds=profile_thirds,overall_thirds=overall_thirds,self_stationarity_diagnostic=stationary,stereo_correlation_passed=stereo,required_gain_negatives_rejected=True,prediction_created_utc=frozen,prediction_sha256=digest,complete_native_sanitizer_wav_byte_identity=True,original_complete_wav_matches_prior_target_observation=True,original_wav_sha256=receipt['output_sha256'],original_receipt_sha256=sha256(root/'original/receipt.json'),summary=dict(path=str(stats.resolve()),sha256=sha256(stats)),peak_temporary_bytes=space.peak));print('MATCHED RANDOM',c['width'],passed,overall['verdict'],profile['verdict'],overall_thirds,profile_thirds,flush=True)
        if root.exists():raise ValueError('Temporary audio retained')
    if bound!=bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_noise_random_matched.py','tools/noise_random_statistics.py','tools/noise_random_probe.cpp']} or target_report_hash!=sha256(a.target_report) or any(sha256(getattr(a,k))!=v for k,v in binaries.items()):raise ValueError('Diagnostic inputs changed')
    save_json(a.output,dict(kind='reference-trajectory-conditioned-random-filter-diagnostic',verification_passed=True,all_conditional_filter_comparisons_passed=all(c['conditional_filter_comparison_passed'] for c in rows),cases=rows,source_sha256=bound,binary_sha256=binaries,target_report_sha256=target_report_hash,raw_audio_retained=False,all_temporary_directories_removed=True,peak_temporary_bytes=max(c['peak_temporary_bytes'] for c in rows),scope='Research-only target-source injection into actual Engine, fixed User600-second programs. Fresh Original audio reproduces prior observed target trajectory; native/ASAN audio and between-source overall/early/late/profile gates tested with unchanged margins. Self-stationarity retained as a diagnostic for the deliberately time-varying trajectory. Does not upgrade default independent-generator audio qualification or copy targets into the product.'))


if __name__=='__main__':main()
