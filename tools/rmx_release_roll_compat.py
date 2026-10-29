#!/usr/bin/env python3
"""Require current optimized/instrumented rolls to equal the published 89 programs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools import rmx_drums_roll as roll
from tools.rmx_drums_strip_motion import recipe as strip_recipe
from tools.rmx_factory_match import new_directory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['host','renderer','sanitizer','original-root','parent-root','parent','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();root=new_directory(a.output);binding=roll.source_hashes();script=sha256(Path(__file__));parent=json.loads(a.parent.read_text())
    require(parent['audio_passed'] and parent['evidence_verified'] and parent['programs']==89 and len(parent['cases'])==89,'Wrong published parent')
    needed={r['comparison_sha256'] for r in parent['cases']};comparisons={}
    for name in subprocess.check_output(['rg','--files',str(a.parent_root),'-g','comparison.json'],text=True).splitlines():
        path=Path(name);h=sha256(path)
        if h in needed:comparisons.setdefault(h,path)
    require(needed<=comparisons.keys(),'Missing parent comparisons')
    wanted={r['case'] for r in parent['cases']};digests={r['receipt_sha256'] for r in parent['cases']};receipts={}
    for name in subprocess.check_output(['rg','--files',str(a.original_root),'-g','receipt.json'],text=True).splitlines():
        path=Path(name)
        if path.parent.name in wanted:
            h=sha256(path)
            if h in digests:receipts.setdefault(h,path)
    require(digests<=receipts.keys(),'Missing original captures')
    commands_path=a.sanitizer.parent/'compile_commands.json';commands=json.loads(commands_path.read_text());suffixes=['/Engine.cpp','/FactoryRelease.cpp','/Scene.cpp','/ReverbUp.cpp','/ReverbDown.cpp','/drums/Kick.cpp','/drums/Snare.cpp','/drums/Clap.cpp','/drums/Hat.cpp','/Wav.cpp','/drum_roll_probe.cpp'];selected=[c for c in commands if any(c['file'].endswith(s) for s in suffixes)]
    require(len(selected)==11 and all('-fsanitize=address,undefined' in c['command'] for c in selected),'Missing instrumented units')
    binaries={str(b):sha256(b) for b in [a.renderer,a.sanitizer]};rows=[]
    for old in parent['cases']:
        stage=old['stage'];cases=strip_recipe() if stage=='strip-discovery' else roll.recipe(stage);c=next(c for c in cases if c['name']==old['case']);capture=receipts[old['receipt_sha256']].parent
        _,provenance=roll.original(SimpleNamespace(session=capture.parent,host=a.host),c);require(provenance['receipt_sha256']==old['receipt_sha256'],'Original binding differs')
        comparison_path=comparisons[old['comparison_sha256']];comparison=json.loads(comparison_path.read_text());require(comparison['acceptance']==roll.ACCEPTANCE,'Parent gates differ');row=next(r for r in comparison['cases'] if r['case']==c['name']);require(row['passed'] and row['candidate_sha256']==old['candidate_sha256'],'Parent verdict/audio differs')
        plan=comparison_path.parent/(c['name']+'.tsv');before=comparison_path.parent/(c['name']+'.wav');dry=comparison_path.parent/(c['name']+'-dry.wav');require(plan.read_text()==roll.schedule(c) and sha256(plan)==row['schedule_sha256'] and sha256(before)==row['candidate_sha256'] and sha256(dry)==row['dry_sha256'],'Parent candidate changed')
        receipt=json.loads((capture/'receipt.json').read_text());source=Path(receipt['input_path']);folder=root/(stage+'-'+c['name']);folder.mkdir()
        for name,binary in [('optimized',a.renderer),('sanitizer',a.sanitizer)]:
            output=folder/(name+'.wav');trace=folder/(name+'-dry.wav');r=subprocess.run([str(binary),str(source),str(output),str(plan),str(trace)],capture_output=True,text=True,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'),timeout=120)
            require(r.returncode==0 and not r.stderr,'Current replay failed '+r.stderr);require(sha256(output)==row['candidate_sha256'] and sha256(trace)==row['dry_sha256'],'Current roll/dry bytes differ from parent: '+c['name'])
        rows.append(old|dict(optimized_parent_byte_identical=True,sanitizer_byte_identical=True,dry_byte_identical=True));print('UNCHANGED',stage,c['name'],flush=True)
    require(binding==roll.source_hashes() and script==sha256(Path(__file__)) and all(sha256(Path(n))==h for n,h in binaries.items()),'Sources/binaries changed')
    save_json(root/'verification.json',dict(kind='rmx-release-prior-roll-compatibility',passed=True,programs=89,cases=rows,source_sha256=binding,verifier_sha256=script,renderer_sha256=binaries,parent_sha256=sha256(a.parent),sanitizer_compile_commands=selected,commands_sha256=sha256(commands_path),scope='All89 published drum-roll programs: original provenance and unchanged gates, complete optimized/sanitized audio and dry traces equal their qualified parent bytes. Transfers prior scoped scores; no new original, tempo, routing or hardware qualification.'))


if __name__=='__main__':main()
