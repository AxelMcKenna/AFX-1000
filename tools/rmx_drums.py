#!/usr/bin/env python3
"""Capture factory drum diagnostics; repeatability is not candidate sound fidelity."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import IDENTITY, new_directory, run
from tools.rmx_filter_match import screen

DRUMS = dict(kick='KickButton',snare='SnareButton',clap='ClapButton',hat='HihatButton')
FRAMES = 480000


def require(value,message):
    if not value: raise ValueError(message)


def recipe():
    cases = []
    for drum in DRUMS:
        for variant,block,shift in [('base',128,0),('repeat',128,0),('block32',32,0),('block256',256,0),('phase37',128,37),('retrigger',128,0)]:
            hits = [48000,48097,48193,48289,96013,96097] if variant == 'retrigger' else [48000+shift,192000+shift,336000+shift]
            cases.append(dict(name=f'drum-{drum}-{variant}',drum=drum,variant=variant,block=block,hits=hits,level=128,pitch=128))
    return cases


def parameters(c):
    values = dict(OutputVolume=0,AutoButton=0,QuantizeButton=0,InputButton=1,XpadButton=0,
                  DefaultSwitch=1,UserSwitch=0,ReleaseLever=0,XpadLevelVolume=c['level']/255,PitchVolume=c['pitch']/255)
    for name in ('IsolatorButton','CutAddButton','TransRollButton','GateDriveButton','RollButton','OverDubButton','HoldButton',
                 'BankShiftButton','XpadTouch','MuteButton','DeleteButton','BpfEchoButton','EchoButton','NoiseButton',
                 'SpiralUpButton','ReverbUpButton','HpfEchoButton','LpfEchoButton','CrushEchoButton','SpiralDownButto','ReverbDownButto',*DRUMS.values()):
        values[name] = 0
    return values


def plan_for(c,inventory):
    def setting(name,value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        require(len(matches) == 1,'Missing/ambiguous original parameter: '+name)
        return {k:matches[0][k] for k in ('index','id','name')} | dict(value=value)
    events = [setting(DRUMS[c['drum']],value) | dict(frame=frame+offset,type='parameter')
              for frame in c['hits'] for offset,value in [(0,1),(32,0)]]
    return dict(schema_version=1,kind='audio-plugin-capture-plan',role='reference',expected_plugin=IDENTITY,
                sample_rate=48000,bpm=120,tail_seconds=0,parameters=[setting(k,v) for k,v in parameters(c).items()],events=events)


def capture(args):
    root = new_directory(args.session); binding = sha256(Path(__file__))
    inventory = json.loads(run([args.host,'inventory',args.plugin]))
    require(all(inventory[k] == v for k,v in IDENTITY.items()),'Requires original RMX-1000 Plug-in 2.2.0')
    save_json(root/'inventory.json',inventory); source = root/'silence.wav'; write_wav(source,48000,np.zeros(FRAMES*2))
    cases = recipe()
    for c in cases:
        plan = root/(c['name']+'.json'); save_json(plan,plan_for(c,inventory))
        run([args.host,'render',args.plugin,source,plan,root/c['name'],c['block']])
        c['receipt_sha256'] = sha256(root/c['name']/'receipt.json'); print('Captured',c['name'],flush=True)
    require(sha256(Path(__file__)) == binding,'Drum recipe changed during capture')
    save_json(root/'matrix.json',dict(kind='rmx220-drum-discovery-captures',cases=cases,script_sha256=binding,
              scope='Original factory Default diagnostics at 48k/120BPM. No candidate or drum sound-match claim.'))
    return 0


def checked(directory,c,*,cold_kick=False):
    # The original ignores a kick press before its first processing callback.
    # This measured control hypothesis must be explicitly selected by the caller;
    # the original discovery/first-prediction contract remains strict by default.
    require(not cold_kick or c['drum']=='kick','Cold-control hypothesis is kick-only')
    inventory = json.loads((directory/'inventory.json').read_text()); folder = directory/c['name']; receipt_path = folder/'receipt.json'
    receipt = json.loads(receipt_path.read_text()); plan = plan_for(c,inventory)
    require(receipt['complete'] and receipt['role'] == 'reference' and all(receipt['plugin'][k] == v for k,v in IDENTITY.items()),'Wrong original capture')
    require(json.loads((folder/'plan.json').read_text()) == plan and receipt['maximum_block_size'] == c['block'],'Drum recipe differs')
    for path,field in [(folder/'audio.wav','output_sha256'),(folder/'plan.json','plan_sha256'),(Path(receipt['input_path']),'input_sha256'),
                       (folder/'state-before.bin','initial_state_sha256'),(folder/'state-after.bin','final_state_sha256'),
                       (folder/'parameter-log.json','parameter_log_sha256'),(folder/'inventory-after.json','final_inventory_sha256')]:
        require(sha256(path) == receipt[field],'Modified capture artifact')
    log = json.loads((folder/'parameter-log.json').read_text())['entries']; requested = [p | dict(frame=-1) for p in plan['parameters']] + plan['events']
    require(len(log) == len(requested),'Unexpected drum parameter log length'); final = parameters(c)
    for req,actual in zip(requested,log):
        expected = 0 if cold_kick and req['frame']==0 and req['name']=='KickButton' and req['value']==1 else req['value']
        require(all(actual[k] == req[k] for k in ('frame','name','index','id')) and np.float32(actual['requested_value']) == np.float32(req['value'])
                and abs(actual['immediate_readback']-float(np.float32(expected))) <= 1e-14,'Drum immediate readback differs')
        final[req['name']] = expected
    readbacks = {p['name']:p['value'] for p in json.loads((folder/'inventory-after.json').read_text())['parameters']}
    require(all(abs(readbacks[k]-float(np.float32(v))) <= 1e-14 for k,v in final.items()),'Drum final readback differs')
    rate,a = float_wav(folder/'audio.wav'); source_rate,x = float_wav(Path(receipt['input_path']))
    require(rate == source_rate == 48000 and a.shape == x.shape == (FRAMES,2) and not np.any(x),'Drum input/rate/extent differs')
    manifest = json.loads((directory/'matrix.json').read_text()); stored = next(row for row in manifest['cases'] if row['name'] == c['name'])
    require(stored == c | dict(receipt_sha256=sha256(receipt_path)),'Drum matrix differs')
    return a,dict(case=c['name'],receipt_sha256=sha256(receipt_path),output_sha256=receipt['output_sha256'],input_sha256=receipt['input_sha256'],plan_sha256=receipt['plan_sha256'])


def analyze(args):
    records = {c['name']:(c,*checked(args.session,c)) for c in recipe()}; rows = []
    for name,(c,a,provenance) in records.items():
        windows = []
        for i,at in enumerate(c['hits']):
            stop = min(FRAMES,at+120000,c['hits'][i+1] if i+1<len(c['hits']) else FRAMES)
            segment = a[at:stop]; nonzero = np.flatnonzero(np.any(np.abs(segment)>1e-12,axis=1))
            windows.append(dict(event_frame=at,first_output_delta=int(nonzero[0]) if len(nonzero) else None,
                                last_output_delta=int(nonzero[-1]) if len(nonzero) else None,
                                peak=float(np.max(np.abs(segment))),rms=float(np.sqrt(np.mean(segment.astype(float)**2)))))
        base_c,base,_ = records[f'drum-{c["drum"]}-base']; length=120000
        if c['variant'] != 'retrigger':
            first = a[c['hits'][0]+32:c['hits'][0]+32+length]; original = base[base_c['hits'][0]+32:base_c['hits'][0]+32+length]
            paired = [a[at+32:at+32+length] for at in c['hits']]
            details = dict(first_hit_vs_base=screen(original.astype(float),first.astype(float)),
                           first_hit_vs_base_bit_exact=bool(np.array_equal(original.view(np.uint32),first.view(np.uint32))),
                           repeated_hits_bit_exact=all(np.array_equal(first.view(np.uint32),p.view(np.uint32)) for p in paired))
        else: details = {}
        rows.append(provenance | dict(drum=c['drum'],variant=c['variant'],callback=c['block'],windows=windows,
                                      channels_bit_exact=bool(np.array_equal(a[:,0].view(np.uint32),a[:,1].view(np.uint32))),**details))
    save_json(args.report,dict(kind='rmx220-drum-original-characterization',capture_verification_passed=True,
              script_sha256=sha256(Path(__file__)),cases=rows,scope='Repeatability, declared-event timing and callback diagnostics only. No candidate fit, gain fit, alignment search or sound-match claim.'))
    print('Verified and characterized',len(rows),'factory drum captures')
    return 0


def compare(args):
    root = new_directory(args.output)
    names = ['tools/rmx_drums.py','tools/drum_probe.cpp','src/core/Engine.cpp','include/rmx/Engine.h',
             'include/rmx/FactoryDrums.h','include/rmx/SampleReader.h','include/rmx/Sample.h','include/rmx/Dsp.h',
             'include/rmx/Parameters.h','CMakeLists.txt']
    binding = {name:sha256(Path(name)) for name in names}; binary = sha256(args.renderer); rows = []
    for c in recipe():
        raw_a,provenance = checked(args.session,c); plan = root/(c['name']+'.tsv')
        plan.write_text('RMX_DRUM 1\n'+f'{list(DRUMS).index(c["drum"])} {c["level"]} {c["pitch"]} {c["block"]}\n'+''.join(f'{at}\n' for at in c['hits']))
        output = root/(c['name']+'.wav'); dry_path = root/(c['name']+'-dry.wav')
        run([args.renderer,args.session/'silence.wav',output,plan,dry_path])
        rate,raw_b = float_wav(output); dry_rate,dry = float_wav(dry_path)
        require(rate == dry_rate == 48000 and raw_b.shape == raw_a.shape == dry.shape and not np.any(dry),'Candidate rate/extent/dry differs')
        # Fixed independently measured bypass convention: reference32/candidate0.
        a,b = raw_a[32:].astype(float),raw_b[:len(raw_a)-32].astype(float)
        row = provenance | dict(drum=c['drum'],variant=c['variant'],candidate_sha256=sha256(output),
                    dry_trace_sha256=sha256(dry_path),schedule_sha256=sha256(plan),whole=screen(a,b),windows=[])
        for at in c['hits']:
            for label,left,right in [('attack',at,at+256),('body',at,at+48000),('decay',at+4800,at+120000)]:
                right = min(len(a),right)
                if right > left: row['windows'].append(dict(kind=label,frame=at,start=left,stop=right,score=screen(a[left:right],b[left:right])))
        row['passed'] = row['whole']['passed'] and all(w['score']['passed'] for w in row['windows'])
        rows.append(row); print('PASS' if row['passed'] else 'FAIL',c['name'],flush=True)
    require(binding == {name:sha256(Path(name)) for name in names} and binary == sha256(args.renderer),'Candidate changed during comparison')
    save_json(root/'comparison.json',dict(kind='rmx220-drum-existing-synthesis-baseline',passed=all(r['passed'] for r in rows),
              renderer_sha256=binary,source_sha256=binding,cases=rows,
              acceptance=dict(relative_rms_error_limit=.01,reference_channel_energy_floor=1e-20,silent_channel_absolute_rms_limit=1e-8,
                              reference_offset_frames=32,candidate_offset_frames=0,gain_fit=False,alignment_search=False),
              scope='First development comparison of existing Engine drum synthesis, not a fresh candidate holdout. Whole and declared attack/body/decay windows each require 1% per channel. No perceived-similarity percentage.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest='command',required=True)
    q=commands.add_parser('capture')
    for name in ('host','plugin','session'):q.add_argument('--'+name,type=Path,required=True)
    q=commands.add_parser('analyze');q.add_argument('--session',type=Path,required=True);q.add_argument('--report',type=Path,required=True)
    q=commands.add_parser('compare')
    for name in ('session','renderer','output'):q.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();raise SystemExit(globals()[args.command](args))


if __name__ == '__main__':main()
