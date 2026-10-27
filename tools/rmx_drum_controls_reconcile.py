#!/usr/bin/env python3
"""Reconcile scalar control calibration with independently captured original drums."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256
from tools.rmx_drums import checked, require
from tools.rmx_drum_controls import recipe, source_hashes


def reconcile(args):
    report=json.loads(args.characterization.read_text());numeric=json.loads(args.numeric.read_text())
    require(report['original_captures_verified'] and report['source_sha256']==source_hashes(),'Characterization source differs')
    require(numeric['script_sha256']==sha256(Path('tools/rmx_drum_observe.py')),'Numeric observer differs')
    require([r['case'] for r in report['cases']]==[c['name'] for c in recipe()],'Control case set differs')
    tables=numeric['shared_pitch_level_tables'];level=tables['level_values'];require(len(level)==256 and level[128]==1,'Level table differs')
    originals={};provenance={}
    for c,row in zip(recipe(),report['cases']):
        a,p=checked(args.session,c);require(all(row[k]==v for k,v in p.items()),'Original provenance differs')
        receipt=json.loads((args.session/c['name']/'receipt.json').read_text())
        require(any(b['sha256']==numeric['binary_sha256'] for b in receipt['plugin']['binary_files']),'Observed binary differs')
        originals[c['name']]=a;provenance[c['name']]=p
    rows=[]
    for c,row in zip(recipe(),report['cases']):
        a=originals[c['name']];base=originals[f'controls-{c["drum"]}-level-128']
        require(row['bit_identical_to_neutral']==bool(np.array_equal(a.view(np.uint32),base.view(np.uint32))),'Pitch identity differs')
        if c['variant']!='level':continue
        predicted=base.astype(float)*level[c['level']];error=a.astype(float)-predicted;energy=float(np.sum(a.astype(float)**2))
        relative=float(np.sqrt(np.sum(error*error)/energy)) if energy>1e-20 else None
        require(relative<=1e-6 if relative is not None else not np.any(a),'Level table fails original waveform law check')
        scale=float(np.sum(base.astype(float)*a.astype(float))/np.sum(base.astype(float)**2))
        require(abs(scale-row['level_law_diagnostic']['scale_relative_to_raw128'])<1e-14,'Characterization scale differs')
        rows.append(dict(case=c['name'],receipt_sha256=provenance[c['name']]['receipt_sha256'],raw=c['level'],
                         predicted_scale=level[c['level']],observed_scale=scale,relative_original_shape_error=relative,
                         scope='Reference-vs-reference level-law verification only; no candidate waveform acceptance.'))
    edges={drum:{str(pitch):report['cases'][next(i for i,c in enumerate(recipe()) if c['drum']==drum and c['variant']=='pitch' and c['pitch']==pitch)]['bit_identical_to_neutral']
                 for pitch in [120,121,135,136]} for drum in ['kick','snare','clap','hat']}
    require(all(v=={'120':False,'121':True,'135':True,'136':False} for v in edges.values()),'Pitch edge characterization differs')
    high={drum:float(np.max(np.abs(originals[f'controls-{drum}-level-255']))) for drum in edges}
    require(all(v>1 for v in high.values()),'Original high-level behaviour differs')
    save_json(args.report,dict(kind='rmx220-drum-control-scalar-waveform-reconciliation',passed=True,
        original_capture_count=76,level_cases=rows,pitch_edges_bit_identical_to_raw128=edges,maximum_level_peaks=high,
        characterization_sha256=sha256(args.characterization),numeric_sha256=sha256(args.numeric),script_sha256=sha256(Path(__file__)),
        scope='Original discovery only. The independently read level table predicts all36 recorded level programs. Neutral pitch edge observations and above-unity high-level peaks are retained. This does not qualify candidate control implementation, automation, broader profiles, full256 waveform controls or Engine integration.'))
    print('Verified 76 original receipts and reconciled 36 level programs with scalar calibration')
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('session','characterization','numeric','report'):parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(reconcile(parser.parse_args()))


if __name__=='__main__':main()
