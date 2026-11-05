#!/usr/bin/env python3
"""Replay retained Original control hashes through native and ASAN models."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from tools.audio.common.reference_audio import save_json, sha256
from tools.audio.drums.rmx_drums import require


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures',type=Path,action='append',required=True)
    parser.add_argument('--prediction-probe',type=Path)
    for name in ['probe','sanitizer','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();rows=[];sources={}
    binaries={name:sha256(getattr(args,name)) for name in ['probe','sanitizer']}
    prediction_probe=args.prediction_probe or args.probe;prediction_binary=sha256(prediction_probe)
    for directory in args.captures:
        path=directory/'verification.json';sources[str(path)]=sha256(path);matrix=json.loads(path.read_text())
        require(matrix['passed'] and not matrix['raw_audio_retained'] and matrix['all_temporary_directories_removed'],'Unverified observations')
        require(matrix['observer_sha256']==sha256(Path('research/audio/experiments/noise_motion_observer.py')),'Observer changed')
        for old in matrix['cases']:
            case=old['case']
            if case['wave']>2:continue
            path=directory/(case['name']+'.json');require(sha256(path)==old['trace_sha256'],'Control trace changed')
            trace=json.loads(path.read_text());require(trace['blocks']==2849 and trace['binary_sha256']=='dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced','Wrong control extent/Original')
            arguments=[str(case['sub2']),str(case['wave']),str(trace['blocks'])]
            native=subprocess.run([str(args.probe),*arguments],capture_output=True,check=True)
            sanitizer=subprocess.run([str(args.sanitizer),*arguments],capture_output=True,check=True)
            require(not native.stderr and not sanitizer.stderr and native.stdout==sanitizer.stdout,'Control native/ASAN differs')
            data=native.stdout;digest=hashlib.sha256(data).hexdigest()
            require(len(data)==2849*32*4 and digest==trace['lfo_f32le_sha256'],'Whole control stream differs')
            values=np.frombuffer(data,dtype='<f4').reshape(-1,32)
            require(np.isfinite(values).all() and np.max(np.abs(values))<=1,'Invalid controls')
            error=0.
            for sample in trace['rows']:
                require(sample['raw_sub2']==case['sub2'] and sample['wave']==case['wave'],'Control mapping differs')
                error=max(error,float(np.max(np.abs(values[sample['block']]-sample['lfo']))))
            require(error==0 and len(old['ordinary_and_observed_sha256'])==6,'Sparse read/invariance differs')
            prospective='prediction_sha256' in old
            if prospective:
                require(old['prediction_sha256']==digest and old['renderer_sha256']==prediction_binary,'Prospective prediction changed')
                require(datetime.fromisoformat(old['prediction_created_utc']).timestamp()<path.stat().st_mtime,'Prediction followed observation')
            rows.append(dict(case=case,controls=2849*32,complete_original_native_asan_f32_identity=True,control_sha256=digest,
                maximum_sparse_read_error=error,prospective=prospective,trace_sha256=sha256(path),
                ordinary_and_observed_sha256=old['ordinary_and_observed_sha256'],original_receipt_sha256=old['original_receipt_sha256']))
    require(all(sha256(getattr(args,k))==v for k,v in binaries.items()),'Probe changed')
    save_json(args.output,dict(kind='original-noise-motion-control-audit',verification_passed=True,cases=rows,
        captures_sha256=sources,binary_sha256=binaries,prediction_probe_sha256=prediction_binary,model_sha256=sha256(Path('include/rmx/NoiseModulator.h')),
        observer_sha256=sha256(Path('research/audio/experiments/noise_motion_observer.py')),auditor_sha256=sha256(Path(__file__)),
        raw_audio_retained=False,scope='Complete deterministic Triangle/Saw/Square control streams, native/ASAN byte identity, retained Original hashes and sparse scalar reads. Ordinary/observed audio invariance was checked live before cleanup; raw Original audio is not reread. This does not compare generated noise samples or establish audio/perceptual accuracy.'))


if __name__=='__main__':main()
