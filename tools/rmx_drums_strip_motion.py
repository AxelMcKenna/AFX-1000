#!/usr/bin/env python3
"""Recheck the retained original held-touch strip-motion discovery programs."""
import argparse
from pathlib import Path

from tools.noise_statistics import float_wav
from tools.reference_audio import save_json,sha256
from tools.rmx_drums import DRUMS,FRAMES,require
from tools.rmx_drums_roll import original,schedule,source_hashes
from tools.rmx_factory_match import new_directory,run
from tools.rmx_filter_match import screen
from tools.rmx_kick_validate import ACCEPTANCE


def recipe():
    rows=[]
    for pad,drum in enumerate(DRUMS):
        for variant,positions in [('up',[51,102,153,204,255]),('down',[255,204,153,102,51]),('same',[102]*5)]:
            changes=[dict(frame=at,type='X',value=value) for at,value in zip([1,120109,168173,216251,264349],positions)]
            changes += [dict(frame=48061,type='H',value=pad),dict(frame=48093,type='R',value=pad),dict(frame=96079,type='T',value=1),dict(frame=336457,type='T',value=0)]
            changes.sort(key=lambda e:e['frame'])
            rows.append(dict(name=f'roll-strip-{drum}-{variant}',drum=drum,variant=variant,block=277+pad*2,level=128,pitch=128,hits=[48061],position=positions[0],bpm=120,quantize=0,changes=changes))
    return rows


def compare(args):
    script=sha256(Path(__file__));binding=source_hashes();binary=sha256(args.renderer);root=new_directory(args.output);rows=[]
    for c in recipe():
        a,provenance=original(args,c);plan=root/(c['name']+'.tsv');plan.write_text(schedule(c));out=root/(c['name']+'.wav');dry=root/(c['name']+'-dry.wav')
        run([args.renderer,args.session/'silence.wav',out,plan,dry]);rate,b=float_wav(out);drate,d=float_wav(dry)
        require(rate==drate==48000 and a.shape==b.shape==d.shape==(FRAMES,2) and not d.any(),'Candidate rate/extent/dry differs')
        a,b=a[32:],b[32:];whole=screen(a,b);touches=[e for e in c['changes'] if e['type']=='T'];last=touches[-1]['frame']
        intervals=[('selection',at,at+120000) for at in c['hits']]+[('tail',last,FRAMES-32)]
        intervals += [('touch-attack' if e['value'] else 'roll-stop',e['frame'],e['frame']+(256 if e['value'] else 1024)) for e in touches]
        intervals += [('roll-window',at,min(at+24000,last)) for at in range(touches[0]['frame'],last,24000)]
        intervals += [('strip-change',e['frame'],e['frame']+24000) for e in c['changes'] if e['type']=='X' and e['frame']>1]
        windows=[]
        for kind,start,stop in intervals:
            stop=min(stop,len(a));windows.append(dict(kind=kind,start=start,stop=stop,score=screen(a[start:stop],b[start:stop])))
        passed=whole['passed'] and all(w['score']['passed'] for w in windows)
        rows.append(provenance|dict(passed=passed,whole=whole,windows=windows,candidate_sha256=sha256(out),dry_sha256=sha256(dry),schedule_sha256=sha256(plan)))
        print('PASS' if passed else 'FAIL',c['name'],flush=True)
    require(script==sha256(Path(__file__)) and binding==source_hashes() and binary==sha256(args.renderer),'Comparison source/binary changed')
    save_json(root/'comparison.json',dict(kind='rmx220-drums-roll-strip-motion-regression',passed=all(r['passed'] for r in rows),stage='strip-discovery',role='development_regression',cases=rows,source_sha256=binding,script_sha256=script,renderer_sha256=binary,acceptance=ACCEPTANCE,
      scope='Twelve retained moving-strip discovery programs, factory48k/120BPM. Whole/selection/touch/strip-change/roll/stop/tail windows, fixed32/32, unchanged1% per channel, no gain/alignment fitting. Fresh moving-strip predictions are separate.'))
    return 0 if all(r['passed'] for r in rows) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['session','renderer','host','output']:p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(compare(p.parse_args()))


if __name__=='__main__':main()
