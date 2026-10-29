#!/usr/bin/env python3
"""Replay the qualified Release programs through an explicit AU/VST3 bundle."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools import rmx_release as release
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory,run
from tools.rmx_filter_match import screen

DELIVERY=dict(relative_rms_limit=1e-5,absolute_peak_limit=1e-5,reported_latency_frames=32)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['host','reference-host','plugin','comparison','audit','session','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--stage',choices=['discovery','fresh','fresh-v2'],required=True);p.add_argument('--prediction',type=Path)
    args=p.parse_args();binding=release.source_hashes();script=sha256(Path(__file__));plugin_source=sha256(Path('src/plugin/Plugin.cpp'))
    native=json.loads(args.comparison.read_text());audit=json.loads(args.audit.read_text());require(native['passed'] and audit['passed'] and native['source_sha256']==audit['source_sha256']==binding and audit['comparison_sha256']==sha256(args.comparison),'Native qualification differs')
    cases=release.recipe(args.stage);require([r['case'] for r in native['cases']]==[c['name'] for c in cases],'Native coverage differs')
    root=new_directory(args.output);inventory=json.loads(run([args.host,'inventory',args.plugin]));save_json(root/'inventory.json',inventory)
    identity={k:inventory[k] for k in ['name','manufacturer','version']};require(identity==dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'),'Wrong project wrapper')
    def setting(name,value):
        matches=[p for p in inventory['parameters'] if p['name']==name]
        if name=='Bypass':matches=[p for p in matches if p['id']=='773352680']
        require(len(matches)==1,'Missing/ambiguous wrapper parameter '+name)
        return {k:matches[0][k] for k in ['name','id','index']}|dict(value=value)
    rows=[];reference_args=argparse.Namespace(session=args.session,host=args.reference_host,stage=args.stage,prediction=args.prediction)
    for c,old in zip(cases,native['cases'],strict=True):
        a,provenance=release.original(reference_args,c);require(all(old[k]==v for k,v in provenance.items()),'Native original provenance differs')
        values={'Auto BPM':0,'Quantize':0,'Scene FX':1/9,'Scene enabled':0,'Isolate enabled':0,'Release FX':release.TYPES[c['effect']]/2,'Release lever':0,'Default / User settings':0,'Sample source':0,'Bypass':0,'Send/return':0,'Input gain':2/3,'Output gain':2/3}
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,sample_rate=48000,bpm=120,tail_seconds=0,post_render_message_pump_ms=100,parameters=[setting(k,v) for k,v in values.items()],events=[setting('Release lever',e['raw']/255)|dict(frame=e['frame'],type='parameter') for e in c['changes']])
        path=root/(c['name']+'.json');save_json(path,plan);folder=root/c['name'];run([args.host,'render',args.plugin,args.session/(c['source']+'.wav'),path,folder,c['block']])
        receipt=json.loads((folder/'receipt.json').read_text());require(receipt['complete'] and receipt['role']=='candidate' and receipt['frames']==release.FRAMES and receipt['sample_rate']==48000 and receipt['maximum_block_size']==c['block'] and receipt['host_sha256']==sha256(args.host) and receipt['input_sha256']==provenance['input_sha256'] and receipt['plugin']['format']==inventory['format'],'Wrapper receipt differs')
        require(json.loads((folder/'plan.json').read_text())==plan and sha256(path)==receipt['plan_sha256']==sha256(folder/'plan.json'),'Wrapper plan differs')
        for name,key in [('audio.wav','output_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==receipt[key],'Wrapper artifact changed')
        for member in receipt['plugin']['binary_files']:require(sha256(args.plugin/member['path'])==member['sha256'],'Wrapper binary changed')
        expected=[e|dict(frame=-1) for e in plan['parameters']]+plan['events'];actual=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(expected)==len(actual),'Wrapper event count differs')
        final={}
        for request,event in zip(expected,actual,strict=True):
            require(all(request[k]==event[k] for k in ['name','id','index','frame']) and np.float32(request['value'])==np.float32(event['requested_value']) and abs(event['immediate_readback']-request['value'])<=1e-6,'Wrapper control delivery differs');final[request['name']]=request['value']
        after={p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-6 for k,v in final.items()),'Final wrapper controls differ')
        rate,b=float_wav(folder/'audio.wav');native_path=args.comparison.parent/(c['name']+'.wav');require(sha256(native_path)==old['candidate_sha256'],'Native audio changed');nr,n=float_wav(native_path);require(rate==nr==48000 and a.shape==b.shape==n.shape==(release.FRAMES,2),'Wrapper extent differs')
        error=b.astype(float)-n.astype(float);energy=float(np.sum(n.astype(float)**2));relative=float(np.linalg.norm(error)/np.sqrt(energy)) if energy>1e-20 else None;peak=float(np.max(np.abs(error)))
        delivery=peak<=DELIVERY['absolute_peak_limit'] and (relative is None or relative<=DELIVERY['relative_rms_limit']) and receipt['reported_latency_frames']==32
        a,b=a[32:],b[32:];whole=screen(a,b);windows=[{k:w[k] for k in ['kind','start','stop']}|dict(score=screen(a[w['start']:w['stop']],b[w['start']:w['stop']])) for w in old['windows']];passed=whole['passed'] and all(w['score']['passed'] for w in windows)
        rows.append(provenance|dict(passed=passed,delivery_passed=delivery,wrapper_receipt_sha256=sha256(folder/'receipt.json'),wrapper_sha256=receipt['output_sha256'],native_sha256=old['candidate_sha256'],reported_latency=receipt['reported_latency_frames'],relative_wrapper_native_error=relative,max_wrapper_native_difference=peak,whole=whole,windows=windows));print('PASS' if passed and delivery else 'FAIL',inventory['format'],c['name'],flush=True)
    require(binding==release.source_hashes() and script==sha256(Path(__file__)) and plugin_source==sha256(Path('src/plugin/Plugin.cpp')),'Sources changed')
    save_json(root/'verification.json',dict(kind='rmx220-release-wrapper-regression',stage=args.stage,passed=all(r['passed'] and r['delivery_passed'] for r in rows),format=inventory['format'],programs=len(rows),cases=rows,source_sha256=binding,verifier_sha256=script,plugin_source_sha256=plugin_source,host_sha256=sha256(args.host),comparison_sha256=sha256(args.comparison),audit_sha256=sha256(args.audit),acceptance=release.ACCEPTANCE,delivery=DELIVERY,scope='Existing original programs through explicit project bundle and normalized control events; fixed32/32 raw gates and separate native-delivery limits. No new original capture, DAW/controller/hardware or whole-device claim.'))


if __name__=='__main__':main()
