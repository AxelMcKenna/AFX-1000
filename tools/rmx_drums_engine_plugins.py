#!/usr/bin/env python3
"""Check AU/VST3 MIDI delivery and complete drum audio against verified Engine cases."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_drums import DRUMS, checked, require
from tools.rmx_drums_engine import ACCEPTANCE, original_plan, recipe
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen


def check(args):
    root=new_directory(args.output);inventory=json.loads(run([args.host,'inventory',args.plugin]));save_json(root/'inventory.json',inventory)
    identity={k:inventory[k] for k in ('name','manufacturer','version')}
    require(identity==dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'),'Wrong wrapper')
    engine=json.loads(args.engine_comparison.read_text());require(engine['passed'] and engine['live_engine'] and engine['acceptance']==ACCEPTANCE,'Engine evidence differs')
    require([r['case'] for r in engine['cases']]==[c['name'] for c in recipe()],'Engine case set differs');rows=[]
    def setting(name,value):
        found=[p for p in inventory['parameters'] if p['name']==name]
        # JUCE VST3 adds a separate wrapper bypass; AU reorders parameter indices.
        # This is the measured stable ID of the project's bypass parameter.
        if name=='Bypass':found=[p for p in found if p['id']=='773352680']
        require(len(found)==1,'Missing/ambiguous wrapper parameter: '+name)
        return {k:found[0][k] for k in ('index','id','name')}|dict(value=value)
    for c,old in zip(recipe(),engine['cases']):
        raw_a,provenance=checked(args.session,c,cold_kick=c['drum']=='kick',plan_builder=original_plan)
        require(all(old[k]==v for k,v in provenance.items()),'Original/Engine provenance differs')
        travel=(c['pitch']-128)*(24/127 if c['pitch']>=128 else 24/128)
        values={'Auto BPM':0,'Quantize':0,'Scene FX':1/9,'Scene enabled':0,'Isolate enabled':0,'Release lever':0,
                'Sample source':0,'Default / User settings':0,'Sampler level':c['level']/255,'Sampler pitch travel':(travel+24)/48,
                'Sampler mute':0,'Bypass':0,'Send/return':0,'Output gain':2/3,'Input gain':2/3}
        pads=c.get('pads',[list(DRUMS).index(c['drum'])]*len(c['hits']));events=[]
        for at,pad in zip(c['hits'],pads):
            events.extend([dict(frame=at,type='midi',bytes=[0x90,36+pad,127]),dict(frame=at+32,type='midi',bytes=[0x80,36+pad,0])])
        events.sort(key=lambda e:e['frame'])
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,sample_rate=48000,bpm=120,
                  tail_seconds=0,post_render_message_pump_ms=100,parameters=[setting(k,v) for k,v in values.items()],events=events)
        path=root/(c['name']+'.json');save_json(path,plan);folder=root/c['name'];run([args.host,'render',args.plugin,args.session/'silence.wav',path,folder,c['block']])
        receipt=json.loads((folder/'receipt.json').read_text())
        require(receipt['complete'] and receipt['role']=='candidate' and receipt['sample_rate']==48000 and receipt['frames']==480000
                and receipt['maximum_block_size']==c['block'] and receipt['input_sha256']==provenance['input_sha256']
                and receipt['host_sha256']==sha256(args.host) and receipt['plugin']['format']==inventory['format'],'Wrapper receipt differs')
        require(json.loads((folder/'plan.json').read_text())==plan and receipt['plan_sha256']==sha256(folder/'plan.json')==sha256(path),'Wrapper plan differs')
        for filename,field in [('audio.wav','output_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
            require(sha256(folder/filename)==receipt[field],'Wrapper artifact differs')
        for binary in receipt['plugin']['binary_files']:require(sha256(args.plugin/binary['path'])==binary['sha256'],'Wrapper binary differs')
        log=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(log)==len(plan['parameters']),'Wrapper parameter count differs')
        for req,actual in zip(plan['parameters'],log):
            require(actual['frame']==-1 and all(actual[k]==req[k] for k in ('name','index','id')) and np.float32(actual['requested_value'])==np.float32(req['value'])
                    and abs(actual['immediate_readback']-req['value'])<=1e-6,'Wrapper parameter delivery differs')
        rate,raw_b=float_wav(folder/'audio.wav');engine_path=args.engine_comparison.parent/(c['name']+'.wav')
        require(sha256(engine_path)==old['candidate_sha256'],'Engine output changed');_,native=float_wav(engine_path)
        require(rate==48000 and raw_b.shape==raw_a.shape==native.shape,'Wrapper extent/rate differs')
        a,b=raw_a[32:].astype(float),raw_b[32:].astype(float)
        row=provenance|dict(candidate_receipt_sha256=sha256(folder/'receipt.json'),candidate_sha256=sha256(folder/'audio.wav'),
                           engine_sha256=sha256(engine_path),reported_latency=receipt['reported_latency_frames'],whole=screen(a,b),windows=[],
                           max_plugin_engine_absolute_difference=float(np.max(np.abs(raw_b.astype(float)-native.astype(float)))))
        for w in old['windows']:
            left,right=w['start'],w['stop'];row['windows'].append({k:w[k] for k in ('kind','frame','start','stop')}|dict(score=screen(a[left:right],b[left:right])))
        row['passed']=row['reported_latency']==0 and row['whole']['passed'] and all(w['score']['passed'] for w in row['windows']);rows.append(row)
        print('PASS' if row['passed'] else 'FAIL',inventory['format'],c['name'],flush=True)
    save_json(root/'verification.json',dict(kind='rmx220-engine-drums-wrapper-check',passed=all(r['passed'] for r in rows),format=inventory['format'],identity=identity,
        script_sha256=sha256(Path(__file__)),host_sha256=sha256(args.host),plugin_source_sha256=sha256(Path('src/plugin/Plugin.cpp')),
        engine_comparison_sha256=sha256(args.engine_comparison),acceptance=ACCEPTANCE,cases=rows,
        scope='20 existing fresh-original Engine cases through an explicit AU/VST3 bundle, MIDI pad events and normalized parameters. Wrapper regressions, not20 further fresh originals. Effects off, factory48k default profiles/ranges only; no DAW/live hardware or FX routing qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('host','plugin','engine-comparison','session','output'):parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(check(parser.parse_args()))


if __name__=='__main__':main()
