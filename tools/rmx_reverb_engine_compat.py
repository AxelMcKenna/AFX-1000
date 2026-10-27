#!/usr/bin/env python3
"""Transfer prior live reverb qualification only when complete renders agree.

Checks the committed1513-case Up/Down reports, original receipts/auxiliary
files, old WAVs and schedules before rerendering the current live Engine.
This is compatibility evidence, not a new original-reference campaign.
"""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import source_hashes
from tools.rmx_factory_match import IDENTITY,new_directory,run


def verify(args):
    root=new_directory(args.output);repo=Path(__file__).resolve().parents[1];binding=source_hashes();used={};rows=[];previous={}
    host_hash=sha256(args.reference_host)
    kinds=['up','down'] if args.effect=='both' else [args.effect]
    renderers={kind:getattr(args,kind).resolve() for kind in kinds};binaries={kind:sha256(path) for kind,path in renderers.items()}
    for kind in kinds:
        report=repo/'research/audio/measurements'/f'2026-10-27-reverb-{kind}-engine-validation-48k.json'
        d=json.loads(report.read_text());require(d['passed'] and len(d['cases'])==(1321 if kind=='up' else 192),'Wrong prior live qualification')
        previous[kind]=(report,d,sha256(report))
    needed={c['receipt_sha256'] for _,d,_ in previous.values() for c in d['cases']}
    names={c['case'] for _,d,_ in previous.values() for c in d['cases']};receipts={}
    paths=subprocess.check_output(['rg','--files',str(args.prior_root.resolve()),'-g','receipt.json'],text=True).splitlines()
    for name in paths:
        path=Path(name)
        if path.parent.name in names:
            digest=sha256(path)
            if digest in needed:receipts.setdefault(digest,path)
    require(needed<=receipts.keys(),'Missing original receipts from prior qualification')
    def unchanged(path,digest):
        path=Path(path).resolve();stat=path.stat();stamp=(stat.st_size,stat.st_mtime_ns)
        if path in used:require(used[path]==(digest,stamp),'Artifact changed or has inconsistent binding')
        else:require(sha256(path)==digest,'Artifact hash differs: '+str(path));used[path]=(digest,stamp)
    for kind in kinds:
        report,d,report_hash=previous[kind];unchanged(report,report_hash)
        directories=[args.prior_root/n for n in (['reverb-up-engine-regressions-v1','reverb-up-engine-fresh-v1'] if kind=='up' else ['reverb-engine-regression-v1','reverb-engine-fresh-v1'])]
        for index,c in enumerate(d['cases']):
            require(c['passed'],'Prior case is not qualified');receipt_path=receipts[c['receipt_sha256']];unchanged(receipt_path,c['receipt_sha256']);receipt=json.loads(receipt_path.read_text())
            require(receipt['complete'] and receipt['role']=='reference' and all(receipt['plugin'][k]==v for k,v in IDENTITY.items()),'Wrong original identity')
            require(receipt['host_sha256']==host_hash,'Original host differs')
            for name,field in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
                unchanged(receipt_path.parent/name,receipt[field])
            require(receipt['output_sha256']==c['output_sha256'] and receipt['plan_sha256']==c['plan_sha256'] and receipt['input_sha256']==c['input_sha256'],'Prior original binding differs')
            source=Path(receipt['input_path']);unchanged(source,c['input_sha256'])
            for member in receipt['plugin']['binary_files']:unchanged(Path(receipt['plugin']['bundle'])/member['path'],member['sha256'])
            matches=[]
            for directory in directories:
                for prefix in [c['case'],c.get('stage','')+'-'+c['case']]:
                    path=directory/(prefix+'.wav')
                    if path.exists() and sha256(path)==c['candidate_sha256']:matches.append(path)
            require(matches,'Missing prior candidate WAV');old=matches[0];old_dry=old.with_name(old.stem+'-dry.wav');plan=old.with_suffix('.tsv')
            unchanged(old,c['candidate_sha256']);unchanged(old_dry,c['dry_trace_sha256']);unchanged(plan,c['schedule_sha256'])
            prefix=f'{kind}-{index}-{c["case"]}';output=root/(prefix+'.wav');dry=root/(prefix+'-dry.wav')
            invocation=[renderers[kind],source,output,plan]
            invocation+=['faded','post','read','32',dry,'output','0','startup','0'] if kind=='down' else [dry]
            run(invocation);rate,a=float_wav(old);new_rate,b=float_wav(output)
            require(rate==new_rate==48000 and a.shape==b.shape and np.isfinite(b).all(),'Current candidate extent/rate/finite values differ')
            values=bool(np.array_equal(a,b));dry_exact=sha256(dry)==c['dry_trace_sha256'];byte_exact=sha256(output)==c['candidate_sha256']
            passed=values and dry_exact
            rows.append(dict(effect=kind,case=c['case'],stage=c.get('stage',''),passed=passed,receipt_sha256=c['receipt_sha256'],
                prior_report_sha256=report_hash,prior_output_sha256=c['candidate_sha256'],candidate_sha256=sha256(output),
                schedule_sha256=c['schedule_sha256'],dry_sha256=sha256(dry),audio_sample_values_identical=values,audio_byte_identical=byte_exact,dry_byte_identical=dry_exact))
            print('UNCHANGED' if passed else 'FAIL',kind,c['case'],flush=True)
    for path,(digest,stamp) in used.items():
        stat=path.stat();require((stat.st_size,stat.st_mtime_ns)==stamp,'Original/prior artifact changed during compatibility run')
    require(binding==source_hashes() and all(sha256(renderers[k])==v for k,v in binaries.items()) and sha256(args.reference_host)==host_hash,'Current source/renderer/host changed')
    save_json(root/'verification.json',dict(kind='rmx-live-reverb-engine-compatibility',passed=all(r['passed'] for r in rows),cases=rows,
        source_sha256=binding,renderer_sha256=binaries,verifier_sha256=sha256(Path(__file__)),reference_host_sha256=host_hash,
        programs=len(rows),audio_sample_values_identical=sum(r['audio_sample_values_identical'] for r in rows),audio_byte_identical=sum(r['audio_byte_identical'] for r in rows),dry_byte_identical=sum(r['dry_byte_identical'] for r in rows),
        scope='Complete prior live Up/Down programs, including all existing control/startup windows. Current full WAV sample values must equal the prior qualified Engine renders exactly, and dry traces must remain byte-identical. Original identities, receipt/auxiliary hashes, input, binary files and schedules are checked. This transfers existing scoped waveform evidence without gain/alignment fitting; it is not new original evidence or a full reverb/device match.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--effect',choices=['up','down','both'],default='both')
    for name in ['up','down','prior-root','reference-host','output']:p.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(verify(p.parse_args()))


if __name__=='__main__':main()
