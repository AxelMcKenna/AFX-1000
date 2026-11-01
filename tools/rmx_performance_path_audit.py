#!/usr/bin/env python3
"""Recompute bounded performance verdicts from retained window energy statistics."""
import argparse,gzip,json,math
from pathlib import Path
import numpy as np
from tools.reference_audio import sha256,save_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',action='append',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];sources={}
    for path in a.report:
        d=json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text());sources[str(path)]=sha256(path)
        if not d['verification_passed'] or d['raw_audio_retained'] or not d['all_temporary_directories_removed'] or d['peak_temporary_bytes']>512*1024**2:raise ValueError('Invalid capture campaign')
        previous=None;all_passed=True
        for c in d['cases']:
            if not c['complete_native_sanitizer_wav_identity'] or not c['negative_controls_rejected']:raise ValueError('Capture verification failed')
            passed=True;count=0
            for window in c['windows']+c.get('effect_difference_windows',[]):
                n=window['samples']
                if n!=window['stop']-window['start'] or n<=0 or len(window['reference_energy'])!=2 or len(window['error_energy'])!=2:raise ValueError('Invalid energy extent')
                channels=[]
                for energy,error,old in zip(window['reference_energy'],window['error_energy'],window['score']['channels'],strict=True):
                    if not math.isfinite(energy+error) or min(energy,error)<0:raise ValueError('Invalid energy')
                    relative=math.sqrt(error/energy) if energy>1e-20 else None;absolute=math.sqrt(error/n);v=relative<=.01 if relative is not None else absolute<=1e-8
                    if v!=old['passed'] or (relative is None)!=(old['relative_rms_error'] is None) or not np.isclose(absolute,old['absolute_error_rms'],rtol=1e-12,atol=1e-12) or relative is not None and not np.isclose(relative,old['relative_rms_error'],rtol=1e-12,atol=1e-12):raise ValueError('Window arithmetic differs')
                    channels.append(v)
                v=all(channels)
                if v!=window['score']['passed']:raise ValueError('Window aggregate differs')
                passed &= v;count+=1
            if c['role']=='active':
                if previous is None or previous['role']!='control' or previous['case']['name']!=c['case']['name']+'-control':raise ValueError('Missing matched control')
                whole=all(w['score']['passed'] for w in c['windows'])
                if whole!=c['whole_output_passed']:raise ValueError('Whole-output aggregate differs')
                passed &= previous['passed']
            if passed!=c['passed']:raise ValueError('Program aggregate differs')
            rows.append(dict(case=c['case']['name'],role=c['role'],passed=passed,windows=count,report_sha256=sources[str(path)]));previous=c;all_passed &= passed
        if all_passed!=d['passed']:raise ValueError('Campaign aggregate differs')
    save_json(a.output,dict(kind='retained-performance-window-energy-audit',verification_passed=True,cases=rows,reports_sha256=sources,auditor_sha256=sha256(Path(__file__)),scope='Recomputes unchanged1%perchannel and1e-8 silent-channel gates from retained sums of squares, all whole/second/event/effect-difference aggregates. Independent dot-product comparison and negative controls were run before cleanup. Does not reread deleted waveforms or create new reference evidence. Failed programs remain failed.'))


if __name__=='__main__':main()
