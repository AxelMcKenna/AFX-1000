#!/usr/bin/env python3
"""Prospective Spiral Up/Down selection, interrupted fades and first selection."""
import json
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools.reference_audio import save_json,sha256

base_bindings=campaign.bindings
base_audit=campaign.audit


def bindings():return base_bindings()|{'tools/rmx_spiral_switch.py':sha256(Path(__file__))}


def source():
    rng=np.random.default_rng(0x53505331);x=np.zeros((600000,2),dtype='<f4');t=np.arange(264000)/48000
    x[:len(t)]=rng.normal(0,.006,(len(t),2))+np.column_stack((.027*np.sin(2*np.pi*(127*t+191*t*t)),.023*np.cos(2*np.pi*(173*t+307*t*t))))
    x[97117:101113]*=.02;x[193031:198319]=0
    for f in [0,31,159,1009,48031,96113,144319,193031,264173,288019]:x[f]+=rng.uniform(-.16,.16,2)
    return x


def recipe():
    rng=np.random.default_rng(0x53505332);rows=[]
    for i in range(16):
        direction=['up','down'][i%2];initial=i%2
        frames=[96113,144319,192193,240277] if i<8 else [96113,96114,96146,96192,96286,97122,144319] if i<12 else [193,96113,144319,192193]
        changes=[]
        for j,frame in enumerate(frames):
            changes.append(dict(frame=frame,control='direction',raw=1-initial if j%2==0 else initial))
            if i%4>=2 and j%2==0:changes += [dict(frame=frame,control=k,raw=int(rng.integers(256))) for k in ['main','time','pitch']]
        changes += [dict(frame=288419,control='enabled',raw=0),dict(frame=336607,control='enabled',raw=1)]
        rows.append(dict(name=f'spiral-switch1-{i:02d}',direction=direction,initial_enabled=i<12,main=[4,64,128,255][i%4],time=int(rng.integers(256)),pitch=int(rng.integers(256)),block=[8,31,127,263,4093,32,79,4096][i%8],source='program',changes=changes))
    return rows


def audit(a):
    result=base_audit(a);path=a.output/'verification.json';report=json.loads(path.read_text())
    report['scope']='Spiral Up/Down selection under input, interrupted selection fades and initial selection from off; combined knobs and later off/on. Default48k/120BPM input-only AutoButton1. Frozen pre-capture predictions; whole/wet/one-second/event windows and complete prediction/native/sanitizer WAV byte identity. No live Engine/wrapper or hardware qualification.'
    path.rename(a.output/'verification-raw.json');save_json(path,report);return result


if __name__=='__main__':
    campaign.bindings=bindings;campaign.source=source;campaign.recipe=recipe;campaign.audit=audit
    raise SystemExit(campaign.main())
