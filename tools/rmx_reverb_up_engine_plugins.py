#!/usr/bin/env python3
"""Regress AU/VST3 Up audio, latency and parameter delivery against the Engine fixtures."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json, sha256
from tools.rmx_factory_match import new_directory, run
from tools.rmx_filter_match import screen
from tools.rmx_reverb_up_engine import recipe, require
from tools.rmx_reverb_up_motion import checked
from tools.rmx_reverb_up_motion_audit import ACCEPTANCE


def check(args):
    root = new_directory(args.output); inventory = json.loads(run([args.host,'inventory',args.plugin]))
    save_json(root/'inventory.json',inventory)
    identity = {k:inventory[k] for k in ('name','manufacturer','version')}
    require(identity == dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'), 'Wrong candidate wrapper')
    engine = json.loads(args.engine_comparison.read_text()); require(engine['passed'] and engine['acceptance'] == ACCEPTANCE,'Engine evidence differs')
    rows = []; waves,cases = recipe(); engine_rows = {r['case']:r for r in engine['cases']}
    def setting(name,value):
        matches = [p for p in inventory['parameters'] if p['name'] == name]
        require(len(matches) == 1,'Missing or ambiguous wrapper parameter: '+name)
        return {k:matches[0][k] for k in ('index','id','name')} | dict(value=value)
    names = dict(main='Scene depth',amount='Scene sub parameter 1',cutoff='Scene sub parameter 2',enabled='Scene enabled')
    for c in cases:
        receipt,raw_a,x,provenance = checked(args.session,c,waves[c['source']]); old = engine_rows[c['name']]
        require(all(old[k] == v for k,v in provenance.items()),'Engine/reference recipe differs')
        values = {'Auto BPM':0,'BPM':.4,'Scene FX':4/9,'Scene source':0,'Scene enabled':c['enabled'],
                  'Scene depth':c['main']/255,'Scene sub parameter 1':c['amount']/255,'Scene sub parameter 2':c['cutoff']/255}
        plan = dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,
                    sample_rate=48000,bpm=120,tail_seconds=c['tail'],post_render_message_pump_ms=100,
                    parameters=[setting(k,v) for k,v in values.items()],
                    events=[setting(names[e['control']],e['value'] if e['control']=='enabled' else e['value']/255) |
                            dict(frame=e['frame'],type='parameter') for e in c['events']])
        path = root/(c['name']+'.json'); save_json(path,plan); folder = root/c['name']
        run([args.host,'render',args.plugin,receipt['input_path'],path,folder,c['block']])
        delivered = json.loads((folder/'receipt.json').read_text())
        require(delivered['complete'] and delivered['role'] == 'candidate' and delivered['plan_sha256'] == sha256(folder/'plan.json') == sha256(path)
                and delivered['input_sha256'] == receipt['input_sha256'],'Wrapper receipt differs')
        for name,field in [('audio.wav','output_sha256'),('parameter-log.json','parameter_log_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('inventory-after.json','final_inventory_sha256')]:
            require(sha256(folder/name) == delivered[field],'Wrapper artifact changed')
        requested = [p | dict(frame=-1) for p in plan['parameters']] + plan['events']
        log = json.loads((folder/'parameter-log.json').read_text())['entries']; require(len(log) == len(requested),'Wrapper parameter count differs')
        for requested,actual in zip(requested,log):
            require(all(actual[k] == requested[k] for k in ('frame','name','index','id'))
                    and np.float32(actual['requested_value']) == np.float32(requested['value'])
                    and abs(actual['immediate_readback']-requested['value']) <= 1e-6,'Wrapper parameter delivery differs')
        engine_path = args.engine_comparison.parent/(c['name']+'.wav'); dry_path = args.engine_comparison.parent/(c['name']+'-dry.wav')
        require(sha256(engine_path) == old['candidate_sha256'] and sha256(dry_path) == old['dry_trace_sha256'],'Engine output/dry changed')
        rate,raw_b = float_wav(folder/'audio.wav'); dry_rate,raw_d = float_wav(dry_path); _,raw_engine = float_wav(engine_path)
        require(rate == dry_rate == 48000 and raw_b.shape == raw_a.shape == raw_d.shape == raw_engine.shape,'Wrapper extent/rate differs')
        a,b,d = raw_a[32:],raw_b[32:].astype(float),raw_d[32:].astype(float); wa,wb = a-d,b-d
        row = provenance | dict(candidate_receipt_sha256=sha256(folder/'receipt.json'),candidate_audio_sha256=sha256(folder/'audio.wav'),
                  engine_audio_sha256=sha256(engine_path),predicted_dry_sha256=sha256(dry_path),reported_latency=delivered['reported_latency_frames'],
                  maximum_plugin_engine_absolute_difference=float(np.max(np.abs(raw_b.astype(float)-raw_engine))),
                  whole=screen(a,b),wet=screen(wa,wb),post_input_tail=screen(a[len(x):],b[len(x):]),event_windows=[],startup_windows=[])
        for group in ('event_windows','startup_windows'):
            for window in old[group]:
                at = window['frame']; left,right = max(0,at-64),min(len(a),at+4096)
                row[group].append(dict(frame=at,whole=screen(a[left:right],b[left:right]),wet=screen(wa[left:right],wb[left:right])))
        row['passed'] = row['reported_latency'] == 32 and all(row[k]['passed'] for k in ('whole','wet','post_input_tail')) and all(
            w[k]['passed'] for group in ('event_windows','startup_windows') for w in row[group] for k in ('whole','wet'))
        rows.append(row); print('PASS' if row['passed'] else 'FAIL',inventory['format'],c['name'],flush=True)
    save_json(root/'verification.json',dict(kind='rmx220-reverb-up-engine-wrapper-check',passed=all(r['passed'] for r in rows),
              format=inventory['format'],identity=identity,script_sha256=sha256(Path(__file__)),host_sha256=sha256(args.host),
              inventory_sha256=sha256(root/'inventory.json'),engine_comparison_sha256=sha256(args.engine_comparison),
              plugin_source_sha256=sha256(Path('src/plugin/Plugin.cpp')),acceptance=ACCEPTANCE,cases=rows,
              limitations=['Eight existing Engine fixtures are wrapper regressions, not eight further fresh original captures.',
                           'Predicted dry comes from the checked processor, not an independently captured wet stem.',
                           'Normalized wrapper parameters can introduce the disclosed small Engine differences.',
                           'Offline explicit-bundle checks are not commercial DAW, live hardware or MCU timing qualification.']))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host','plugin','engine-comparison','session','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(check(parser.parse_args()))


if __name__ == '__main__':
    main()
