#!/usr/bin/env python3
"""Check combined drum/FX reference programs through explicit AU/VST3 bundles."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import ACCEPTANCE,FRAMES,checked,recipe,source_hashes
from tools.rmx_factory_match import new_directory,run
from tools.rmx_filter_match import screen

DELIVERY=dict(relative_rms_error_limit=1e-5,absolute_peak_error_limit=1e-5,reported_latency_frames=32)


def check(args):
    root=new_directory(args.output);binding=source_hashes();script=sha256(Path(__file__));plugin_source=sha256(Path('src/plugin/Plugin.cpp'))
    inventory=json.loads(run([args.host,'inventory',args.plugin]));save_json(root/'inventory.json',inventory);identity={k:inventory[k] for k in ['name','manufacturer','version']}
    require(identity==dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'),'Wrong project wrapper')
    parent=json.loads(args.parent_audit.read_text());engine=json.loads(args.engine_comparison.read_text())
    require(parent['evidence_verified'] and parent['live_engine'] and engine['live_engine'] and engine['backend']=='engine' and engine['source_sha256']==parent['source_sha256'] and engine['renderer_sha256']==parent['renderer_sha256'] and engine['acceptance']==ACCEPTANCE,'Wrong native reference evidence')
    cases=recipe('live-fresh');require([r['case'] for r in engine['cases']]==[c['name'] for c in cases],'Native recipe differs');audited={r['case']:r for r in parent['cases'] if r['stage']=='live-fresh'}
    def setting(name,value):
        matches=[p for p in inventory['parameters'] if p['name']==name]
        if name=='Bypass':matches=[p for p in matches if p['id']=='773352680']
        require(len(matches)==1,'Missing/ambiguous wrapper control: '+name)
        return {k:matches[0][k] for k in ['name','id','index']}|dict(value=value)
    rows=[];baseline=None;call=copy.copy(args);call.host=args.reference_host;call.stage='live-fresh'
    for c,old in zip(cases,engine['cases']):
        a,provenance=checked(call,c);require(all(old[k]==v for k,v in provenance.items()) and audited[c['name']]['comparison_sha256']==sha256(args.engine_comparison) and audited[c['name']]['candidate_sha256']==old['candidate_sha256'],'Original/native binding differs')
        travel=(c['pitch']-128)*(24/127 if c['pitch']>=128 else 24/128)
        values={'Auto BPM':0,'Quantize':0,'Scene FX':c['effect']/9,'Scene enabled':c['enabled'],'Scene source':c['route']/3,
                'Scene depth':c['main']/255,'Scene sub parameter 1':c['amount']/255,'Scene sub parameter 2':c['cutoff']/255,
                'Isolate enabled':0,'Release lever':0,'Sample source':0,'Default / User settings':0,
                'Sampler level':c['level']/255,'Sampler pitch travel':(travel+24)/48,'Sampler mute':0,'Bypass':0,'Send/return':0,'Output gain':2/3,'Input gain':2/3}
        events=[]
        for at,pad in zip(c['hits'],c['pads']):events.extend([dict(frame=at,type='midi',bytes=[0x90,36+pad,127]),dict(frame=at+32,type='midi',bytes=[0x80,36+pad,0])])
        events.sort(key=lambda e:e['frame'])
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,sample_rate=48000,bpm=120,tail_seconds=0,
                  post_render_message_pump_ms=100,parameters=[setting(k,v) for k,v in values.items()],events=events)
        path=root/(c['name']+'.json');save_json(path,plan);folder=root/c['name'];run([args.host,'render',args.plugin,args.session/'program.wav',path,folder,c['block']])
        receipt=json.loads((folder/'receipt.json').read_text())
        require(receipt['complete'] and receipt['role']=='candidate' and receipt['frames']==FRAMES and receipt['sample_rate']==48000 and receipt['maximum_block_size']==c['block'] and receipt['host_sha256']==sha256(args.host) and receipt['input_sha256']==provenance['input_sha256'] and receipt['plugin']['format']==inventory['format'],'Wrapper receipt differs')
        require(json.loads((folder/'plan.json').read_text())==plan and sha256(path)==receipt['plan_sha256']==sha256(folder/'plan.json'),'Wrapper plan differs')
        for name,field in [('audio.wav','output_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==receipt[field],'Wrapper artifact changed')
        for member in receipt['plugin']['binary_files']:require(sha256(args.plugin/member['path'])==member['sha256'],'Wrapper binary changed')
        log=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(log)==len(plan['parameters']),'Wrapper parameter count differs')
        for request,actual in zip(plan['parameters'],log):
            require(actual['frame']==-1 and all(actual[k]==request[k] for k in ['name','id','index']) and np.float32(actual['requested_value'])==np.float32(request['value']) and abs(actual['immediate_readback']-request['value'])<=1e-6,'Wrapper control delivery differs')
        rate,b=float_wav(folder/'audio.wav');native_path=args.engine_comparison.parent/(c['name']+'.wav');require(sha256(native_path)==old['candidate_sha256'],'Native oracle changed');native_rate,native=float_wav(native_path)
        require(rate==native_rate==48000 and a.shape==b.shape==native.shape==(FRAMES,2),'Wrapper extent/rate differs')
        error=b.astype(float)-native.astype(float);energy=float(np.sum(native.astype(float)**2));relative=float(np.linalg.norm(error)/np.sqrt(energy)) if energy>1e-20 else None;peak=float(np.max(np.abs(error)))
        delivery=peak<=DELIVERY['absolute_peak_error_limit'] and (relative is None or relative<=DELIVERY['relative_rms_error_limit']) and receipt['reported_latency_frames']==32
        a=a[32:].astype(float);b=b[32:].astype(float)
        if not c['enabled']:baseline=(a,b)
        da,db=baseline;wa,wb=a-da,b-db
        row=provenance|dict(wrapper_receipt_sha256=sha256(folder/'receipt.json'),candidate_sha256=sha256(folder/'audio.wav'),native_sha256=old['candidate_sha256'],
            reported_latency=receipt['reported_latency_frames'],delivery_passed=delivery,plugin_native_relative_rms_error=relative,max_plugin_native_absolute_difference=peak,
            whole=screen(a,b),wet=screen(wa,wb),tail=screen(a[288000:],b[288000:]),windows=[])
        for window in old['windows']:
            left,right=window['start'],window['stop'];row['windows'].append({k:window[k] for k in ['frame','kind','start','stop']}|dict(whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
        row['raw_gate_passed']=all(row[k]['passed'] for k in ['whole','wet','tail']) and all(w[k]['passed'] for w in row['windows'] for k in ['whole','wet']);rows.append(row)
        print('DELIVERY_PASS' if delivery else 'DELIVERY_FAIL','RAW_PASS' if row['raw_gate_passed'] else 'RAW_FAIL',inventory['format'],c['name'],flush=True)
    require(binding==source_hashes() and script==sha256(Path(__file__)) and plugin_source==sha256(Path('src/plugin/Plugin.cpp')),'Source changed during wrapper checks')
    save_json(root/'verification.json',dict(kind='rmx-live-drums-fx-wrapper-regression',format=inventory['format'],identity=identity,
        wrapper_delivery_passed=all(r['delivery_passed'] for r in rows),all_raw_gates_passed=all(r['raw_gate_passed'] for r in rows),all_whole_outputs_passed=all(r['whole']['passed'] for r in rows),
        cases=rows,source_sha256=binding,script_sha256=script,plugin_source_sha256=plugin_source,host_sha256=sha256(args.host),parent_audit_sha256=sha256(args.parent_audit),
        native_reference_comparison_sha256=sha256(args.engine_comparison),acceptance=ACCEPTANCE,wrapper_delivery=DELIVERY,
        scope='56 existing original-reference drum/Scene programs through an explicit AU/VST3 bundle, normalized parameters and MIDI36–39. These are wrapper regressions, not new originals. A separate tight wrapper/native delivery tolerance and nominal32-frame latency are checked. Every original raw gate is reported without relaxing its limits; a precision-limited raw wet failure is not relabeled as passing. No real DAW, controller or physical hardware qualification.'))
    return 0 if all(r['delivery_passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['host','reference-host','plugin','parent-audit','engine-comparison','session','output']:p.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(check(p.parse_args()))


if __name__=='__main__':main()
