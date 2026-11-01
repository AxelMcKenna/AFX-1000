#!/usr/bin/env python3
"""Reproduce bounded read-only Original control observations with artifact identity guards."""
import argparse,json,tempfile
from pathlib import Path
import numpy as np
from tools import rmx_performance_path as path
from tools.rmx_noise_stream import RenderSpace
from tools.reference_audio import sha256,save_json,write_wav


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=['selector','pattern','performance-selector'],required=True)
    for k in ['host','plugin','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--expected-output-sha256');p.add_argument('--effect-index',type=int,choices=range(9),default=0)
    p.add_argument('--family',choices=['switch','tempo'],default='switch');p.add_argument('--stage',choices=['fresh','fresh2','fresh3'],default='fresh');a=p.parse_args()
    if a.output.exists():raise ValueError('Choose a new report')
    pattern=a.mode=='pattern';performance=a.mode=='performance-selector';observer=Path('research/audio/experiments')/('pattern_clock_observer.py' if pattern else 'scene_selector_observer.py' if performance else 'scene_motion_observer.py');observer=observer.resolve()
    c=path.control_case(next(c for c in path.recipe('fresh') if c['name']=='path-fresh-tempo-03')) if pattern else path.recipe('discovery')[0]|dict(effect=0,main=95,changes=[dict(frame=4096,type='N',value=1),dict(frame=8192,type='N',value=0)],block=128)
    if performance:c=[c for c in path.recipe(a.stage) if c['family']==a.family][a.effect_index]
    frames=path.FRAMES if pattern or performance else 32768
    bound={str(q):sha256(q) for q in [a.host,observer,Path(__file__)]}
    with tempfile.TemporaryDirectory(prefix='rmx-path-observe-',dir='/private/tmp') as directory:
        root=Path(directory);space=RenderSpace(root);write_wav(root/'input.wav',48000,np.zeros(frames*2));inventory=json.loads(space.run([a.host,'inventory',a.plugin]));plan=path.plan_for(c,inventory);save_json(root/'plan.json',plan)
        space.run([a.host,'render',a.plugin,root/'input.wav',root/'plan.json',root/'ordinary',c['block']])
        receipt=json.loads((root/'ordinary/receipt.json').read_text())
        if not receipt['complete'] or receipt['frames']!=frames or receipt['host_sha256']!=bound[str(a.host)]:raise ValueError('Incomplete ordinary observation baseline')
        if a.expected_output_sha256 and receipt['output_sha256']!=a.expected_output_sha256:raise ValueError('Ordinary audio differs from pinned prior capture')
        names=['audio.wav','plan.json','state-before.bin','state-after.bin','parameter-log.json','inventory-after.json']+(['transport-log.json'] if any(e['type']=='transport' for e in plan['events']) else [])
        hashes={n:sha256(root/'ordinary'/n) for n in names};(root/'ordinary/audio.wav').unlink()
        args=['render',str(a.plugin.resolve()),str(root/'input.wav'),str(root/'plan.json'),str(root/'observed'),str(c['block']),'600']
        commands=root/'observe.lldb';commands.write_text('target create '+json.dumps(str(a.host.resolve()))+'\nsettings set target.run-args '+' '.join(map(json.dumps,args))+'\ncommand script import '+json.dumps(str(observer))+'\nrun\nquit\n')
        variable='RMX_PATTERN_CLOCK_TRACE' if pattern else 'RMX_SCENE_SELECTOR_TRACE' if performance else 'RMX_SCENE_MOTION_TRACE'
        env=[variable+'='+str(root/'trace.jsonl')]
        if performance:
            blocks=set(range(16))
            for e in c['changes']:
                if e['type'] in 'NEZ':
                    at=e['frame']//32;blocks.update(range(max(0,at-4),min(15000,at+60)));blocks.update(b for b in [at+128,at+256,at+512] if b<15000)
            save_json(root/'blocks.json',sorted(blocks));env += ['RMX_SCENE_SELECTOR_BLOCKS='+str(root/'blocks.json')]
        space.run(['env',*env,'lldb','--batch','-s',commands])
        observed=json.loads((root/'observed/receipt.json').read_text())
        if not observed['complete'] or any(sha256(root/'observed'/n)!=v for n,v in hashes.items()):raise ValueError('Observer changed complete capture artifacts')
        trace=[json.loads(line) for line in (root/'trace.jsonl').read_text().splitlines()]
        if (pattern and (not trace or not any(r['slot_changes'] for r in trace))) or (performance and [r['block'] for r in trace]!=sorted(blocks)) or (not pattern and not performance and len(trace)!=320):raise ValueError('Missing bounded control observations')
        record=dict(kind='read-only-performance-control-observation',verification_passed=True,mode=a.mode,case=c,frames=frames,plan=plan,trace=trace,ordinary_and_observed_sha256=hashes,source_and_host_sha256=bound,peak_temporary_bytes=space.peak,raw_audio_retained=False)
    if any(sha256(Path(k))!=v for k,v in bound.items()):raise ValueError('Observation inputs changed')
    record['all_temporary_directories_removed']=not root.exists();save_json(a.output,record)


if __name__=='__main__':main()
