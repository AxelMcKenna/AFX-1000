#!/usr/bin/env python3
"""Fresh cold-input and long-clock Spiral predictions after lifecycle corrections."""
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools.reference_audio import sha256,save_json
import json

base_bindings=campaign.bindings
base_audit=campaign.audit


def bindings():
    return base_bindings()|{'tools/rmx_spiral_motion_fresh3.py':sha256(Path(__file__))}


def source():
    rng=np.random.default_rng(0x53504d4635);x=np.zeros((1536000,2),dtype='<f4')
    for start,n in [(0,96000),(1008000,96000)]:
        t=np.arange(n)/48000
        x[start:start+n]=rng.normal(0,.006,(n,2))+np.column_stack((.031*np.sin(2*np.pi*(89*t+283*t*t)),.019*np.cos(2*np.pi*(211*t+193*t*t))))
    x[3113:7127]*=.03;x[29113:32273]=0
    for f in [0,15,31,32,127,159,160,191,1007,12019,48031,97117,145129,217109,264173,963113,1008019,1199017,1259719]:x[f]+=rng.uniform(-.17,.17,2)
    return x


def recipe():
    rng=np.random.default_rng(0x53504d4636);boundary=[0,1,3,4,5,8,9,16,28,29,63,64,65,66,127,128,129,130,131,192,254,255];rows=[]
    for i in range(64):
        changes=[]
        for j,frame in enumerate([3707,8513,17011,34019,61013,96131,144319,240277,1008113,1259719]):
            # The first sixteen hold controls through startup before later gestures.
            if i<16 and j<5:continue
            for control in ['main','time','pitch','enabled']:
                raw=int(j%2==1) if control=='enabled' else int(rng.choice(boundary)) if j<7 else int(rng.integers(256))
                changes.append(dict(frame=frame,control=control,raw=raw))
        rows.append(dict(name=f'spiral-motion-fresh3-{i:03d}',direction=['up','down'][i%2],main=boundary[(i*5)%len(boundary)] if i<44 else int(rng.integers(256)),time=int(rng.integers(256)),pitch=int(rng.integers(256)),source='program',block=[31,8,4093,79,263,17,4096,32,1021,127][i%10],changes=changes))
    return rows


def audit(a):
    result=base_audit(a)
    path=a.output/'verification.json';report=json.loads(path.read_text())
    report['scope']='Fresh predictions preceded every Original capture. Default48k/120BPM input-only AutoButton1; nonzero input from frame0, 32-second programs crossing the slow clock reversal, held startup and combined gestures. Whole/wet, one-second and event windows plus complete prediction/native/sanitizer WAV byte identity. No live-wrapper, other-profile or hardware qualification.'
    path.rename(a.output/'verification-raw.json')
    save_json(path,report)
    return result


if __name__=='__main__':
    campaign.bindings=bindings;campaign.source=source;campaign.recipe=recipe;campaign.audit=audit
    raise SystemExit(campaign.main())
