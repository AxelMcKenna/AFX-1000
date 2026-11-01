#!/usr/bin/env python3
"""Independently audit Noise powers paired by a verified default trajectory."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from tools.reference_audio import sha256,save_json
from tools.rmx_noise_power_audit import moments,verdict
from tools.rmx_noise_motion_power_audit import phase


def paired(a,ta,b,tb):
    def interval(x,y,margin):
        mx=np.sum(x,axis=0)/len(x);my=np.sum(y,axis=0)/len(y)
        delta=(10/np.log(10))*np.log(my/mx)
        _,variance=moments(y/my-x/mx)
        half=(30/np.log(10))*np.sqrt(variance)
        return delta,half,np.abs(delta)+half<=margin,np.abs(delta)-half>margin
    d,h,p,diff=interval(a,b,.5);dl,hl,pl,ld=interval(ta,tb,.1)
    mask=np.sum(a,axis=0)/len(a)>=(np.sum(ta,axis=0)/len(ta))[None,:]*1e-4
    result='pass' if np.all(p[mask]) and np.all(pl) else 'different' if np.any(diff[mask]) or np.any(ld) else 'inconclusive'
    return result,d,h,dl,hl,mask


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['report','probe','sanitizer','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();d=json.loads(a.report.read_text());rows=[]
    if d['kind']!='verified-reference-trajectory-random-noise-validation' or not d['verification_passed'] or d['raw_audio_retained'] or not d['all_temporary_directories_removed'] or d['peak_temporary_bytes']>512*1024**2:raise ValueError('Invalid trajectory report')
    for c in d['cases']:
        if not all(c[k] for k in ['default_trajectory_matches_observed_original','fresh_original_complete_wav_identical_to_prior_observation','complete_native_sanitizer_wav_byte_identity']):raise ValueError('Trajectory prerequisite failed')
        path=Path(c['summary']['path'])
        if not path.is_absolute():path=a.report.parent/path
        if sha256(path)!=c['summary']['sha256']:raise ValueError('Powers changed')
        with np.load(path,allow_pickle=False) as z:
            rb,rt,cb,ct=[z[k] for k in ['reference_bands','reference_total','candidate_bands','candidate_total']]
            x,tx,y,ty=[z[k] for k in ['reference_profile_bands','reference_profile_total','candidate_profile_bands','candidate_profile_total']]
            if rb.shape!=cb.shape or rb.shape!=(len(rt),30,2) or rt.shape!=ct.shape or x.shape!=y.shape or x.shape!=(len(tx),4,6,2) or tx.shape!=ty.shape or tx.shape!=(len(tx),4,2) or z['profile_exposure'].shape!=(len(tx),4):raise ValueError('Power extent differs')
            if any(not np.isfinite(v).all() or np.min(v)<0 for v in [rb,rt,cb,ct,x,tx,y,ty]) or np.any(z['profile_exposure']<=0):raise ValueError('Invalid powers/exposures')
            blocks=(c['frames']-4832)//32
            for probe in [a.probe,a.sanitizer]:
                r=subprocess.run([probe,str(c['sub2']),str(blocks),'own','targets'],check=True,capture_output=True)
                if r.stderr or r.stdout!=z['default_targets'].astype('<f4').tobytes():raise ValueError('Default trajectory replay differs')
            ov,delta,half,level,lh,mask=paired(rb,rt,cb,ct);errors=[]
            for actual,key in [(delta,'mean_power_ratio_db'),(half,'band_interval_half_db'),(level,'whole_level_ratio_db'),(lh,'whole_level_interval_half_db')]:errors.append(float(np.max(np.abs(actual-np.asarray(c['statistics'][key])))))
            if ov!=c['statistics']['verdict'] or not np.array_equal(mask,c['statistics']['meaningful_bands']):raise ValueError('Overall verdict differs')
            pv,pd,ph,pl,plh,mask=phase(x,tx,y,ty)
            for actual,key in [(pd,'mean_paired_band_log_ratio_db'),(ph,'band_interval_half_db'),(pl,'mean_paired_level_log_ratio_db'),(plh,'level_interval_half_db')]:errors.append(float(np.max(np.abs(actual-np.asarray(c['profile'][key])))))
            if pv!=c['profile']['verdict'] or not np.array_equal(mask,c['profile']['meaningful_bands']) or max(errors)>1e-10:raise ValueError('Profile arithmetic differs')
            n=len(tx)//3;no=len(rt)//3
            thirds=dict(early=phase(x[:n],tx[:n],y[:n],ty[:n])[0],late=phase(x[-n:],tx[-n:],y[-n:],ty[-n:])[0])
            whole=dict(early=paired(rb[:no],rt[:no],cb[:no],ct[:no])[0],late=paired(rb[-no:],rt[-no:],cb[-no:],ct[-no:])[0])
            diagnostic={name:verdict(b[:no],t[:no],b[-no:],t[-no:])[0] for name,b,t in [('reference',rb,rt),('candidate',cb,ct)]}
            stereo=abs(float(z['reference_correlation'])-float(z['candidate_correlation']))<=.02
            passed=ov==pv=='pass' and stereo and all(v=='pass' for v in thirds.values()) and all(v=='pass' for v in whole.values())
            if thirds!=c['profile_thirds'] or whole!=c['overall_thirds'] or diagnostic!=c['self_stationarity_diagnostic'] or passed!=c['passed'] or stereo!=c['stereo_correlation_passed'] or verdict(rb,rt,cb,ct)[0]!=c['conservative_independent_screen']['verdict']:raise ValueError('Aggregate/diagnostic differs')
            if paired(rb,rt,rb*10**.3,rt*10**.3)[0]!='different' or phase(x,tx,x*10**.3,tx*10**.3)[0]!='different':raise ValueError('Gain negative passed')
            rows.append(dict(case=c['name'],passed=passed,overall=ov,profile=pv,overall_thirds=whole,profile_thirds=thirds,maximum_arithmetic_difference=max(errors),default_native_asan_targets_match=True,required_gain_negatives_rejected=True,summary_sha256=sha256(path)))
    if all(r['passed'] for r in rows)!=d['passed']:raise ValueError('Report aggregate differs')
    save_json(a.output,dict(kind='independent-reference-trajectory-noise-audit',verification_passed=True,cases=rows,report_sha256=sha256(a.report),auditor_sha256=sha256(Path(__file__)),shared_auditor_sha256=sha256(Path('tools/rmx_noise_power_audit.py')),profile_auditor_sha256=sha256(Path('tools/rmx_noise_motion_power_audit.py')),scope='Separate sums/einsum HAC arithmetic for paired ratio of mean powers, profiles, full/early/late gates, stereo, default target replay and gain negatives. Self-stationarity and earlier independent variance screens retained as diagnostics. No waveform or perceptual percentage.'))


if __name__=='__main__':main()
