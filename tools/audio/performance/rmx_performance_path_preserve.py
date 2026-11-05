#!/usr/bin/env python3
"""Replay prior manual-clock output hashes after the host-overdub boundary fix."""
import argparse,gzip,json,tempfile
from pathlib import Path
import numpy as np
from tools.audio.drums import rmx_drum_combos as combo
from tools.audio.drums import rmx_drum_gestures as gesture
from tools.audio.performance import rmx_performance_path as path
from tools.audio.noise.rmx_noise_stream import RenderSpace
from tools.audio.common.reference_audio import sha256,save_json,write_wav


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['renderer','before','prior_report','output']:p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Choose a new report')
    bound=path.bindings()|{str(Path(__file__)):sha256(Path(__file__))};binaries={k:sha256(getattr(a,k)) for k in ['renderer','before']};prior=json.loads(gzip.decompress(a.prior_report.read_bytes()) if a.prior_report.suffix=='.gz' else a.prior_report.read_text());rows=[];peak=0
    jobs=[(combo,c) for stage in ['multi','multi-fresh','user-overdub','user-overdub-fresh'] for c in combo.recipe(stage)]+[(gesture,c) for stage in ['recorded','recorded-fresh','recorded-fresh2'] for c in gesture.recipe(stage)]
    with tempfile.TemporaryDirectory(prefix='rmx-path-preserve-',dir='/private/tmp') as directory:
        root=Path(directory);space=RenderSpace(root);write_wav(root/'input.wav',48000,np.zeros(path.FRAMES*2))
        for module,c in jobs:
            program=root/'program.tsv';program.write_text(module.schedule(c));hashes=[]
            for renderer in [a.before,a.renderer]:
                space.run([renderer,root/'input.wav',root/'out.wav',program,root/'dry.wav']);hashes.append([sha256(root/n) for n in ['out.wav','dry.wav']])
                for n in ['out.wav','dry.wav']:(root/n).unlink()
            rows.append(dict(case=c['name'],kind='manual-clock-before-after',complete_output_identity=hashes[0]==hashes[1],before_sha256=hashes[0],after_sha256=hashes[1]));print('PRESERVE',c['name'],rows[-1]['complete_output_identity'],flush=True)
        (root/'input.wav').unlink()
        for old in prior['cases']:
            c=old['case']
            if c['family']=='tempo':continue
            write_wav(root/'input.wav',48000,path.stimulus(c).reshape(-1));program=root/'program.tsv';program.write_text(path.schedule(c));space.run([a.renderer,root/'input.wav',root/'out.wav',program,root/'dry.wav']);digest=sha256(root/'out.wav')
            rows.append(dict(case=c['name'],kind='prior-fresh-prediction-replay',complete_output_identity=digest==old['prediction_sha256'],before_sha256=old['prediction_sha256'],after_sha256=digest,prior_passed=old['passed']))
            for n in ['input.wav','out.wav','dry.wav']:(root/n).unlink()
            print('REPLAY',c['name'],rows[-1]['complete_output_identity'],flush=True)
        peak=space.peak
    if bound!=path.bindings()|{str(Path(__file__)):sha256(Path(__file__))} or any(sha256(getattr(a,k))!=v for k,v in binaries.items()):raise ValueError('Preservation inputs changed')
    save_json(a.output,dict(kind='manual-clock-and-mixed-performance-preservation',verification_passed=True,passed=all(r['complete_output_identity'] for r in rows),cases=rows,source_sha256=bound,binary_sha256=binaries,prior_report_sha256=sha256(a.prior_report),peak_temporary_bytes=peak,raw_audio_retained=False,all_temporary_directories_removed=not root.exists(),scope='180 manual-clock overdub/strip/mute/delete/quantize programs compared against the pinned pre-boundary-fix renderer;90 non-tempo fresh active/control predictions replayed against retained whole-WAV hashes. Identity transfers only the original report verdict, including failures; no new Original capture.'))


if __name__=='__main__':main()
