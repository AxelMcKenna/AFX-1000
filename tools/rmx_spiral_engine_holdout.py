#!/usr/bin/env python3
"""Fresh Original holdout for the integrated Spiral Engine, including short touches."""
import json,subprocess
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools.rmx_drums import require
from tools.reference_audio import save_json,sha256

base_bindings=campaign.bindings
base_predict=campaign.predict
base_audit=campaign.audit


def bindings():return base_bindings()|{'tools/rmx_spiral_engine_holdout.py':sha256(Path(__file__))}


def source():
    rng=np.random.default_rng(0x53504531);x=np.zeros((672000,2),dtype='<f4');t=np.arange(336000)/48000
    x[:len(t)]=rng.normal(0,.0065,(len(t),2))+np.column_stack((.029*np.cos(2*np.pi*(131*t+257*t*t)),.024*np.sin(2*np.pi*(229*t+163*t*t))))
    x[8713:13179]*=.013;x[169113:174319]=0
    for f in [0,1,9,17,31,159,197,1013,48031,96113,144319,193031,336173,432019]:x[f]+=rng.uniform(-.18,.18,2)
    return x


def recipe():
    rng=np.random.default_rng(0x53504532);rows=[];boundary=[0,4,8,28,29,63,64,65,66,127,128,129,130,131,192,255]
    for i in range(16):
        initial=i%2;changes=[]
        if i>=8:
            anchor=1 if i<12 else 96113
            changes += [dict(frame=anchor,control='enabled',raw=1),dict(frame=anchor+8,control='enabled',raw=0),dict(frame=anchor+16,control='enabled',raw=1)]
        for j,frame in enumerate([4013,48031,144319,192193,288419,384607]):
            changes.append(dict(frame=frame,control='direction',raw=(initial+j+1)%2))
            changes += [dict(frame=frame,control=k,raw=int(rng.choice(boundary))) for k in ['main','time','pitch']]
        changes.sort(key=lambda e:e['frame'])
        rows.append(dict(name=f'spiral-engine-fresh1-{i:02d}',direction=['up','down'][initial],initial_enabled=i<8 or i>=12,
            main=boundary[i],time=int(rng.integers(256)),pitch=int(rng.integers(256)),source='program',block=[17,4093,8,127,4096,31,263,1021][i%8],changes=changes))
    return rows


def predict(a):
    require('rmx::Engine::process(' in subprocess.check_output(['nm','-C',str(a.renderer)],text=True),'Prediction is not from the live Engine');return base_predict(a)


def audit(a):
    result=base_audit(a);path=a.output/'verification.json';report=json.loads(path.read_text());f=json.loads((a.session/'prediction.json').read_text())
    for renderer in [a.sanitizer,Path(f['renderer'])]:require('rmx::Engine::process(' in subprocess.check_output(['nm','-C',str(renderer)],text=True),'Replay is not the live Engine')
    report['live_engine']=True
    report['scope']='Fresh integrated Engine programs: cold input, initially off, short touches, Up/Down selection and combined controls. Default48k/manual120 input-only, Original AutoButton1. Frozen pre-capture predictions; whole/wet/one-second/event windows and complete prediction/native/sanitizer WAV byte identity. No wrapper, broader-profile or hardware qualification.'
    path.rename(a.output/'verification-raw.json');save_json(path,report);return result


if __name__=='__main__':
    campaign.bindings=bindings;campaign.source=source;campaign.recipe=recipe;campaign.predict=predict;campaign.audit=audit
    raise SystemExit(campaign.main())
