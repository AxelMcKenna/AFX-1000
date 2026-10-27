#!/usr/bin/env python3
"""Check other/fallback Scene and accepted Down outputs after live Up integration."""
import argparse
import json
from pathlib import Path

import numpy as np

from tools.reference_audio import save_json, sha256, write_wav
from tools.rmx_factory_match import new_directory, run
from tools.rmx_reverb_motion import checked, recipe
from tools.rmx_reverb_up_engine import require


def legacy(args):
    root = new_directory(args.output); rows = []
    cases = [(f'scene-{scene}',48000,scene,{}) for scene in range(10) if scene != 4]
    cases += [(f'up-{key}-{value}',48000,4,{key:value,'user_settings':1}) for key,value in
              [('reverb_up_room_size',1),('reverb_up_time',0),('reverb_up_time',2),('reverb_up_filter',0),('reverb_up_filter',1),('reverb_decay',.5)]]
    cases += [('down-room-small',48000,9,dict(user_settings=1,reverb_down_room_size=1))]
    cases += [(f'scene-{scene}-rate-{rate}',rate,scene,{}) for rate in (44100,96000) for scene in (4,9)]
    for name,rate,scene,settings in cases:
        source = root/(f'input-{rate}.wav')
        if not source.exists():
            t = np.arange(rate*2)/rate
            x = np.random.default_rng(0xE06132).normal(0,.011,(len(t),2))
            x += .009*np.column_stack((np.sin(2*np.pi*(331*t+29*t*t)),np.cos(2*np.pi*1747*t)))
            x[rate//2:rate] = 0; write_wav(source,rate,x.ravel())
        values = dict(auto_tempo=0,isolate_on=1,low=.19,mid=-.27,high=.13,scene_on=1,
                      scene_type=scene,scene_depth=.72,scene_time=137*7/255,scene_resonance=.27) | settings
        preset = root/(name+'.rmx'); preset.write_text('RMX_STATE 1\n'+''.join(f'param {k} {v}\n' for k,v in values.items()))
        before = root/(name+'-before.wav'); after = root/(name+'-after.wav')
        run([args.before,source,before,preset,'6']); run([args.after,source,after,preset,'6'])
        equal = sha256(before) == sha256(after)
        rows.append(dict(case=name,sample_rate=rate,settings=values,input_sha256=sha256(source),preset_sha256=sha256(preset),
                         before_sha256=sha256(before),after_sha256=sha256(after),byte_identical=equal))
        print('PASS' if equal else 'FAIL',name,flush=True)
    save_json(root/'verification.json',dict(kind='rmx220-reverb-up-engine-other-scene-check',passed=all(r['byte_identical'] for r in rows),
              script_sha256=sha256(Path(__file__)),before_renderer_sha256=sha256(args.before),after_renderer_sha256=sha256(args.after),cases=rows,
              scope='Preserved pre-integration renderer versus current Engine. Other Scenes, measured Down and unsupported Up profiles/rates; no claim that the fallback matches the original RMX.'))
    return 0 if all(r['byte_identical'] for r in rows) else 1


def down(args):
    root = new_directory(args.output); audit = json.loads(args.audit.read_text()); records = []; rows = []
    require(audit['passed'] and set(audit['comparisons_sha256']) == {sha256(p) for p in args.previous},'Previous Down audit binding differs')
    for p in args.previous:
        report = json.loads(p.read_text()); require(report['passed'] and report['backend'] == 'engine','Previous Down Engine not accepted')
        records += [(p.parent,r) for r in report['cases']]
    require(len(records) == len({(r['stage'],r['case']) for _,r in records}) == 192,'Wrong previous Down coverage')
    recipes = {}
    for parent,row in records:
        stage = row['stage']
        if stage not in recipes:
            waves,cases = recipe(stage); recipes[stage] = waves,{c['name']:c for c in cases}
        waves,cases = recipes[stage]; c = cases[row['case']]
        receipts = [p for p in args.capture_root.glob('rmx-reverb*/'+c['name']+'/receipt.json') if sha256(p) == row['receipt_sha256']]
        require(len(receipts) == 1,'Missing/ambiguous original Down receipt')
        receipt_path = receipts[0]; receipt = json.loads(receipt_path.read_text())
        _,_,provenance = checked(receipt_path.parent.parent,c,waves[c['source']])
        require(all(row[k] == v for k,v in provenance.items()),'Down original provenance differs')
        prefix = stage+'-'+c['name']; plan = parent/(prefix+'.tsv'); old_audio = parent/(prefix+'.wav'); old_dry = parent/(prefix+'-dry.wav')
        require(sha256(plan) == row['schedule_sha256'] and sha256(old_audio) == row['candidate_sha256']
                and sha256(old_dry) == row['dry_trace_sha256'],'Accepted Down candidate files changed')
        output = root/(prefix+'.wav'); dry = root/(prefix+'-dry.wav')
        run([args.renderer,receipt['input_path'],output,plan,'faded','post','read','32',dry,'output','0','startup','0'])
        equal = sha256(output) == row['candidate_sha256'] and sha256(dry) == row['dry_trace_sha256']
        rows.append(provenance | dict(stage=stage,output_sha256=sha256(output),dry_trace_sha256=sha256(dry),audio_and_dry_byte_identical=equal))
        print('PASS' if equal else 'FAIL',stage,c['name'],flush=True)
    save_json(root/'verification.json',dict(kind='rmx220-reverb-up-engine-down-preservation',passed=all(r['audio_and_dry_byte_identical'] for r in rows),
              script_sha256=sha256(Path(__file__)),renderer_sha256=sha256(args.renderer),previous_audit_sha256=sha256(args.audit),
              previous_comparisons_sha256=[sha256(p) for p in args.previous],cases=rows,
              scope='192 prior measured Down Engine outputs and diagnostic dry traces retain exact byte identity; these are regressions, not new original captures.'))
    return 0 if all(r['audio_and_dry_byte_identical'] for r in rows) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command',required=True)
    q = commands.add_parser('legacy')
    for name in ('before','after','output'): q.add_argument('--'+name,type=Path,required=True)
    q = commands.add_parser('down')
    for name in ('renderer','audit','capture-root','output'): q.add_argument('--'+name,type=Path,required=True)
    q.add_argument('--previous',type=Path,action='append',required=True)
    args = parser.parse_args(); raise SystemExit(globals()[args.command](args))


if __name__ == '__main__':
    main()
