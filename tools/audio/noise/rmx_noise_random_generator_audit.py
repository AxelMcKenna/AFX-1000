#!/usr/bin/env python3
"""Infer Random startup from float control outputs and replay held-out targets."""
import argparse,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from tools.audio.common.reference_audio import sha256,save_json


def generate(first,second,count):
    out=np.empty(count,dtype='<f4')
    for i in range(count):
        signed=second if second<2**31 else second-2**32
        out[i]=np.float32(signed)*np.float32(2**-31)
        first^=second;second=(second+first)&0xffffffff
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['discovery','observed-report','probe','sanitizer','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();discovery=json.loads(a.discovery.read_text());trace=next(c['trace'] for c in discovery['cases'] if c['case']['sub2']==255)
    prefix=np.asarray([t['target'] for t in trace['targets']],dtype='<f4')
    # The first observed output corresponds to a positive integer below2^24:
    # unlike later draws, no integer information was lost to float rounding.
    second=int(float(prefix[0])*2**31)
    if not 0<=second<2**24 or np.float32(second)*np.float32(2**-31)!=prefix[0]:raise ValueError('First output is not an exact small integer')
    center=int(float(prefix[1])*2**31);candidates=list(range(center-4,center+5));solutions=[]
    for next_second in candidates:
        first=((next_second-second)&0xffffffff)^second
        if np.array_equal(generate(first,second,len(prefix)),prefix):solutions.append((first,second))
    if len(solutions)!=1:raise ValueError('Initialization is not unique in the second-output quantization cell')
    first,second=solutions[0];rows=[]
    report=json.loads(a.observed_report.read_text())
    for c in report['cases']:
        path=Path(c['summary']['path'])
        if not path.is_absolute():path=a.observed_report.parent/path
        if sha256(path)!=c['summary']['sha256']:raise ValueError('Observed targets changed')
        with np.load(path,allow_pickle=False) as z:targets=z['reference_targets'].astype('<f4')
        if not np.array_equal(generate(first,second,len(targets)),targets):raise ValueError('Held-out scalar recurrence differs')
        for probe in [a.probe,a.sanitizer]:
            r=subprocess.run([probe,str(c['sub2']),str((c['frames']-4832)//32),'own','targets'],capture_output=True,check=True)
            if r.stderr or r.stdout!=targets.tobytes():raise ValueError('Actual-core default targets differ')
        rows.append(dict(case=c['name'],targets=len(targets),scalar_native_asan_original_identity=True,target_sha256=hashlib.sha256(targets.tobytes()).hexdigest(),summary_sha256=sha256(path)))
    save_json(a.output,dict(kind='output-inferred-random-startup-audit',verification_passed=True,initialization=dict(first=first,second=second),candidate_second_words_tested=candidates,prefix_draws=len(prefix),prefix_sha256=hashlib.sha256(prefix.tobytes()).hexdigest(),held_out_cases=rows,manufacturer_prng_memory_read=False,discovery_sha256=sha256(a.discovery),observed_report_sha256=sha256(a.observed_report),auditor_sha256=sha256(Path(__file__)),binary_sha256={str(p):sha256(p) for p in [a.probe,a.sanitizer]},scope='Output-only inversion of xor/add recurrence and unique startup in the second-draw rounding cell. Long target streams overlap; their counts are not independent observations. Verifies modulation targets, not white-noise excitation or waveform identity.'))


if __name__=='__main__':main()
