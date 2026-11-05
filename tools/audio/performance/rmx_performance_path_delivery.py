#!/usr/bin/env python3
"""Bounded normalized-control/MIDI delivery; distinct from native strip evidence."""
import argparse,json,tempfile
from pathlib import Path
import numpy as np
from tools.audio.performance import rmx_performance_path as path
from tools.audio.noise.rmx_noise_stream import RenderSpace
from tools.audio.common.reference_audio import sha256,save_json,write_wav
from tools.audio.noise.noise_statistics import float_wav


def one_shots(c):
    changes=[e for e in c['changes'] if e['type'] not in 'TXFO']
    if c['family']=='release':changes += [dict(frame=400001,type='E',value=1)]
    return c|dict(name=c['name']+'-delivery',changes=sorted(changes,key=lambda e:e['frame']))


def plan_for(c,inv):
    def setting(name,value):
        matches=[p for p in inv['parameters'] if p['name']==name]
        if len(matches)!=1:raise ValueError('Ambiguous wrapper control: '+name)
        return {k:matches[0][k] for k in ['name','id','index']}|dict(value=value)
    travel=(c['pitch']-128)*(24/127 if c['pitch']>=128 else 24/128)
    values={'Auto BPM':c['automatic'],'Quantize':c['quantize'],'Scene FX':c['effect']/9,'Scene enabled':c['enabled'],'Scene source':c['route']/3,
        'Scene depth':c['main']/255,'Scene sub parameter 1':c['amount']/255,'Scene sub parameter 2':c['cutoff']/255,
        'Isolator mode':c['isolate_mode']/3,'Isolator source':c['route']/3,'Isolate enabled':c['isolate_enabled'],
        'Low':c['low']/255,'Mid':c['mid']/255,'High':c['high']/255,'Release FX':c['release_type']/2,'Release lever':0,
        'Sample source':0,'Default / User settings':0,'Sampler level':c['level']/255,'Sampler pitch travel':(travel+24)/48,
        'Sampler mute':0,'Roll hold':0,'Overdub':0,'Input gain':2/3,'Output gain':2/3}
    raw={'V':'Scene depth','B':'Scene sub parameter 1','C':'Scene sub parameter 2','U':'Low','W':'Mid','Y':'High','e':'Release lever'};events=[]
    for e in c['changes']:
        kind=e['type'];value=e['value'];at=e['frame'];pairs=[]
        if kind in ['H','R']:events.append(dict(frame=at,type='midi',bytes=[0x90 if kind=='H' else 0x80,36+value,127 if kind=='H' else 0]))
        elif kind=='Z':events.append({k:v for k,v in e.items() if k!='value'}|dict(type='transport'))
        elif kind in raw:pairs=[(raw[kind],value/255)]
        elif kind=='E':pairs=[('Scene enabled',value)]
        elif kind=='I':pairs=[('Isolate enabled',value)]
        elif kind=='N':pairs=[('Scene FX',value/9),('Scene enabled',1)]
        elif kind=='J':pairs=[('Isolator mode',value/3),('Isolate enabled',1)]
        elif kind=='G':pairs=[('Release FX',value/2)]
        elif kind=='S':pairs=[('Scene source',value/3),('Isolator source',value/3)]
        elif kind=='K':pairs=[('Isolator source',value/3)]
        else:raise ValueError('Unsupported delivery event: '+kind)
        events += [setting(k,v)|dict(frame=at,type='parameter') for k,v in pairs]
    return dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin={k:inv[k] for k in ['name','manufacturer','version']},sample_rate=48000,bpm=c['bpm'],tail_seconds=0,post_render_message_pump_ms=100,parameters=[setting(k,v) for k,v in values.items()],events=events)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['renderer','host','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--plugin',type=Path,action='append',required=True);p.add_argument('--case',action='append');a=p.parse_args()
    if a.output.exists():raise ValueError('Choose new report')
    bound=path.bindings()|{'tools/audio/performance/rmx_performance_path_delivery.py':sha256(Path(__file__)),'src/plugin/Plugin.cpp':sha256(Path('src/plugin/Plugin.cpp'))};binary={k:sha256(getattr(a,k)) for k in ['renderer','host']};rows=[];peak=0
    cases=path.recipe('fresh')
    if a.case:cases=[c for c in cases if c['name'] in a.case]
    for plugin in a.plugin:
        with tempfile.TemporaryDirectory(prefix='rmx-path-delivery-',dir='/private/tmp') as directory:
            root=Path(directory);space=RenderSpace(root);inv=json.loads(space.run([a.host,'inventory',plugin]))
            if any(inv[k]!=v for k,v in dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0').items()):raise ValueError('Wrong project bundle')
            for original in cases:
                c=one_shots(original);write_wav(root/'input.wav',48000,path.stimulus(c).reshape(-1));program=root/'program.tsv';program.write_text(path.schedule(c));wave=root/'native.wav';dry=root/'dry.wav';space.run([a.renderer,root/'input.wav',wave,program,dry]);native_hash=sha256(wave);rate,x=float_wav(wave);wave.unlink();dry.unlink();plan=plan_for(c,inv);save_json(root/'plan.json',plan);space.run([a.host,'render',plugin,root/'input.wav',root/'plan.json',root/'wrapper',c['block']]);folder=root/'wrapper';receipt=json.loads((folder/'receipt.json').read_text())
                if not receipt['complete'] or receipt['host_sha256']!=binary['host'] or receipt['role']!='candidate' or receipt['frames']!=path.FRAMES or receipt['sample_rate']!=48000 or receipt['maximum_block_size']!=c['block'] or receipt['input_sha256']!=sha256(root/'input.wav') or json.loads((folder/'plan.json').read_text())!=plan:raise ValueError('Wrapper receipt/plan differs')
                if inv['format']=='AudioUnit' and receipt.get('audio_unit_offline_property_verified') is not True:raise ValueError('Actual AU offline property was not verified')
                for n,k in [('audio.wav','output_sha256'),('plan.json','plan_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:
                    if sha256(folder/n)!=receipt[k]:raise ValueError('Wrapper auxiliary changed')
                for member in receipt['plugin']['binary_files']:
                    if sha256(plugin/member['path'])!=member['sha256']:raise ValueError('Wrapper binary changed')
                requests=[v|dict(frame=-1) for v in plan['parameters']]+[e for e in plan['events'] if e['type']=='parameter'];log=json.loads((folder/'parameter-log.json').read_text())['entries']
                if len(requests)!=len(log):raise ValueError('Wrapper log extent differs')
                for req,actual in zip(requests,log,strict=True):
                    if any(req[k]!=actual[k] for k in ['name','id','index','frame']) or np.float32(req['value'])!=np.float32(actual['requested_value']) or abs(actual['immediate_readback']-req['value'])>1e-6:raise ValueError('Wrapper parameter delivery differs')
                transport=[e for e in plan['events'] if e['type']=='transport']
                if transport and (not receipt.get('explicit_transport') or sha256(folder/'transport-log.json')!=receipt['transport_log_sha256'] or json.loads((folder/'transport-log.json').read_text())!=dict(kind='explicit-transport-event-log',entries=transport)):raise ValueError('Wrapper transport delivery differs')
                rate,y=float_wav(folder/'audio.wav')
                if rate!=48000 or x.shape!=y.shape or x.shape!=(path.FRAMES,2):raise ValueError('Wrapper audio extent differs')
                delta=y.astype(float)-x;maximum=float(np.max(np.abs(delta)));relative=float(np.linalg.norm(delta)/np.linalg.norm(x.astype(float)));passed=maximum<=1e-5 and relative<=1e-5 and receipt['reported_latency_frames']==32
                different=np.flatnonzero(np.any(x.view(np.uint32)!=y.view(np.uint32),axis=1))
                rows.append(dict(case=c,format=inv['format'],passed=passed,max_absolute_error=maximum,relative_rms_error=relative,native_sha256=native_hash,wrapper_sha256=receipt['output_sha256'],latency_frames=receipt['reported_latency_frames'],receipt_sha256=sha256(folder/'receipt.json'),plan_sha256=receipt['plan_sha256'],plugin_binary_files=receipt['plugin']['binary_files'],first_different_frame=int(different[0]) if len(different) else None,last_different_frame=int(different[-1]) if len(different) else None,maximum_error_frame=int(np.argmax(np.max(np.abs(delta),axis=1))),per_second_max_absolute_error=[float(np.max(np.abs(delta[i:i+48000]))) for i in range(0,path.FRAMES,48000)]));print('DELIVERY',inv['format'],c['name'],passed,maximum,relative,flush=True)
                import shutil
                shutil.rmtree(folder);(root/'plan.json').unlink();(root/'input.wav').unlink();peak=max(peak,space.peak)
        if root.exists():raise ValueError('Audio retained')
    if bound!=path.bindings()|{'tools/audio/performance/rmx_performance_path_delivery.py':sha256(Path(__file__)),'src/plugin/Plugin.cpp':sha256(Path('src/plugin/Plugin.cpp'))} or any(sha256(getattr(a,k))!=v for k,v in binary.items()):raise ValueError('Delivery inputs changed')
    save_json(a.output,dict(kind='bounded-performance-path-wrapper-delivery',verification_passed=True,passed=all(c['passed'] for c in rows),cases=rows,source_sha256=bound,binary_sha256=binary,peak_temporary_bytes=peak,raw_audio_retained=False,all_temporary_directories_removed=True,scope='Ten-second normalized Scene/Isolator/Release/routing/tempo automation plus MIDI one-shots. Roll/touch/record commands are removed and native output is regenerated for this declared delivery recipe. Separate1e-5 delivery gates; no new Original fidelity or strip/controller qualification.'))


if __name__=='__main__':main()
