#!/usr/bin/env python3
"""Characterize original drum pitch/level laws; this is discovery, not fidelity."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_drums import DRUMS, FRAMES, checked, plan_for, require
from tools.rmx_factory_match import IDENTITY, new_directory, run


def recipe():
    rows=[]
    for drum in DRUMS:
        controls=[('level',v,128) for v in [0,1,32,64,96,128,160,224,255]]
        controls += [('pitch',128,v) for v in [0,64,119,120,121,135,136,137,192,255]]
        for variant,level,pitch in controls:
            rows.append(dict(name=f'controls-{drum}-{variant}-{level if variant=="level" else pitch}',drum=drum,variant=variant,
                             block=128,hits=[48000,192000,336000],level=level,pitch=pitch))
    return rows


def source_hashes():
    return {name:sha256(Path(name)) for name in ['tools/rmx_drum_controls.py','tools/rmx_drums.py',
                        'tools/rmx_factory_match.py','tools/noise_statistics.py','tools/reference_audio.py']}


def capture(args):
    binding=source_hashes();root=new_directory(args.session)
    inventory=json.loads(run([args.host,'inventory',args.plugin]));require(all(inventory[k]==v for k,v in IDENTITY.items()),'Wrong original plug-in')
    save_json(root/'inventory.json',inventory);source=root/'silence.wav';write_wav(source,48000,np.zeros(FRAMES*2));cases=recipe()
    for c in cases:
        plan=root/(c['name']+'.json');save_json(plan,plan_for(c,inventory))
        run([args.host,'render',args.plugin,source,plan,root/c['name'],c['block']])
        c['receipt_sha256']=sha256(root/c['name']/'receipt.json');print('Captured',c['name'],flush=True)
    require(binding==source_hashes(),'Control scan source changed during capture')
    save_json(root/'matrix.json',dict(kind='rmx220-drum-controls-discovery',source_sha256=binding,cases=cases,
            scope='Original neutral-profile48k/120BPM pitch/level discovery; no candidate or sound-match claim.'))
    return 0


def analyze(args):
    binding=source_hashes();manifest=json.loads((args.session/'matrix.json').read_text())
    require(manifest['source_sha256']==binding,'Control scan source differs');records={}
    for c in recipe():
        a,provenance=checked(args.session,c);receipt=json.loads((args.session/c['name']/'receipt.json').read_text())
        require(receipt['host_sha256']==sha256(args.host),'Reference host differs')
        for binary in receipt['plugin']['binary_files']:
            require(sha256(Path(receipt['plugin']['bundle'])/binary['path'])==binary['sha256'],'Original plug-in differs')
        records[c['name']]=(c,a,provenance)
    rows=[]
    for c,a,provenance in records.values():
        baseline=records[f'controls-{c["drum"]}-level-128'][1];x=baseline.astype(float);y=a.astype(float)
        require(np.array_equal(a[:,0].view(np.uint32),a[:,1].view(np.uint32)),'Unexpected stereo difference')
        nonzero=np.flatnonzero(np.any(np.abs(a)>1e-12,axis=1))
        row=provenance|dict(drum=c['drum'],variant=c['variant'],level=c['level'],pitch=c['pitch'],
            peak=float(np.max(np.abs(y))),rms=float(np.sqrt(np.mean(y*y))),
            first_output_frame=int(nonzero[0]) if len(nonzero) else None,
            last_output_frame=int(nonzero[-1]) if len(nonzero) else None,
            bit_identical_to_neutral=bool(np.array_equal(a.view(np.uint32),baseline.view(np.uint32))))
        if c['variant']=='level':
            # Reference-vs-reference law identification only. Never used as a
            # fitted candidate comparison gain or as a sound acceptance score.
            scale=float(np.sum(x*y)/np.sum(x*x));residual=y-x*scale;energy=float(np.sum(y*y))
            row['level_law_diagnostic']=dict(scale_relative_to_raw128=scale,
                normalized_shape_residual=float(np.sqrt(np.sum(residual*residual)/energy)) if energy>1e-20 else None,
                absolute_shape_residual_rms=float(np.sqrt(np.mean(residual*residual))))
        rows.append(row);print('Verified',c['name'],flush=True)
    require(binding==source_hashes(),'Control scan source changed during analysis')
    save_json(args.report,dict(kind='rmx220-drum-controls-characterization',original_captures_verified=True,source_sha256=binding,
            cases=rows,full_drum_match=False,
            scope='76 original discovery programs across four drums. Static neutral-profile pitch/level laws only. Reference-vs-reference scale diagnostics identify a future control hypothesis; they are not candidate fidelity, comparison gain fitting or prospective validation.'))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for command in ('capture','analyze'):
        q=commands.add_parser(command)
        for name in ('host','session'):q.add_argument('--'+name,type=Path,required=True)
        q.add_argument('--plugin' if command=='capture' else '--report',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__=='__main__':main()
