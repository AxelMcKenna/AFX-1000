#!/usr/bin/env python3
"""Independent cold/long Spiral holdout after exact startup interpolation order."""
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_prospective as campaign
from tools import rmx_spiral_motion_fresh3 as long_campaign
from tools.reference_audio import sha256

base_bindings=campaign.bindings


def bindings():
    return base_bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_spiral_motion_fresh3.py','tools/rmx_spiral_motion_fresh4.py']}


def source():
    rng=np.random.default_rng(0x53504d4637);x=np.zeros((1536000,2),dtype='<f4')
    for start,n in [(0,120000),(984000,120000)]:
        t=np.arange(n)/48000
        x[start:start+n]=rng.normal(0,.0075,(n,2))+np.column_stack((.027*np.cos(2*np.pi*(109*t+349*t*t)),.033*np.sin(2*np.pi*(167*t+271*t*t))))
    x[1973:5189]*=.009;x[37973:41911]=0
    for f in [0,1,17,31,32,63,127,159,160,191,263,1009,13717,49379,121007,193031,271019,961193,984017,1197731,1296973]:x[f]+=rng.uniform(-.18,.18,2)
    return x


def recipe():
    rng=np.random.default_rng(0x53504d4638);boundary=[0,3,4,5,8,9,16,28,29,63,64,65,66,127,128,129,130,131,192,254,255];rows=[]
    for i in range(32):
        changes=[]
        for j,frame in enumerate([4013,7919,15173,31379,59117,93113,137719,237973,1001173,1296973]):
            if i<8 and j<5:continue
            for control in ['main','time','pitch','enabled']:
                raw=int(j%2==1) if control=='enabled' else int(rng.choice(boundary)) if j<7 else int(rng.integers(256))
                changes.append(dict(frame=frame,control=control,raw=raw))
        rows.append(dict(name=f'spiral-motion-fresh4-{i:03d}',direction=['down','up'][i%2],main=boundary[(i*8)%len(boundary)] if i<24 else int(rng.integers(256)),time=int(rng.integers(256)),pitch=int(rng.integers(256)),source='program',block=[4093,17,127,4096,8,1021,31,263,32,79][i%10],changes=changes))
    return rows


if __name__=='__main__':
    campaign.bindings=bindings;campaign.source=source;campaign.recipe=recipe;campaign.audit=long_campaign.audit
    raise SystemExit(campaign.main())
