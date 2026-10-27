#!/usr/bin/env python3
"""Check existing original-reference drum gestures through explicit AU/VST3 bundles."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import FRAMES,checked,require
from tools.rmx_drums_motion import ACCEPTANCE,original_plan,recipe,source_hashes
from tools.rmx_factory_match import new_directory,run
from tools.rmx_filter_match import screen

DELIVERY=dict(relative_rms_limit=1e-5,absolute_peak_limit=1e-5,reported_latency_frames=32)


def pitch_value(raw):
    travel=(raw-128)*(24/127 if raw>=128 else 24/128)
    return (travel+24)/48


def check(args):
    binding=source_hashes();script=sha256(Path(__file__));native=json.loads(args.comparison.read_text())
    require(native['passed'] and native['stage']=='fresh' and native['source_sha256']==binding and native['acceptance']==ACCEPTANCE,'Wrong native comparison')
    cases=recipe('fresh');require([c['name'] for c in cases]==[r['case'] for r in native['cases']],'Native recipe differs')
    root=new_directory(args.output);inventory=json.loads(run([args.host,'inventory',args.plugin]));save_json(root/'inventory.json',inventory)
    identity={k:inventory[k] for k in ['name','manufacturer','version']};require(identity==dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'),'Wrong project bundle')
    def setting(name,value):
        matches=[p for p in inventory['parameters'] if p['name']==name]
        if name=='Bypass':matches=[p for p in matches if p['id']=='773352680']
        require(len(matches)==1,'Missing/ambiguous wrapper control: '+name)
        return {k:matches[0][k] for k in ['name','id','index']}|dict(value=value)
    rows=[]
    for c,old in zip(cases,native['cases']):
        a,provenance=checked(args.session,c,plan_builder=original_plan);require(all(old[k]==v for k,v in provenance.items()),'Original native provenance differs')
        receipt=json.loads((args.session/c['name']/'receipt.json').read_text());require(receipt['host_sha256']==sha256(args.reference_host),'Original host differs')
        for member in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/member['path'])==member['sha256'],'Original binary differs')
        values={'Auto BPM':0,'Quantize':0,'Scene FX':0,'Scene enabled':0,'Isolate enabled':0,'Release lever':0,'Sample source':0,'Default / User settings':0,
          'Sampler level':c['level']/255,'Sampler pitch travel':pitch_value(c['pitch']),'Sampler mute':0,'Bypass':0,'Send/return':0,'Input gain':2/3,'Output gain':2/3}
        parameters=[setting(k,v) for k,v in values.items()];events=[]
        for e in c['changes']:
            at=e['frame'];kind=e['type'];value=e['value']
            if kind in ('H','R'):events.append(dict(frame=at,type='midi',bytes=[0x90 if kind=='H' else 0x80,36+value,127 if kind=='H' else 0]))
            else:events.append(setting('Sampler level' if kind=='L' else 'Sampler pitch travel',value/255 if kind=='L' else pitch_value(value))|dict(frame=at,type='parameter'))
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,sample_rate=48000,bpm=120,tail_seconds=0,
          post_render_message_pump_ms=100,parameters=parameters,events=events)
        path=root/(c['name']+'.json');save_json(path,plan);folder=root/c['name'];run([args.host,'render',args.plugin,args.session/'silence.wav',path,folder,c['block']])
        receipt=json.loads((folder/'receipt.json').read_text())
        require(receipt['complete'] and receipt['role']=='candidate' and receipt['frames']==FRAMES and receipt['sample_rate']==48000 and receipt['maximum_block_size']==c['block']
          and receipt['host_sha256']==sha256(args.host) and receipt['input_sha256']==provenance['input_sha256'] and receipt['plugin']['format']==inventory['format'],'Wrapper receipt differs')
        require(json.loads((folder/'plan.json').read_text())==plan and sha256(path)==receipt['plan_sha256']==sha256(folder/'plan.json'),'Wrapper plan differs')
        for name,field in [('audio.wav','output_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==receipt[field],'Wrapper artifact changed')
        for member in receipt['plugin']['binary_files']:require(sha256(args.plugin/member['path'])==member['sha256'],'Wrapper binary changed')
        log=json.loads((folder/'parameter-log.json').read_text())['entries'];expected=[p|dict(frame=-1) for p in parameters]+[e for e in events if e['type']=='parameter']
        require(len(log)==len(expected),'Wrapper control event count differs')
        for req,actual in zip(expected,log):
            require(all(actual[k]==req[k] for k in ['frame','name','id','index']) and np.float32(actual['requested_value'])==np.float32(req['value']) and abs(actual['immediate_readback']-req['value'])<=1e-6,'Wrapper control readback differs')
        rate,b=float_wav(folder/'audio.wav');native_path=args.comparison.parent/(c['name']+'.wav');require(sha256(native_path)==old['candidate_sha256'],'Native output changed');nr,n=float_wav(native_path)
        require(rate==nr==48000 and a.shape==b.shape==n.shape==(FRAMES,2),'Wrapper extent/rate differs')
        err=b.astype(float)-n.astype(float);energy=float(np.sum(n.astype(float)**2));relative=float(np.sqrt(np.sum(err*err)/energy)) if energy>1e-20 else None;peak=float(np.max(np.abs(err)))
        delivery=peak<=DELIVERY['absolute_peak_limit'] and (relative is None or relative<=DELIVERY['relative_rms_limit']) and receipt['reported_latency_frames']==32
        a,b=a[32:],b[32:];whole=screen(a,b);windows=[]
        for w in old['windows']:windows.append({k:w[k] for k in ['kind','frame','start','stop']}|dict(score=screen(a[w['start']:w['stop']],b[w['start']:w['stop']])))
        passed=whole['passed'] and all(w['score']['passed'] for w in windows)
        rows.append(provenance|dict(wrapper_receipt_sha256=sha256(folder/'receipt.json'),candidate_sha256=sha256(folder/'audio.wav'),native_sha256=old['candidate_sha256'],reported_latency=receipt['reported_latency_frames'],
          delivery_passed=delivery,relative_wrapper_native_error=relative,max_wrapper_native_absolute_difference=peak,whole=whole,windows=windows,passed=passed))
        print('PASS' if passed and delivery else 'FAIL',inventory['format'],c['name'],flush=True)
    require(binding==source_hashes() and script==sha256(Path(__file__)),'Sources changed')
    passed=all(r['passed'] and r['delivery_passed'] for r in rows)
    save_json(root/'verification.json',dict(kind='rmx220-drums-motion-wrapper-regression',passed=passed,format=inventory['format'],programs=len(rows),cases=rows,source_sha256=binding,script_sha256=script,
      host_sha256=sha256(args.host),native_comparison_sha256=sha256(args.comparison),acceptance=ACCEPTANCE,wrapper_delivery=DELIVERY,
      scope='Sixteen existing original-reference gestures through normalized parameters and MIDI36–39 in an explicit local AU/VST3 bundle. Fixed32/32 waveform checks, separate tight wrapper/native delivery limits, no gain or alignment fit. No new originals, DAW/controller, custom profiles, rolls or hardware qualification.'))
    return 0 if passed else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['host','reference-host','plugin','comparison','session','output']:p.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(check(p.parse_args()))


if __name__=='__main__':main()
