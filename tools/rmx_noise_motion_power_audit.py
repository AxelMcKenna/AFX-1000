#!/usr/bin/env python3
"""Independently audit retained overall and control-conditioned Noise powers."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_drums import require
from tools.rmx_noise_power_audit import moments, verdict


def phase_interval(a,b,margin):
    logs=(10/np.log(10))*(np.log(np.maximum(b,1e-30))-np.log(np.maximum(a,1e-30)))
    mean,variance=moments(logs)
    half=3*np.sqrt(variance)
    return mean,half,np.abs(mean)+half<=margin,np.abs(mean)-half>margin


def phase(a,ta,b,tb):
    d,h,p,different=phase_interval(a,b,.5)
    dl,hl,pl,dl_different=phase_interval(ta,tb,.1)
    meaningful=np.sum(a,axis=0)/len(a)>=(np.sum(ta,axis=0)/len(ta))[:,None,:]*1e-4
    v='pass' if np.all(p[meaningful]) and np.all(pl) else 'different' if np.any(different[meaningful]) or np.any(dl_different) else 'inconclusive'
    return v,d,h,dl,hl,meaningful


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,action='append',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();rows=[];sources={}
    for path in args.report:
        report=json.loads(path.read_text());sources[str(path)]=sha256(path)
        require(not report['raw_audio_retained'] and report['all_temporary_directories_removed'] and report['peak_temporary_bytes']<=512*1024**2,'Retention/budget differs')
        for case in report['cases']:
            power_path=Path(case['summary']['path'])
            if not power_path.is_absolute():power_path=path.parent/power_path
            require(sha256(power_path)==case['summary']['sha256'],'Power summary changed')
            with np.load(power_path,allow_pickle=False) as z:
                a,ta,b,tb=[z[k] for k in ['reference_bands','reference_total','candidate_bands','candidate_total']]
                x,tx,y,ty=[z[k] for k in ['reference_profile_bands','reference_profile_total','candidate_profile_bands','candidate_profile_total']]
                bins=3 if case['wave']==2 else 4;n=len(tx)//3
                require(a.shape==b.shape==(len(ta),30,2) and ta.shape==tb.shape==(len(ta),2),'Overall extent differs')
                require(x.shape==y.shape==(len(tx),bins,6,2) and tx.shape==ty.shape==(len(tx),bins,2) and z['profile_exposure'].shape==(len(tx),bins),'Profile extent differs')
                require(np.all(z['profile_exposure']>0) and all(np.isfinite(v).all() and np.min(v)>=0 for v in [a,ta,b,tb,x,tx,y,ty]),'Invalid summary')
                ov,d,h,dl,hl=verdict(a,ta,b,tb);require(ov==case['statistics']['verdict'],'Overall verdict differs')
                for band,old in enumerate(case['statistics']['bands']):
                    for ch,value in enumerate(old['channels']):
                        require(abs(value['candidate_minus_reference_db']-d[band,ch])<1e-10 and np.max(np.abs(np.asarray(value['approximate_99pct_interval_db'])-[d[band,ch]-h[band,ch],d[band,ch]+h[band,ch]]))<1e-10,'Overall band arithmetic differs')
                for ch,value in enumerate(case['statistics']['whole_level']):
                    require(abs(value['candidate_minus_reference_db']-dl[ch])<1e-10 and np.max(np.abs(np.asarray(value['approximate_99pct_interval_db'])-[dl[ch]-hl[ch],dl[ch]+hl[ch]]))<1e-10,'Overall level arithmetic differs')
                pv,pd,ph,pdl,phl,meaningful=phase(x,tx,y,ty);old=case['profile'];require(pv==old['verdict'],'Profile verdict differs')
                errors=[]
                for actual,key in [(pd,'mean_paired_band_log_ratio_db'),(ph,'band_interval_half_db'),(pdl,'mean_paired_level_log_ratio_db'),(phl,'level_interval_half_db')]:
                    error=float(np.max(np.abs(actual-np.asarray(old[key]))));errors.append(error);require(error<1e-10,'Profile arithmetic differs')
                require(np.array_equal(meaningful,np.asarray(old['meaningful_bands'])),'Meaningful mask differs')
                thirds=dict(early=phase(x[:n],tx[:n],y[:n],ty[:n])[0],late=phase(x[-n:],tx[-n:],y[-n:],ty[-n:])[0])
                require(thirds==case['profile_thirds'],'Profile thirds differ')
                n_overall=len(ta)//3;stability={name:verdict(v[:n_overall],t[:n_overall],v[-n_overall:],t[-n_overall:])[0] for name,v,t in [('reference',a,ta),('candidate',b,tb)]}
                require(stability==case['stationarity'],'Overall drift differs')
                correlation=abs(float(z['reference_correlation'])-float(z['candidate_correlation']))<=.02
                require(correlation==case['stereo_correlation_passed'],'Stereo verdict differs')
                qualified=ov==pv=='pass' and correlation and all(v=='pass' for v in stability.values()) and all(v=='pass' for v in thirds.values())
                require(qualified==case['passed'],'Aggregate qualification differs')
                require(verdict(a,ta,a*10**.3,ta*10**.3)[0]=='different','A gain negative control passed')
                inversion=phase(x,tx,x[:,::-1],tx[:,::-1])[0]
                if report['kind']=='bounded-noise-sidechain-audio-validation':
                    require(phase(x,tx,x*10**.3,tx*10**.3)[0]=='different' and case['negative_controls']['profile_gain3db']=='different','A profile gain negative passed')
                    require(inversion==case['negative_controls']['stimulus_phase_inversion'],'Phase reversal diagnostic differs')
                else:require(inversion=='different','A control inversion negative passed')
                gates=['gain3db','profile_gain3db'] if report['kind']=='bounded-noise-sidechain-audio-validation' else ['gain3db','control_polarity_inversion']
                rows.append(dict(case=case['name'],qualified=qualified,overall=ov,profile=pv,profile_thirds=thirds,stationarity=stability,maximum_profile_arithmetic_difference=max(errors),negative_controls_rejected=True,required_negative_control_gates=gates,phase_reversal_diagnostic=inversion,summary_sha256=sha256(power_path),report_sha256=sources[str(path)]))
    save_json(args.output,dict(kind='independent-noise-motion-power-audit',verification_passed=True,cases=rows,report_sha256=sources,auditor_sha256=sha256(Path(__file__)),shared_auditor_sha256=sha256(Path('tools/rmx_noise_power_audit.py')),
        scope='Separate float64 log differences, sums/einsum moments and HAC variance; every overall and profile interval, early/late verdict, stereo gate and aggregate qualification. Confirms retained arithmetic and summary binding after raw audio cleanup; no listening or whole-device percentage.'))


if __name__=='__main__':main()
