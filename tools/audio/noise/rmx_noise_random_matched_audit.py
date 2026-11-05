#!/usr/bin/env python3
"""Audit synchronized-target filter diagnostics without upgrading default Random."""
import argparse,json
from pathlib import Path
import numpy as np
from tools.audio.common.reference_audio import save_json,sha256
from tools.audio.noise.rmx_noise_power_audit import verdict
from tools.audio.noise.rmx_noise_motion_power_audit import phase


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['report','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();d=json.loads(a.report.read_text());rows=[]
    if d['kind']!='reference-trajectory-conditioned-random-filter-diagnostic' or not d['verification_passed'] or d['raw_audio_retained'] or not d['all_temporary_directories_removed'] or d['peak_temporary_bytes']>512*1024**2:raise ValueError('Invalid conditional report')
    for c in d['cases']:
        path=Path(c['summary']['path'])
        if not path.is_absolute():path=a.report.parent/path
        if sha256(path)!=c['summary']['sha256']:raise ValueError('Summary changed')
        with np.load(path,allow_pickle=False) as z:
            rb,rt,cb,ct=[z[k] for k in ['reference_bands','reference_total','candidate_bands','candidate_total']]
            x,tx,y,ty=[z[k] for k in ['reference_profile_bands','reference_profile_total','candidate_profile_bands','candidate_profile_total']]
            ov,delta,half,level,lh=verdict(rb,rt,cb,ct);pv,pd,ph,pl,plh,mask=phase(x,tx,y,ty);errors=[]
            for i,b in enumerate(c['statistics']['bands']):
                for ch,row in enumerate(b['channels']):errors.extend([abs(delta[i,ch]-row['candidate_minus_reference_db']),float(np.max(np.abs(np.asarray(row['approximate_99pct_interval_db'])-[delta[i,ch]-half[i,ch],delta[i,ch]+half[i,ch]])))])
            for ch,row in enumerate(c['statistics']['whole_level']):errors.extend([abs(level[ch]-row['candidate_minus_reference_db']),float(np.max(np.abs(np.asarray(row['approximate_99pct_interval_db'])-[level[ch]-lh[ch],level[ch]+lh[ch]])))])
            for actual,key in [(pd,'mean_paired_band_log_ratio_db'),(ph,'band_interval_half_db'),(pl,'mean_paired_level_log_ratio_db'),(plh,'level_interval_half_db')]:errors.append(float(np.max(np.abs(actual-np.asarray(c['profile'][key])))))
            if ov!=c['statistics']['verdict'] or pv!=c['profile']['verdict'] or not np.array_equal(mask,c['profile']['meaningful_bands']) or max(errors)>1e-10:raise ValueError('Conditional arithmetic differs')
            n=len(tx)//3;no=len(rt)//3;thirds=dict(early=phase(x[:n],tx[:n],y[:n],ty[:n])[0],late=phase(x[-n:],tx[-n:],y[-n:],ty[-n:])[0]);whole=dict(early=verdict(rb[:no],rt[:no],cb[:no],ct[:no])[0],late=verdict(rb[-no:],rt[-no:],cb[-no:],ct[-no:])[0]);self_diagnostic={name:verdict(b[:no],t[:no],b[-no:],t[-no:])[0] for name,b,t in [('reference',rb,rt),('candidate',cb,ct)]}
            stereo=abs(float(z['reference_correlation'])-float(z['candidate_correlation']))<=.02
            passed=ov==pv=='pass' and stereo and all(v=='pass' for v in thirds.values()) and all(v=='pass' for v in whole.values())
            if thirds!=c['profile_thirds'] or whole!=c['overall_thirds'] or self_diagnostic!=c['self_stationarity_diagnostic'] or passed!=c['conditional_filter_comparison_passed']:raise ValueError('Conditional aggregate differs')
            if verdict(rb,rt,rb*10**.3,rt*10**.3)[0]!='different' or phase(x,tx,x*10**.3,tx*10**.3)[0]!='different':raise ValueError('Gain negative passed')
            rows.append(dict(case=c['name'],conditional_filter_comparison_passed=passed,overall=ov,profile=pv,overall_thirds=whole,profile_thirds=thirds,self_stationarity_diagnostic=self_diagnostic,maximum_arithmetic_difference=max(errors),required_gain_negatives_rejected=True,summary_sha256=sha256(path)))
    save_json(a.output,dict(kind='independent-synchronized-random-filter-audit',verification_passed=True,cases=rows,report_sha256=sha256(a.report),auditor_sha256=sha256(Path(__file__)),shared_auditor_sha256=sha256(Path('tools/audio/noise/rmx_noise_power_audit.py')),profile_auditor_sha256=sha256(Path('tools/audio/noise/rmx_noise_motion_power_audit.py')),scope='Recomputes conditional between-source filter comparisons and retains trajectory self-stationarity separately. No upgrade of default independent-generator Random qualification.'))


if __name__=='__main__':main()
