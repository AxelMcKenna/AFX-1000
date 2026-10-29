#!/usr/bin/env python3
"""Replay every prior static Spiral program through the stateful processor."""
import argparse,concurrent.futures,gzip,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
from tools import rmx_spiral_static_match as static
from tools import rmx_spiral_motion_match as motion
from tools.rmx_spiral_prospective import score
from tools.rmx_factory_match import new_directory,run
from tools.rmx_drums import require
from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256,write_wav


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['original_root','host','renderer','sanitizer','output']:p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--comparison',type=Path,action='append',required=True);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--engine',action='store_true')
    p.add_argument('--reuse-lossless',type=Path)
    a=p.parse_args();require(1<=a.workers<=4,'Invalid worker count');root=new_directory(a.output)
    bound=motion.bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_spiral_static_motion_audit.py','tools/rmx_spiral_prospective.py']}
    binaries={str(b):sha256(b) for b in [a.renderer,a.sanitizer]};symbols=subprocess.check_output(['nm','-C',str(a.sanitizer)],text=True);require('___asan_init' in symbols and '___ubsan_handle_' in symbols,'Missing sanitizers')
    if a.engine:
        require('rmx::Engine::process(' in symbols and 'rmx::Engine::process(' in subprocess.check_output(['nm','-C',str(a.renderer)],text=True),'Replay is not the live Engine')
    previous={};report_hashes={str(f):sha256(f) for f in a.comparison}
    reuse={};reuse_hash=None
    if a.reuse_lossless:
        reuse_path=a.reuse_lossless/'verification.json';reuse_data=json.loads(reuse_path.read_text());require(reuse_data['passed'],'Previous lossless archive is not qualified');reuse_hash=sha256(reuse_path)
        reuse={(c['session'],c['case']):(i,c) for i,c in enumerate(reuse_data['cases'])}
    for f in a.comparison:
        for c in json.loads(f.read_text())['cases']:
            key=(c['session'],c['case']);require(key not in previous,'Duplicate previous case');previous[key]=c
    def one(item):
        index,((session,name),prior)=item;folder=a.original_root/session/name;receipt,plan,controls,direction,x=static.original(folder,a.host)
        require(sha256(folder/'receipt.json')==prior['receipt_sha256'] and receipt['output_sha256']==prior['original_sha256'],'Prior reference binding differs')
        source=Path(receipt['input_path']);rate,input_audio=float_wav(source);require(rate==48000,'Wrong source rate');frames=len(x)
        clock=np.zeros((frames,2),dtype='<f4');clock[:min(len(input_audio),frames)]=input_audio[:frames]
        raw={k:round(controls[k]*255) for k in ['SceneVolume','Sub1Volume','Sub2Volume']}
        c=dict(direction=direction,block=receipt['maximum_block_size'],main=raw['SceneVolume'],time=raw['Sub1Volume'],pitch=raw['Sub2Volume'],changes=[])
        with tempfile.TemporaryDirectory(prefix='rmx-spiral-static-replay-') as tmp:
            tmp=Path(tmp);schedule=tmp/'schedule.tsv';schedule.write_text(motion.schedule(c));used=source
            if len(input_audio)!=frames:used=tmp/'padded-input.wav';write_wav(used,48000,clock.ravel())
            native=tmp/'native.wav';sanitized=tmp/'sanitized.wav';run([a.renderer,used,native,schedule])
            r=subprocess.run([str(a.sanitizer),str(used),str(sanitized),str(schedule)],capture_output=True,text=True,
                env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),timeout=120)
            require(r.returncode==0 and not r.stderr,'Sanitizer failure: '+r.stderr);digest=sha256(native);require(digest==sha256(sanitized),'Complete sanitizer WAV bytes differ')
            rate,y=float_wav(native);require(rate==48000 and y.shape==x.shape,'Extent differs');dry=static.transport(clock,clock,c['block'])[32:];x=x[32:];y=y[32:]
            intervals=[(0,len(x),'complete')]+[(s,min(s+48000,len(x)),'second') for s in range(0,len(x),48000)]
            windows=[dict(start=s,stop=t,kind=k,whole=score(x[s:t],y[s:t]),wet=score(x[s:t].astype(float)-dry[s:t],y[s:t].astype(float)-dry[s:t])) for s,t,k in intervals]
            compressed=root/f'{index:04d}-candidate.wav.gz'
            reused=False;old=reuse.get((session,name))
            if old and old[1]['candidate_wav_sha256']==digest:
                require(old[1]['receipt_sha256']==sha256(folder/'receipt.json'),'Lossless reference differs');previous_gzip=a.reuse_lossless/f'{old[0]:04d}-candidate.wav.gz'
                require(sha256(previous_gzip)==old[1]['lossless_candidate_sha256'],'Previous compressed output changed')
                if sys.platform=='darwin':subprocess.run(['/bin/cp','-c',str(previous_gzip),str(compressed)],check=True)
                else:shutil.copyfile(previous_gzip,compressed)
                require(sha256(compressed)==sha256(previous_gzip),'Lossless copy differs');reused=True
            else:
                with compressed.open('xb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',compresslevel=1,mtime=0) as z:z.write(native.read_bytes())
            with gzip.open(compressed,'rb') as z:require(hashlib.file_digest(z,'sha256').hexdigest()==digest,'Lossless archive changed WAV bytes')
            result=dict(session=session,case=name,passed=all(w['whole']['passed'] and w['wet']['passed'] for w in windows),windows=windows,
                sanitizer_byte_identical=True,lossless_storage_reused=reused,candidate_wav_sha256=digest,lossless_candidate_sha256=sha256(compressed),receipt_sha256=sha256(folder/'receipt.json'),input_sha256=receipt['input_sha256'])
        print('STATIC',index,name,result['passed'],flush=True);return result
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:rows=list(pool.map(one,enumerate(previous.items())))
    require(bound==motion.bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_spiral_static_motion_audit.py','tools/rmx_spiral_prospective.py']} and all(sha256(Path(b))==h for b,h in binaries.items()) and all(sha256(Path(f))==h for f,h in report_hashes.items()),'Audit input changed')
    if a.reuse_lossless:require(reuse_hash==sha256(a.reuse_lossless/'verification.json'),'Previous compressed report changed')
    save_json(root/'verification.json',dict(kind='spiral-stateful-complete-static-regression',live_engine=a.engine,passed=all(r['passed'] for r in rows),programs=len(rows),cases=rows,source_sha256=bound,binaries_sha256=binaries,previous_reports_sha256=report_hashes,previous_lossless_report_sha256=reuse_hash,
        scope='Every supplied prior static Original program through the current stateful Spiral candidate. Fixed32/32 transport, whole/wet/one-second1%perchannel screens, complete optimized/sanitized WAV byte identity. Native WAVs retained losslessly as gzip after decompressed SHA256 verification; transient inputs and replay files are disposable. No new prospective, live-wrapper or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
