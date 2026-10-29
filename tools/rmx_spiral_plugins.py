#!/usr/bin/env python3
"""Replay qualified live Spiral programs through an explicit AU/VST3 bundle."""
import argparse,concurrent.futures,gzip,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
import numpy as np
from tools import rmx_spiral_motion_match as motion
from tools import rmx_spiral_static_match as static
from tools.rmx_spiral_prospective import score
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory,run
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools import wav_delta

DELIVERY=dict(relative_rms_limit=1e-5,absolute_peak_limit=1e-5,reported_latency_frames=32)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['host','reference-host','plugin','native-report','native-renderer','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--static',action='store_true');p.add_argument('--session',type=Path);p.add_argument('--original-root',type=Path);p.add_argument('--workers',type=int,default=2)
    a=p.parse_args();require(1<=a.workers<=4,'Invalid worker count');root=new_directory(a.output)
    bound=motion.bindings();own=sha256(Path(__file__));codec_source=sha256(Path('tools/wav_delta.py'));plugin_source=sha256(Path('src/plugin/Plugin.cpp'));native=json.loads(a.native_report.read_text());native_hash=sha256(a.native_report)
    require(native['passed'] and native.get('live_engine',False),'Native Engine qualification is missing')
    require(all(native['source_sha256'].get(k)==v for k,v in bound.items()),'Native source differs')
    native_binary=sha256(a.native_renderer)
    require(native_binary in native.get('binaries_sha256',{}).values() or native_binary==native.get('renderer_sha256'),'Native renderer differs')
    require('rmx::Engine::process(' in subprocess.check_output(['nm','-C',str(a.native_renderer)],text=True),'Native renderer does not use the live Engine')
    inventory=json.loads(run([a.host,'inventory',a.plugin]));save_json(root/'inventory.json',inventory)
    identity={k:inventory[k] for k in ['name','manufacturer','version']};require(identity==dict(name='RMX',manufacturer='Axel McKenna',version='0.1.0'),'Wrong project bundle')
    def setting(name,value):
        matches=[x for x in inventory['parameters'] if x['name']==name]
        if name=='Bypass':matches=[x for x in matches if x['id']=='773352680']
        require(len(matches)==1,'Missing/ambiguous wrapper control '+name)
        return {k:matches[0][k] for k in ['name','id','index']}|dict(value=value)
    if a.static:
        require(a.original_root is not None,'Static originals root is required');cases=list(enumerate(native['cases']))
    else:
        require(a.session is not None,'Motion session is required');frozen=json.loads((a.session/'prediction.json').read_text())
        expected=native.get('prediction_sha256',native.get('previous_prediction_sha256'));require(expected==sha256(a.session/'prediction.json'),'Native program binding differs')
        require([r['case'] for r in native['cases']]==[c['name'] for c in frozen['cases']],'Native coverage differs');cases=list(enumerate(frozen['cases']))
    def one(item):
        index,c=item;old=native['cases'][index]
        if a.static:
            folder=a.original_root/c['session']/c['case'];receipt,original_plan,controls,direction,x=static.original(folder,a.reference_host)
            source=Path(receipt['input_path']);_,input_audio=float_wav(source);clock=np.zeros_like(x);clock[:min(len(x),len(input_audio))]=input_audio[:len(x)]
            c=dict(name=c['case'],direction=direction,main=round(controls['SceneVolume']*255),time=round(controls['Sub1Volume']*255),pitch=round(controls['Sub2Volume']*255),block=receipt['maximum_block_size'],changes=[])
            tail=original_plan['tail_seconds'];native_wav=a.native_report.parent/f'{index:04d}-candidate.wav.gz';native_digest=old['candidate_wav_sha256']
        else:
            source=a.session/(c['source']+'.wav');_,clock=float_wav(source);receipt,x,_=motion.original(argparse.Namespace(session=a.session,host=a.reference_host),c,clock)
            tail=0;native_wav=a.native_report.parent/(c['name']+'-native.wav');native_digest=old['candidate_sha256']
            if not native_wav.exists():native_wav=a.native_report.parent/(c['name']+'.wav')
        require(sha256((a.original_root/old['session']/old['case'] if a.static else a.session/c['name'])/'receipt.json')==old['receipt_sha256'],'Native Original receipt differs')
        values={'Auto BPM':0,'BPM':.4,'Quantize':0,'Scene FX':(8 if c['direction']=='down' else 3)/9,'Scene enabled':int(c.get('initial_enabled',True)),
            'Scene depth':c['main']/255,'Scene sub parameter 1':c['time']/255,'Scene sub parameter 2':c['pitch']/255,
            'Scene source':0,'Isolator source':0,'Isolator mode':0,'Isolate enabled':0,'Low':.5,'Mid':.5,'High':.5,
            'Release lever':0,'Default / User settings':0,'Sample source':0,'Bypass':0,'Send/return':0,'Input gain':2/3,'Output gain':2/3}
        names=dict(main='Scene depth',time='Scene sub parameter 1',pitch='Scene sub parameter 2',enabled='Scene enabled');events=[]
        for e in c['changes']:
            if e['control']=='direction':
                events += [setting('Scene FX',(8 if e['raw'] else 3)/9)|dict(frame=e['frame'],type='parameter'),setting('Scene enabled',1)|dict(frame=e['frame'],type='parameter')]
            else:events.append(setting(names[e['control']],e['raw'] if e['control']=='enabled' else e['raw']/255)|dict(frame=e['frame'],type='parameter'))
        plan=dict(schema_version=1,kind='audio-plugin-capture-plan',role='candidate',expected_plugin=identity,sample_rate=48000,bpm=120,tail_seconds=tail,post_render_message_pump_ms=100,parameters=[setting(k,v) for k,v in values.items()],events=events)
        destination=root/f'{index:04d}-{c["name"]}';destination.mkdir();plan_path=destination/'requested-plan.json';save_json(plan_path,plan)
        with tempfile.TemporaryDirectory(prefix='rmx-spiral-wrapper-') as tmp:
            folder=Path(tmp)/'render';run([a.host,'render',a.plugin,source,plan_path,folder,c['block']]);r=json.loads((folder/'receipt.json').read_text())
            require(r['complete'] and r['role']=='candidate' and r['frames']==len(x) and r['sample_rate']==48000 and r['maximum_block_size']==c['block'] and r['host_sha256']==sha256(a.host) and r['input_sha256']==receipt['input_sha256'] and r['plugin']['format']==inventory['format'],'Wrapper receipt differs')
            require(json.loads((folder/'plan.json').read_text())==plan and sha256(plan_path)==r['plan_sha256']==sha256(folder/'plan.json'),'Wrapper plan differs')
            for name,key in [('audio.wav','output_sha256'),('state-before.bin','initial_state_sha256'),('state-after.bin','final_state_sha256'),('parameter-log.json','parameter_log_sha256'),('inventory-after.json','final_inventory_sha256')]:require(sha256(folder/name)==r[key],'Wrapper artifact differs')
            for member in r['plugin']['binary_files']:require(sha256(a.plugin/member['path'])==member['sha256'],'Wrapper binary changed')
            requests=[v|dict(frame=-1) for v in plan['parameters']]+events;actual=json.loads((folder/'parameter-log.json').read_text())['entries'];require(len(requests)==len(actual),'Wrapper event count differs');final={}
            for request,event in zip(requests,actual,strict=True):
                require(all(request[k]==event[k] for k in ['name','id','index','frame']) and np.float32(request['value'])==np.float32(event['requested_value']) and abs(event['immediate_readback']-request['value'])<=1e-6,'Wrapper control delivery differs');final[request['name']]=request['value']
            after={q['name']:q['value'] for q in json.loads((folder/'inventory-after.json').read_text())['parameters']};require(all(abs(after[k]-v)<=1e-6 for k,v in final.items()),'Wrapper final readback differs')
            if native_wav.suffix=='.gz':
                require(sha256(native_wav)==old['lossless_candidate_sha256'],'Native lossless archive changed');plain=Path(tmp)/'native.wav'
                with gzip.open(native_wav,'rb') as z:plain.write_bytes(z.read())
            else:plain=native_wav
            require(sha256(plain)==native_digest,'Native audio changed');rate,y=float_wav(folder/'audio.wav');nr,n=float_wav(plain);require(rate==nr==48000 and y.shape==n.shape==x.shape,'Wrapper extent differs')
            error=y.astype(float)-n.astype(float);energy=float(np.sum(n.astype(float)**2));relative=float(np.linalg.norm(error)/np.sqrt(energy)) if energy>1e-20 else None;peak=float(np.max(np.abs(error)))
            delivery=peak<=DELIVERY['absolute_peak_limit'] and (relative is None or relative<=DELIVERY['relative_rms_limit']) and r['reported_latency_frames']==32
            dry=motion.transport(clock,c['block'],c['changes'])[32:];ref=x[32:];candidate=y[32:];windows=[]
            for w in old['windows']:
                s,t=w['start'],w['stop'];windows.append(dict(start=s,stop=t,kind=w['kind'],whole=score(ref[s:t],candidate[s:t]),wet=score(ref[s:t].astype(float)-dry[s:t],candidate[s:t].astype(float)-dry[s:t])))
            passed=all(w['whole']['passed'] and w['wet']['passed'] for w in windows)
            audio=wav_delta.pack((folder/'audio.wav').read_bytes(),plain.read_bytes(),destination,
                base_archive=native_wav if native_wav.suffix=='.gz' else None,cache=root.parent/'spiral-wrapper-native-base-cache')
            require(hashlib.sha256(wav_delta.unpack(audio)).hexdigest()==r['output_sha256'],'Archived wrapper WAV differs')
            for file in folder.iterdir():
                if file.is_file() and file.name!='audio.wav':shutil.copy2(file,destination/file.name);require(sha256(destination/file.name)==sha256(file),'Archived wrapper auxiliary differs')
            row=dict(case=c['name'],session=old.get('session',str(a.session)),passed=passed,delivery_passed=delivery,windows=windows,
                original_receipt_sha256=old['receipt_sha256'],wrapper_receipt_sha256=sha256(destination/'receipt.json'),wrapper_wav_sha256=r['output_sha256'],lossless_wrapper_metadata_sha256=sha256(audio),native_wav_sha256=native_digest,
                max_wrapper_native_difference=peak,relative_wrapper_native_error=relative,reported_latency=r['reported_latency_frames'])
        print('WRAPPER',inventory['format'],index,c['name'],passed and delivery,flush=True);return row
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:rows=list(pool.map(one,cases))
    require(bound==motion.bindings() and own==sha256(Path(__file__)) and codec_source==sha256(Path('tools/wav_delta.py')) and plugin_source==sha256(Path('src/plugin/Plugin.cpp')) and native_hash==sha256(a.native_report) and native_binary==sha256(a.native_renderer),'Wrapper inputs changed')
    save_json(root/'verification.json',dict(kind='spiral-live-wrapper-regression',passed=all(r['passed'] and r['delivery_passed'] for r in rows),format=inventory['format'],programs=len(rows),cases=rows,source_sha256=bound,verifier_sha256=own,codec_source_sha256=codec_source,plugin_source_sha256=plugin_source,native_report_sha256=native_hash,native_renderer_sha256=native_binary,host_sha256=sha256(a.host),delivery=DELIVERY,
        scope='Existing qualified Original programs through the explicit project AU/VST3 bundle. Whole/wet and every native window1%perchannel; separate1e-5 native delivery limits and latency32. Wrapper audio retained as its exact WAV container and lossless PCM XOR against the retained native base, with complete reconstructed WAV SHA256 verification; all auxiliary artifacts retained. Storage changes no sample, score or gate. No new Original capture, DAW/controller/hardware or whole-device qualification.'))
    return 0 if all(r['passed'] and r['delivery_passed'] for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
