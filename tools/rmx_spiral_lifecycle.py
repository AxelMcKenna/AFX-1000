#!/usr/bin/env python3
"""Freeze and audit first activation after an initially disabled Spiral scene."""
import json
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools.reference_audio import save_json,sha256

base_bindings=campaign.bindings
base_audit=campaign.audit


def bindings():
    return base_bindings()|{'tools/rmx_spiral_lifecycle.py':sha256(Path(__file__))}


def source():
    rng=np.random.default_rng(0x53504c31);x=np.zeros((600000,2),dtype='<f4');t=np.arange(288000)/48000
    x[:len(t)]=rng.normal(0,.007,(len(t),2))+np.column_stack((.025*np.sin(2*np.pi*(113*t+179*t*t)),.029*np.cos(2*np.pi*(181*t+241*t*t))))
    x[29011:48017]*=.03;x[119113:124319]=0
    for f in [0,31,159,1009,48031,96113,144319,193031,264173,288019]:x[f]+=rng.uniform(-.19,.19,2)
    return x


def recipe():
    rng=np.random.default_rng(0x53504c32);rows=[]
    for direction in ['up','down']:
        for i,anchor in enumerate([1,31,33,159,1009,48031,96113,144319]):
            changes=[dict(frame=anchor,control='enabled',raw=1)]
            changes += [dict(frame=anchor+4013,control=k,raw=int(rng.integers(256))) for k in ['main','time','pitch']]
            changes += [dict(frame=anchor+24031,control='enabled',raw=0),dict(frame=anchor+42019,control='enabled',raw=1)]
            rows.append(dict(name=f'spiral-lifecycle-first-{direction}-{i:02d}',direction=direction,
                main=[0,4,16,64,128,192,255,129][i],time=int(rng.integers(256)),pitch=int(rng.integers(256)),
                block=[8,31,127,263,4093,32,79,4096][i],source='program',initial_enabled=False,changes=changes))
    return rows


def audit(a):
    result=base_audit(a);path=a.output/'verification.json';report=json.loads(path.read_text())
    report['scope']='Initially disabled Spiral, first activation at varied input/callback boundaries, later combined knobs and off/on. Default48k/120BPM input-only AutoButton1, nonzero input from frame0. Frozen pre-capture predictions, whole/wet/one-second/event windows and complete prediction/native/sanitizer WAV byte identity. No effect-type switching, live Engine/wrapper or hardware qualification.'
    path.rename(a.output/'verification-raw.json');save_json(path,report);return result


if __name__=='__main__':
    campaign.bindings=bindings;campaign.source=source;campaign.recipe=recipe;campaign.audit=audit
    raise SystemExit(campaign.main())
