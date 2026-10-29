#!/usr/bin/env python3
"""Score nonzero-start discovery separately from warm Spiral qualification."""
import argparse,json,os,subprocess
from pathlib import Path
from tools import rmx_spiral_cold as cold
from tools import rmx_spiral_motion_match as match
from tools.rmx_spiral_prospective import score
from tools.rmx_factory_match import new_directory,run
from tools.rmx_drums import require
from tools.reference_audio import save_json,sha256
from tools.noise_statistics import float_wav


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['session','host','renderer','sanitizer','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--engine',action='store_true')
    a=p.parse_args();root=new_directory(a.output);bound=match.bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_spiral_cold.py','tools/rmx_spiral_cold_match.py','tools/rmx_spiral_prospective.py']};binaries={str(b):sha256(b) for b in [a.renderer,a.sanitizer]}
    matrix=json.loads((a.session/'matrix.json').read_text());require([c['name'] for c in matrix['cases']]==[c['name'] for c in cold.recipe()],'Coverage differs')
    symbols=subprocess.check_output(['nm','-C',str(a.sanitizer)],text=True);require('___asan_init' in symbols and '___ubsan_handle_' in symbols,'Missing sanitizers');rows=[]
    if a.engine:require('rmx::Engine::process(' in symbols and 'rmx::Engine::process(' in subprocess.check_output(['nm','-C',str(a.renderer)],text=True),'Replay is not the live Engine')
    for c in cold.recipe():
        receipt,x,input_audio=match.original(a,c,cold.sources()[c['source']]);schedule=root/(c['name']+'.tsv');schedule.write_text(match.schedule(c));out=schedule.with_suffix('.wav');sanitized=root/(c['name']+'-sanitized.wav');run([a.renderer,a.session/(c['source']+'.wav'),out,schedule])
        r=subprocess.run([str(a.sanitizer),str(a.session/(c['source']+'.wav')),str(sanitized),str(schedule)],capture_output=True,text=True,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),timeout=120);require(r.returncode==0 and not r.stderr,'Sanitizer failure: '+r.stderr);require(sha256(out)==sha256(sanitized),'Sanitizer WAV differs');rate,y=float_wav(out);require(rate==48000 and x.shape==y.shape,'Extent differs');x=x[32:];y=y[32:];dry=match.transport(input_audio,c['block'],[])[32:]
        intervals=[(0,len(x)),(0,1024),(1024,48000)]+[(s,min(len(x),s+48000)) for s in range(48000,len(x),48000)];windows=[dict(start=s,stop=t,whole=score(x[s:t],y[s:t]),wet=score(x[s:t].astype(float)-dry[s:t],y[s:t].astype(float)-dry[s:t])) for s,t in intervals];passed=all(w['whole']['passed'] and w['wet']['passed'] for w in windows);rows.append(dict(case=c['name'],passed=passed,windows=windows,sanitizer_byte_identical=True,candidate_sha256=sha256(out),receipt_sha256=sha256(a.session/c['name']/'receipt.json')));print('COLD',c['name'],passed,flush=True)
    require(bound==match.bindings()|{n:sha256(Path(n)) for n in ['tools/rmx_spiral_cold.py','tools/rmx_spiral_cold_match.py','tools/rmx_spiral_prospective.py']} and all(sha256(Path(b))==h for b,h in binaries.items()),'Candidate changed');save_json(root/'verification.json',dict(kind='spiral-cold-development-independent-audit',live_engine=a.engine,passed=all(r['passed'] for r in rows),cases=rows,source_sha256=bound,binaries_sha256=binaries,scope='Existing nonzero-start programs, Default48k/120BPM AutoButton1. Whole/wet/startup/tail windows1%perchannel plus complete optimized/sanitizer WAV byte identity. No new prospective capture, wrapper or hardware qualification.'))
    return 0 if all(r['passed'] for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
