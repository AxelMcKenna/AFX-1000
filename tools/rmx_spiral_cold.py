#!/usr/bin/env python3
"""Capture explicitly developmental Spiral programs with nonzero startup input."""
import argparse, concurrent.futures, json
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion as motion
from tools import rmx_spiral_motion_match as match
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_drums import require
from tools.reference_audio import save_json, sha256, write_wav


def sources():
    rng = np.random.default_rng(0x53504331); n = 180000
    program = np.zeros((n,2), dtype='<f4'); t = np.arange(36000)/48000
    program[:36000] = rng.normal(0,.011,(len(t),2)) + np.column_stack((.032*np.sin(2*np.pi*193*t),.025*np.cos(2*np.pi*733*t)))
    pulses = np.zeros_like(program)
    for f in [0,1,15,31,32,63,159,160,191,255,479,1009,6007,12013,24019,48031]:
        pulses[f] += rng.uniform(-.21,.21,2)
    return dict(program=program,pulses=pulses)


def recipe():
    rows=[]
    for raw in [0,4,8,16,64,128,192,255]:
        for direction in ['up','down']:
            for source in ['program','pulses']:
                i=len(rows);rows.append(dict(name=f'spiral-cold1-{i:03d}',direction=direction,main=raw,
                    time=[0,32,128,255][i%4],pitch=[0,64,130,255][(i//4)%4],source=source,
                    block=[17,127,263,4093][i%4],changes=[]))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['host','plugin','session','renderer']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=new_directory(a.session);bound=match.bindings();own=sha256(Path(__file__));binary=sha256(a.renderer)
    inventory=json.loads(run([a.host,'inventory',a.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original');save_json(root/'inventory.json',inventory)
    for name,audio in sources().items():write_wav(root/(name+'.wav'),48000,audio.ravel())
    def one(c):
        schedule=root/(c['name']+'.tsv');schedule.write_text(match.schedule(c));out=schedule.with_suffix('.wav');run([a.renderer,root/(c['source']+'.wav'),out,schedule])
        plan=root/(c['name']+'.json');save_json(plan,motion.plan_for(c,inventory));run([a.host,'render',a.plugin,root/(c['source']+'.wav'),plan,root/c['name'],c['block']])
        print('COLD DISCOVERY',c['name'],flush=True);return c|dict(receipt_sha256=sha256(root/c['name']/'receipt.json'),candidate_sha256=sha256(out))
    with concurrent.futures.ThreadPoolExecutor(4) as pool:rows=list(pool.map(one,recipe()))
    require(bound==match.bindings() and own==sha256(Path(__file__)) and binary==sha256(a.renderer),'Candidate changed')
    save_json(root/'matrix.json',dict(kind='spiral-cold-development-original',cases=rows,source_sha256=bound,
              verifier_sha256=own,renderer_sha256=binary,scope='Development discovery only. Nonzero initial input, Default48k/120BPM/AutoButton1. No fresh qualification.'))


if __name__=='__main__':main()
