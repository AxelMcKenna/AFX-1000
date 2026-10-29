#!/usr/bin/env python3
"""Independent Spiral selection holdout after pitch-history and dry-fade fixes."""
import json
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools.reference_audio import save_json,sha256

base_bindings=campaign.bindings
base_audit=campaign.audit


def bindings():return base_bindings()|{'tools/rmx_spiral_switch_fresh2.py':sha256(Path(__file__))}


def source():
    rng=np.random.default_rng(0x53505333);x=np.zeros((840000,2),dtype='<f4');t=np.arange(312000)/48000
    x[:len(t)]=rng.normal(0,.008,(len(t),2))+np.column_stack((.022*np.sin(2*np.pi*(149*t+223*t*t)),.026*np.cos(2*np.pi*(199*t+281*t*t))))
    x[7913:11179]*=.017;x[149113:154319]=0
    for f in [0,17,31,159,197,1013,48031,96113,144319,193031,312173,576019]:x[f]+=rng.uniform(-.18,.18,2)
    return x


def recipe():
    rng=np.random.default_rng(0x53505334);rows=[];bound=[0,4,8,16,28,29,63,64,65,66,127,128,129,130,131,192,254,255]
    for i in range(32):
        initial=i%2;changes=[]
        for j,frame in enumerate([17,197,1013,48031,96113,144319,192193,240277,288419,336607]):
            if i<8 and j<5:continue
            changes.append(dict(frame=frame,control='direction',raw=(initial+j+1)%2))
            if i%4>=2:changes += [dict(frame=frame,control=k,raw=int(rng.choice(bound)) if j<7 else int(rng.integers(256))) for k in ['main','time','pitch']]
            if i>=16 and j in [3,6]:changes.append(dict(frame=frame+33,control='direction',raw=(initial+j)%2))
        changes += [dict(frame=384419,control='enabled',raw=0),dict(frame=432607,control='enabled',raw=1)]
        rows.append(dict(name=f'spiral-switch2-{i:02d}',direction=['up','down'][initial],initial_enabled=i%3!=0,
            main=bound[(i*7)%len(bound)] if i<24 else int(rng.integers(256)),time=int(rng.integers(256)),pitch=int(rng.integers(256)),
            block=[4093,17,127,4096,8,1021,31,263,32,79][i%10],source='program',changes=changes))
    return rows


def audit(a):
    result=base_audit(a);path=a.output/'verification.json';report=json.loads(path.read_text())
    report['scope']='Fresh Spiral Up/Down selection, interrupted fades, initial off, early selection and combined controls. Default48k/120BPM input-only AutoButton1. Frozen pre-capture predictions, whole/wet/one-second/event windows and complete prediction/native/sanitizer WAV byte identity. No live Engine/wrapper or hardware qualification.'
    path.rename(a.output/'verification-raw.json');save_json(path,report);return result


if __name__=='__main__':
    campaign.bindings=bindings;campaign.source=source;campaign.recipe=recipe;campaign.audit=audit
    raise SystemExit(campaign.main())
