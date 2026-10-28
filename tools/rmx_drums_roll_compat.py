#!/usr/bin/env python3
"""Transfer prior drum scores only when current optimized and sanitized audio is identical."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import checked,require
from tools import rmx_drums_engine as dry
from tools import rmx_drums_motion as motion
from tools import rmx_drums_fx as fx
from tools.rmx_drums_roll import source_hashes
from tools.rmx_factory_match import new_directory


def verify(args):
    binding=source_hashes();script=sha256(Path(__file__));root=new_directory(args.output);rows=[];parents={};symbols={};units=[]
    commands_path=args.asan/'compile_commands.json';commands=json.loads(commands_path.read_text())
    probes=dict(dry='rmx_drum_probe',motion='rmx_drum_motion_probe',fx='rmx_drums_fx_probe')
    binaries={str(folder/probe):sha256(folder/probe) for folder in [args.core,args.asan] for probe in probes.values()}
    for group,probe in probes.items():
        for folder in [args.core,args.asan]:
            binary=folder/probe;text=subprocess.check_output(['nm','-C',str(binary)],text=True)
            require('rmx::Engine::process(' in text,'Fixture lacks actual Engine');symbols[str(binary)]=hashlib.sha256(text.encode()).hexdigest()
        filenames=dict(dry='/drum_probe.cpp',motion='/drum_motion_probe.cpp',fx='/drums_fx_probe.cpp')
        suffixes=('/Engine.cpp','/Scene.cpp','/ReverbUp.cpp','/ReverbDown.cpp','/drums/Kick.cpp','/drums/Snare.cpp','/drums/Clap.cpp','/drums/Hat.cpp','/Wav.cpp')
        selected=[c for c in commands if c['file'].endswith(suffixes) or (c['file'].endswith(filenames[group]) and 'RMX_DRUMS_SHARED_FIXTURE' not in c['command'])]
        require(len(selected)==10 and all('-fsanitize=address,undefined' in c['command'] for c in selected),'Missing instrumented units')
        require(all('-ffp-contract=off' in c['command'] for c in selected if '/drums/' in c['file'] or '/Reverb' in c['file']),'Identified float flags differ');units += selected
        parent_path=args.parent_root/f'drums-roll-prior-{group}-v1/verification.json'
        published=Path(f'research/audio/measurements/2026-10-28-drums-roll-prior-{group}.json')
        require(sha256(parent_path)==sha256(published),'Published parent summary changed');parents[group]=sha256(parent_path)
        parent=json.loads(parent_path.read_text());count=0
        for dataset in parent['datasets']:
            path=Path(dataset['comparison']);require(sha256(path)==dataset['comparison_sha256'],'Parent comparison changed')
            d=json.loads(path.read_text());stage=dataset['stage'];session=Path(dataset['session']);helper=dict(dry=dry,motion=motion,fx=fx)[group]
            require(d['acceptance']==helper.ACCEPTANCE,'Parent gates changed')
            cases=(dry.recipe() if stage=='fresh' else dry.cases_for(stage)) if group=='dry' else helper.recipe(stage)
            require([c['name'] for c in cases]==[r['case'] for r in d['cases']] and len(cases)==dataset['programs'],'Parent recipe/count differs')
            for c,row in zip(cases,d['cases'],strict=True):
                if group=='fx':
                    _,provenance=fx.checked(SimpleNamespace(session=session,host=args.host,stage=stage),c)
                else:
                    _,provenance=checked(session,c,plan_builder=helper.original_plan,**(dict(cold_kick=c['drum']=='kick') if group=='dry' else {}))
                    receipt=json.loads((session/c['name']/'receipt.json').read_text());require(receipt['host_sha256']==sha256(args.host),'Original host changed')
                    for member in receipt['plugin']['binary_files']:require(sha256(Path(receipt['plugin']['bundle'])/member['path'])==member['sha256'],'Original binary changed')
                require(all(row[k]==v for k,v in provenance.items()),'Parent original provenance differs')
                plan=path.parent/(c['name']+'.tsv');old=path.parent/(c['name']+'.wav')
                require(plan.read_text()==helper.schedule(c) and sha256(plan)==row['schedule_sha256'] and sha256(old)==row['candidate_sha256'],'Parent candidate/schedule changed')
                source=session/('program.wav' if group=='fx' else 'silence.wav');folder=root/(group+'-'+stage);folder.mkdir(exist_ok=True)
                out=folder/(c['name']+'.wav');san=folder/(c['name']+'-asan.wav');out_dry=folder/(c['name']+'-dry.wav');san_dry=folder/(c['name']+'-asan-dry.wav')
                for binary,audio,trace in [(args.core/probe,out,out_dry),(args.asan/probe,san,san_dry)]:
                    command=[str(binary),str(source),str(audio),str(plan)]+([] if group=='fx' else [str(trace)])
                    r=subprocess.run(command,capture_output=True,text=True,timeout=120,env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
                    require(r.returncode==0 and not r.stderr,'Replay failed: '+c['name']+' '+r.stderr)
                require(sha256(out)==row['candidate_sha256']==sha256(san),'Current optimized/sanitized audio differs from parent: '+c['name'])
                if group!='fx':require(sha256(out_dry)==sha256(san_dry)==row['dry_trace_sha256' if group=='dry' else 'dry_sha256'],'Dry trace changed')
                rows.append(dict(group=group,stage=stage,case=c['name'],raw_gate_passed=row['passed'],candidate_sha256=sha256(out),comparison_sha256=sha256(path),receipt_sha256=provenance['receipt_sha256'],optimized_parent_byte_identical=True,sanitizer_byte_identical=True));count+=1
                print('UNCHANGED',group,stage,c['name'],flush=True)
        require(count==dict(dry=224,motion=44,fx=568)[group],'Incomplete parent corpus')
    failures=[dict(group=r['group'],stage=r['stage'],case=r['case']) for r in rows if not r['raw_gate_passed']]
    require(failures==[dict(group='fx',stage='live-fresh',case='drum-fx-live-effect7-route1')],'Inherited failure changed')
    require(binding==source_hashes() and script==sha256(Path(__file__)) and all(sha256(Path(p))==v for p,v in binaries.items()),'Compatibility source/binary changed')
    save_json(root/'verification.json',dict(kind='rmx-drums-roll-prior-byte-compatibility',compatibility_passed=True,programs=len(rows),raw_programs_passed=sum(r['raw_gate_passed'] for r in rows),inherited_failures=failures,cases=rows,
      source_sha256=binding,verifier_sha256=script,renderer_sha256=binaries,parent_summaries_sha256=parents,sanitizer_compile_commands_sha256=sha256(commands_path),sanitizer_compile_commands=[c['command'] for c in units],engine_symbol_sha256=symbols,sanitizer_stderr_empty=True,
      scope='224 static dry,44 moving-control and568 drum/Scene programs. Rechecks original provenance and unchanged recipes/gates, then requires complete current optimized audio to equal the published kick-corrected parent bytes and sanitizer audio to equal optimized bytes. This transfers all prior scores/windows without fitting or new captures. The existing near-null Crush wet-window failure remains failed. No new roll/tempo/wrapper qualification.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['core','asan','host','parent-root','output']:p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(verify(p.parse_args()))


if __name__=='__main__':main()
