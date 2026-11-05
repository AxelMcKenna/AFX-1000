#!/usr/bin/env python3
"""Replay retained Sidechain detector/control hashes without keeping raw traces."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from tools.audio.common.reference_audio import save_json, sha256
from tools.audio.noise.rmx_noise_sidechain_controls import stimulus


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['report','release-report','probe','sanitizer','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();fresh=json.loads(a.report.read_text());release=json.loads(a.release_report.read_text())
    if not fresh['verification_passed'] or not fresh['all_declared_cases_matched'] or not release['passed']:raise ValueError('An observation is unqualified')
    for name,digest in fresh['source_sha256'].items():
        if sha256(Path(name))!=digest:raise ValueError('Observation source changed: '+name)
    if sha256(a.probe)!=fresh['binary_sha256']['probe'] or sha256(a.sanitizer)!=fresh['binary_sha256']['sanitizer']:raise ValueError('Control probe changed')
    rows=[]
    for old in fresh['cases']+[release]:
        c=old['case'];name=c['name'].removeprefix('sidechain-fresh-')
        if old is release:
            x=np.zeros((192000,2),dtype='<f4');x[:48000]=stimulus('low')
        else:x=stimulus(name)
        native=subprocess.run([a.probe,'--chain',str(c['sub2'])],input=x.tobytes(),capture_output=True,check=True)
        san=subprocess.run([a.sanitizer,'--chain',str(c['sub2'])],input=x.tobytes(),capture_output=True,check=True)
        if native.stderr or san.stderr or native.stdout!=san.stdout:raise ValueError('Native/ASAN control replay differs')
        digest=hashlib.sha256(native.stdout).hexdigest();values=np.frombuffer(native.stdout,dtype='<f4').reshape(-1,65)
        if digest!=old['prediction_sha256'] or digest!=old['observed_trace_sha256'] or len(values)!=old['blocks']:raise ValueError('Retained Original stream hash differs')
        if old.get('maximum_control_error')!=0 or old.get('maximum_detector_error')!=0 or len(old['ordinary_and_observed_sha256'])!=6:raise ValueError('Observation comparison differs')
        if old is not release and hashlib.sha256(values[:,33:].copy().tobytes()).hexdigest()!=old['observed_control_sha256']:raise ValueError('Control-only hash differs')
        if len(values)>1 and hashlib.sha256(values[::-1].copy().tobytes()).hexdigest()==digest:raise ValueError('Reversed timeline negative passed')
        rows.append(dict(case=c['name'],blocks=len(values),control_values=len(values)*32,driver_and_control_values=len(values)*65,complete_original_native_asan_f32_identity=True,prospective=True,observed_trace_sha256=digest,reversed_timeline_rejected=True))
    save_json(a.output,dict(kind='noise-sidechain-complete-control-audit',verification_passed=True,cases=rows,report_sha256=sha256(a.report),release_report_sha256=sha256(a.release_report),auditor_sha256=sha256(Path(__file__)),model_sha256=sha256(Path('include/rmx/NoiseModulator.h')),detector_source_sha256=sha256(Path('src/core/GateDrive.cpp')),binary_sha256=dict(probe=sha256(a.probe),sanitizer=sha256(a.sanitizer)),raw_audio_retained=False,scope='Regenerates seven prospective synthetic-input driver/control predictions, compares complete float32 hashes retained from Original observations, native/ASAN identity and reversed-time negatives. Ordinary/observed audio invariance was checked live before cleanup. No generated Noise audio or perceptual accuracy claim.'))


if __name__=='__main__':main()
