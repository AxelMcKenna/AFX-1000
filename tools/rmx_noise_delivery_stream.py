#!/usr/bin/env python3
"""Check bounded AU/VST3 Noise delivery against the actual native Engine."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
from tools import rmx_noise_user as noise
from tools.rmx_noise_stream import RenderSpace
from tools.noise_statistics import float_wav
from tools.reference_audio import write_wav, save_json, sha256
from tools.rmx_drums import require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['host','renderer','noise-report','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--extra-noise-report',type=Path,action='append',default=[])
    p.add_argument('--input-stimulus',choices=['low','asymmetric','steps'],help='Use a declared synthetic input for delivery checks')
    p.add_argument('--all-cases',action='store_true',help='Check transport delivery even when Original fidelity remains inconclusive')
    p.add_argument('--plugin',type=Path,action='append',required=True);a=p.parse_args()
    require(not a.output.exists(),'Report already exists');source=sha256(Path('src/plugin/Plugin.cpp'));own=sha256(Path(__file__));report_hash=sha256(a.noise_report)
    extra_hashes={str(path):sha256(path) for path in a.extra_noise_report};qualified_cases={}
    for path in [a.noise_report]+a.extra_noise_report:
        qualified=json.loads(path.read_text());require(qualified['kind'] in ['rmx220-bounded-user-noise-statistical-validation','bounded-noise-motion-validation','bounded-noise-sidechain-audio-validation','bounded-noise-random-audio-validation','verified-reference-trajectory-random-noise-validation'],'Wrong native Noise report')
        for c in qualified['cases']:
            if c['passed'] or a.all_cases:qualified_cases[c['name']]=c
    cases=list(qualified_cases.values());require(cases,'Expected qualified Noise presets')
    cases=[noise.recipe()[0]]+cases;rows=[];peak=0;stimulus_source=None
    with tempfile.TemporaryDirectory(prefix='rmx-bounded-noise-delivery-',dir='/private/tmp') as directory:
        root=Path(directory);space=RenderSpace(root)
        if a.input_stimulus:
            from tools.rmx_noise_sidechain_controls import stimulus
            stimulus_source=sha256(Path('tools/rmx_noise_sidechain_controls.py'))
            input_samples=stimulus(a.input_stimulus).reshape(-1)
        else:input_samples=np.zeros(96000)
        write_wav(root/'silence.wav',48000,input_samples)
        input_hash=sha256(root/'silence.wav')
        for plugin in a.plugin:
            inv=json.loads(space.run([a.host,'inventory',plugin]));identity={k:inv[k] for k in ['name','manufacturer','version']}
            require(identity==dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'),'Wrong project plug-in')
            def setting(name,value):
                values=[p for p in inv['parameters'] if p['name']==name];require(len(values)==1,'Missing/ambiguous wrapper parameter: '+name)
                return {k:values[0][k] for k in ['name','id','index']}|dict(value=value)
            for old in cases:
                c=old|dict(frames=144000)
                with tempfile.TemporaryDirectory(prefix='case-',dir=root) as d:
                    case=Path(d);program=case/'native.tsv';schedule=noise.schedule(c)
                    if a.input_stimulus:
                        lines=schedule.splitlines()
                        if lines[0].endswith(' 1'):lines[1]+=' 0 0 0 0'
                        lines[0]='RMX_NOISE_USER 3';schedule='\n'.join(lines)+'\n'
                    program.write_text(schedule);wave=case/'native.wav'
                    space.run([a.renderer,root/'silence.wav',wave,program])
                    controls={'Auto BPM':0,'Quantize':0,'Scene FX':2/9,'Scene enabled':0,'Isolate enabled':0,'Release lever':0,
                        'Default / User settings':c['user'],'Scene source':0,'Scene depth':c['main']/255,
                        'Scene sub parameter 1':c['amount']/255,'Scene sub parameter 2':c.get('sub2',0)/255,
                        'Noise Sub2 mode':c.get('mode',0),'Noise modulation wave':c.get('wave',0)/4,
                        'Noise resonance character':c.get('resonance',0)/2,
                        'Noise filter width':c['width']/2,'Noise minimum level':c['minimum']/3,'Noise maximum level':c['maximum']/3,
                        'Input gain':2/3,'Output gain':2/3}
                    plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,
                        sample_rate=48000,bpm=120,tail_seconds=2,post_render_message_pump_ms=100,
                        parameters=[setting(k,v) for k,v in controls.items()],events=[setting('Scene enabled',1)|dict(frame=4800,type='parameter')])
                    path=case/'plan.json';save_json(path,plan);output=case/'wrapper'
                    space.run([a.host,'render',plugin,root/'silence.wav',path,output,c['block']]);receipt=json.loads((output/'receipt.json').read_text())
                    require(receipt['complete'] and receipt['role']=='candidate' and receipt['input_sha256']==sha256(root/'silence.wav') and receipt['frames']==144000 and receipt['sample_rate']==48000 and receipt['maximum_block_size']==c['block'],'Wrapper capture differs')
                    require(receipt['host_sha256']==sha256(a.host) and json.loads((output/'plan.json').read_text())==plan,'Wrapper host/plan differs')
                    for name,key in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(output/name)==receipt[key],'Wrapper auxiliary changed')
                    for member in receipt['plugin']['binary_files']:require(sha256(plugin/member['path'])==member['sha256'],'Wrapper binary changed')
                    requests=[v|dict(frame=-1) for v in plan['parameters']]+plan['events'];log=json.loads((output/'parameter-log.json').read_text())['entries'];require(len(log)==len(requests),'Wrapper parameter log extent differs')
                    for req,actual in zip(requests,log,strict=True):require(all(actual[k]==req[k] for k in ['name','id','index','frame']) and np.float32(actual['requested_value'])==np.float32(req['value']) and abs(actual['immediate_readback']-req['value'])<1e-6,'Wrapper parameter delivery differs')
                    rate,x=float_wav(wave);other_rate,y=float_wav(output/'audio.wav');require(rate==other_rate==48000 and x.shape==y.shape==(144000,2),'Wrapper audio extent differs')
                    delta=y.astype(float)-x;maximum=float(np.max(np.abs(delta)));relative=float(np.linalg.norm(delta)/np.linalg.norm(x.astype(float)))
                    passed=maximum<=1e-5 and relative<=1e-5 and receipt['reported_latency_frames']==32
                    rows.append(dict(format=inv['format'],case=c['name'],passed=passed,max_absolute_error=maximum,relative_rms_error=relative,
                        source_report_original_qualification=c.get('passed'),
                        reported_latency=receipt['reported_latency_frames'],native_sha256=sha256(wave),wrapper_sha256=receipt['output_sha256'],receipt=receipt,receipt_sha256=sha256(output/'receipt.json')))
                    peak=max(peak,space.peak);print('DELIVERY',inv['format'],c['name'],passed,maximum,relative,flush=True)
    require(not root.exists() and source==sha256(Path('src/plugin/Plugin.cpp')) and own==sha256(Path(__file__)) and report_hash==sha256(a.noise_report)
        and all(sha256(Path(path))==digest for path,digest in extra_hashes.items())
        and (stimulus_source is None or stimulus_source==sha256(Path('tools/rmx_noise_sidechain_controls.py'))),'Delivery inputs changed/audio retained')
    save_json(a.output,dict(kind='bounded-noise-project-wrapper-delivery',passed=all(r['passed'] for r in rows),cases=rows,
        native_noise_report_sha256=report_hash,additional_noise_reports_sha256=extra_hashes,all_declared_cases_requested=a.all_cases,input_stimulus=a.input_stimulus,input_sha256=input_hash,input_stimulus_source_sha256=stimulus_source,plugin_source_sha256=source,verifier_sha256=own,peak_temporary_bytes=peak,raw_audio_retained=False,
        scope=('Default and all declared presets' if a.all_cases else 'Default and all qualified presets')+' from the supplied Noise reports through explicit AU/VST3 bundles. Three-second full output vs actual native Engine; separate1e-5 delivery gates and latency32. Source-report Original qualification is retained separately from delivery. No new Original fidelity, DAW/controller or hardware claim.'))


if __name__=='__main__':main()
