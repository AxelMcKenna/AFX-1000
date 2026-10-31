#!/usr/bin/env python3
"""Independently audit retained Noise block powers after temporary WAV cleanup."""
import argparse
import json
from pathlib import Path
import numpy as np
from tools.reference_audio import sha256, save_json
from tools.rmx_drums import require


def moments(values):
    count = len(values); average = np.sum(values, axis=0)/count; centered = values-average
    variance = np.einsum('i...,i...->...', centered, centered)/(count-1)
    corrected = variance.copy()
    for lag in [1, 2]:
        covariance = np.einsum('i...,i...->...', centered[:-lag], centered[lag:])/(count-lag)
        corrected = corrected + 2*(1-lag/3)*covariance
    return average, np.maximum(variance, corrected)/count


def interval(left, right, margin):
    ma, va = moments(left); mb, vb = moments(right)
    delta = (10/np.log(10))*np.log(np.maximum(mb, 1e-30)/np.maximum(ma, 1e-30))
    half = (30/np.log(10))*np.sqrt(va/np.maximum(ma, 1e-30)**2 + vb/np.maximum(mb, 1e-30)**2)
    return delta, half, np.abs(delta)+half <= margin, np.abs(delta)-half > margin


def verdict(a, ta, b, tb):
    d, h, passed, different = interval(a, b, .5); dl, hl, pl, diff_l = interval(ta, tb, .1)
    meaningful = np.sum(a, axis=0)/len(a) >= (np.sum(ta, axis=0)/len(ta))[None,:]*1e-4
    value = 'pass' if np.all(passed[meaningful]) and np.all(pl) else 'different' if np.any(different[meaningful]) or np.any(diff_l) else 'inconclusive'
    return value, d, h, dl, hl


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--report', type=Path, action='append', required=True); p.add_argument('--output', type=Path, required=True); a = p.parse_args(); rows=[]; sources={}
    for path in a.report:
        report=json.loads(path.read_text()); sources[str(path.resolve())]=sha256(path)
        require(not report['raw_audio_retained'] and report['all_temporary_directories_removed'] and report['peak_temporary_bytes']<=512*1024**2, 'Audio retention/budget differs')
        for case in report['cases']:
            data_path=Path(case['summary']['path'])
            if not data_path.is_absolute(): data_path=path.parent/data_path
            require(sha256(data_path)==case['summary']['sha256'], 'Power summary changed')
            with np.load(data_path,allow_pickle=False) as data:
                x,tx,y,ty=[data[k] for k in ['reference_bands','reference_total','candidate_bands','candidate_total']]
                require(x.shape==y.shape==(len(tx),30,2) and tx.shape==ty.shape==(len(tx),2), 'Power extent differs')
                require(all(np.isfinite(v).all() and np.min(v)>=0 for v in [x,tx,y,ty]), 'Invalid power summary')
                v,d,h,dl,hl=verdict(x,tx,y,ty); old=case['statistics'];require(v==old['verdict'], 'Independent statistical verdict differs')
                errors=[]
                for band,row in enumerate(old['bands']):
                    for ch,channel in enumerate(row['channels']):
                        error=max(abs(channel['candidate_minus_reference_db']-d[band,ch]), abs(channel['approximate_99pct_interval_db'][0]-(d[band,ch]-h[band,ch])), abs(channel['approximate_99pct_interval_db'][1]-(d[band,ch]+h[band,ch])))
                        errors.append(float(error));require(error<1e-10, 'Independent band arithmetic differs')
                for ch,row in enumerate(old['whole_level']):require(abs(row['candidate_minus_reference_db']-dl[ch])<1e-10 and np.max(np.abs(np.asarray(row['approximate_99pct_interval_db'])-[dl[ch]-hl[ch],dl[ch]+hl[ch]]))<1e-10, 'Independent level arithmetic differs')
                n=len(tx)//3;drift={name:verdict(b[:n],t[:n],b[-n:],t[-n:])[0] for name,b,t in [('reference',x,tx),('candidate',y,ty)]}
                require(drift==case['stationarity'], 'Independent drift screen differs')
                correlation=abs(float(data['reference_correlation'])-float(data['candidate_correlation']))<=.02
                require(correlation==case['stereo_correlation_passed'], 'Stereo verdict differs')
                require(case['passed']==(v=='pass' and correlation and all(value=='pass' for value in drift.values())), 'Aggregate verdict differs')
                require(verdict(x,tx,x*10**.3,tx*10**.3)[0]=='different', 'Independent screen accepted3dB error')
                rows.append(dict(case=case['name'],statistical_verdict=v,stationarity=drift,stereo_correlation_passed=correlation,qualified=case['passed'],maximum_arithmetic_difference=max(errors),negative_gain3db_rejected=True,summary_sha256=sha256(data_path),report_sha256=sources[str(path.resolve())]))
    save_json(a.output,dict(kind='independent-retained-noise-power-audit',verification_passed=True,cases=rows,reports_sha256=sources,
        verifier_sha256=sha256(Path(__file__)),scope='Separate float64 sums/einsum moments, HAC uncertainty, every retained band/level interval, stereo gate and early/late-third verdict. Confirms the statistical arithmetic and retained summary binding; does not reconstruct deleted waveforms or assign perceptual accuracy.'))


if __name__=='__main__':main()
