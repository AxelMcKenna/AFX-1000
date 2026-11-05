#!/usr/bin/env python3
"""Independently recompute Random Noise intervals and separate-source labels."""
import argparse,json,subprocess,tempfile,hashlib
from pathlib import Path
import numpy as np
from tools.audio.common.reference_audio import save_json,sha256
from tools.audio.noise.rmx_noise_power_audit import verdict
from tools.audio.noise.rmx_noise_motion_power_audit import phase


def labels(probe,raw,source,seconds):
    count=(seconds*48000-256)//128+1
    p=subprocess.run([probe,'--bins',str(raw),str(source),str(4*48000+128-4864),'128',str(count)],capture_output=True,check=True)
    values=np.frombuffer(p.stdout,dtype=np.uint8)
    if p.stderr or len(values)!=count or np.any(values>3):raise ValueError('Random label replay differs')
    exposures=np.asarray([np.bincount(values[max(0,i*3750-1):min(count,(i+1)*3750-1)],minlength=4) for i in range(seconds//10)])
    return exposures


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,action='append',required=True)
    for key in ['probe','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();rows=[];reports={};probe_hash=sha256(a.probe)
    with tempfile.TemporaryDirectory(prefix='rmx-random-power-audit-',dir='/private/tmp') as directory:
        target_file=Path(directory)/'targets.txt'
        for path in a.report:
            d=json.loads(path.read_text());reports[str(path)]=sha256(path)
            if d['kind']!='bounded-noise-random-audio-validation' or d['raw_audio_retained'] or not d['all_temporary_directories_removed'] or d['peak_temporary_bytes']>512*1024**2:raise ValueError('Invalid Random report')
            for c in d['cases']:
                summary=Path(c['summary']['path'])
                if not summary.is_absolute():summary=path.parent/summary
                if sha256(summary)!=c['summary']['sha256']:raise ValueError('Power summary changed')
                with np.load(summary,allow_pickle=False) as z:
                    rb,rt,cb,ct=[z[k] for k in ['reference_bands','reference_total','candidate_bands','candidate_total']]
                    x,tx,y,ty=[z[k] for k in ['reference_profile_bands','reference_profile_total','candidate_profile_bands','candidate_profile_total']]
                    seconds=d['stationary_seconds'];epochs=seconds//10
                    if rb.shape!=cb.shape or rt.shape!=ct.shape or rb.shape!=(seconds//2,30,2) or x.shape!=y.shape or x.shape!=(epochs,4,6,2) or tx.shape!=ty.shape:raise ValueError('Summary extent differs')
                    if x.shape!=(epochs,4,6,2) or tx.shape!=(epochs,4,2):raise ValueError('Random profile extent differs')
                    for name,source in [('reference',target_file),('candidate','own')]:
                        targets=z[name+'_targets'];digest=hashlib.sha256(targets.astype('<f4').tobytes()).hexdigest()
                        if digest!=c[name+'_target_controls_sha256']:raise ValueError('Target stream changed')
                        if name=='reference':target_file.write_text('\n'.join(format(v,'.17g') for v in targets)+'\n')
                        actual=labels(a.probe,c['sub2'],source,seconds)
                        if not np.array_equal(actual,z[name+'_profile_exposure']) or np.any(actual<=0):raise ValueError('Source-specific profile exposures differ')
                    frames=(c['frames']-4832)//32
                    p=subprocess.run([a.probe,str(c['sub2']),str(frames),'own','targets'],capture_output=True,check=True)
                    if p.stdout!=z['candidate_targets'].astype('<f4').tobytes() or p.stderr:raise ValueError('Production own targets differ')
                    ov,od,oh,ol,olh=verdict(rb,rt,cb,ct)
                    if ov!=c['statistics']['verdict']:raise ValueError('Overall verdict differs')
                    errors=[]
                    for i,old in enumerate(c['statistics']['bands']):
                        for ch,row in enumerate(old['channels']):errors.append(abs(od[i,ch]-row['candidate_minus_reference_db']));errors.append(float(np.max(np.abs(np.asarray(row['approximate_99pct_interval_db'])-[od[i,ch]-oh[i,ch],od[i,ch]+oh[i,ch]]))))
                    for ch,row in enumerate(c['statistics']['whole_level']):errors.append(abs(ol[ch]-row['candidate_minus_reference_db']));errors.append(float(np.max(np.abs(np.asarray(row['approximate_99pct_interval_db'])-[ol[ch]-olh[ch],ol[ch]+olh[ch]]))))
                    pv,pd,ph,pl,plh,mask=phase(x,tx,y,ty)
                    for actual,key in [(pd,'mean_paired_band_log_ratio_db'),(ph,'band_interval_half_db'),(pl,'mean_paired_level_log_ratio_db'),(plh,'level_interval_half_db')]:errors.append(float(np.max(np.abs(actual-np.asarray(c['profile'][key])))))
                    if pv!=c['profile']['verdict'] or not np.array_equal(mask,c['profile']['meaningful_bands']) or max(errors)>1e-10:raise ValueError('Profile or interval arithmetic differs')
                    n=len(tx)//3;thirds=dict(early=phase(x[:n],tx[:n],y[:n],ty[:n])[0],late=phase(x[-n:],tx[-n:],y[-n:],ty[-n:])[0])
                    no=len(rt)//3;stability={name:verdict(v[:no],t[:no],v[-no:],t[-no:])[0] for name,v,t in [('reference',rb,rt),('candidate',cb,ct)]}
                    stereo=abs(float(z['reference_correlation'])-float(z['candidate_correlation']))<=.02
                    qualified=ov==pv=='pass' and stereo and all(v=='pass' for v in thirds.values()) and all(v=='pass' for v in stability.values())
                    if thirds!=c['profile_thirds'] or stability!=c['stationarity'] or stereo!=c['stereo_correlation_passed'] or qualified!=c['passed']:raise ValueError('Aggregate or stability verdict differs')
                    if verdict(rb,rt,rb*10**.3,rt*10**.3)[0]!='different' or phase(x,tx,x*10**.3,tx*10**.3)[0]!='different':raise ValueError('Gain negative control passed')
                    if phase(x,tx,x[:,::-1],tx[:,::-1])[0]!=c['negative_controls']['reversed_control_bins']:raise ValueError('Control-bin reversal diagnostic differs')
                    rows.append(dict(case=c['name'],qualified=qualified,overall=ov,profile=pv,profile_thirds=thirds,stationarity=stability,maximum_arithmetic_difference=max(errors),source_specific_exposures_reproduced=True,own_target_stream_reproduced=True,required_gain_negatives_rejected=True,summary_sha256=sha256(summary),report_sha256=reports[str(path)]))
    if sha256(a.probe)!=probe_hash:raise ValueError('Probe changed')
    save_json(a.output,dict(kind='independent-random-noise-power-audit',verification_passed=True,cases=rows,report_sha256=reports,auditor_sha256=sha256(Path(__file__)),shared_auditor_sha256=sha256(Path('tools/audio/noise/rmx_noise_power_audit.py')),profile_auditor_sha256=sha256(Path('tools/audio/noise/rmx_noise_motion_power_audit.py')),probe_sha256=probe_hash,raw_audio_retained=False,scope='Independent interval/mask/early-late/qualification arithmetic, source-specific exposure replay and own-target verification from retained summaries. Default candidate and Original target sequences are different. Raw audio is not reread.'))


if __name__=='__main__':main()
