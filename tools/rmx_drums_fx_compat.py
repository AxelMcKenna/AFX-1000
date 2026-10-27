#!/usr/bin/env python3
"""Transfer an audited Engine corpus by exact output and sanitizer byte parity.

No new original recordings are claimed. Inherited raw-gate failures remain
failures even when compatibility and separate precision diagnostics pass.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_drums_fx import ACCEPTANCE,checked,recipe,schedule,source_hashes
from tools.rmx_drums_fx_precision import cases as precision_cases,original as precision_original
from tools.rmx_factory_match import new_directory,run


def verify(args):
    parent=json.loads(args.parent_audit.read_text());precision=json.loads(args.precision_report.read_text());binding=source_hashes();script=sha256(Path(__file__))
    require(parent['evidence_verified'] and parent['live_engine'] and parent['backend']=='engine' and parent['acceptance']==ACCEPTANCE,'Wrong parent audit')
    require(precision['passed'] and precision['source_sha256']==parent['source_sha256'] and precision['renderer_sha256']==parent['renderer_sha256'] and precision['acceptance']==ACCEPTANCE,'Precision parent differs')
    stages={'discovery':'discovery','former':'fresh','second':'fresh-v2','third':'fresh-v3','fourth':'fresh-v4','fifth':'fresh-v5','sixth':'fresh-v6','live-fresh':'live-fresh'}
    require(sorted(d[0] for d in args.dataset)==sorted(stages),'Requires every audited parent dataset')
    root=new_directory(args.output);rows=[];binaries={str(p):sha256(p) for p in [args.renderer,args.sanitized]};parent_rows={(r['stage'],r['case']):r for r in parent['cases']};seen=set()
    command_path=args.sanitized.parent/'compile_commands.json';commands=json.loads(command_path.read_text());suffixes=('/Engine.cpp','/Scene.cpp','/ReverbUp.cpp','/ReverbDown.cpp','/drums/Kick.cpp','/drums/Snare.cpp','/drums/Clap.cpp','/drums/Hat.cpp','/Wav.cpp')
    units=[c for c in commands if c['file'].endswith(suffixes) or (c['file'].endswith('/drums_fx_probe.cpp') and 'RMX_DRUMS_SHARED_FIXTURE' not in c['command'])]
    require(len(units)==10 and all('-fsanitize=address,undefined' in c['command'] for c in units),'Missing native sanitizer units')
    require(all('-ffp-contract=off' in c['command'] for c in units if '/drums/' in c['file'] or '/Reverb' in c['file']),'Missing identified float flags')
    symbols={}
    for p in [args.renderer,args.sanitized]:
        text=subprocess.check_output(['nm','-C',str(p)],text=True);require('rmx::Engine::process(' in text,'Fixture lacks actual Engine')
        symbols[str(p)]=hashlib.sha256(text.encode()).hexdigest()
    def render(stage,c,source,old_directory,row):
        old=old_directory/(c['name']+'.wav');old_plan=old_directory/(c['name']+'.tsv')
        require(sha256(old)==row['candidate_sha256'] and sha256(old_plan)==row['schedule_sha256'] and old_plan.read_text()==schedule(c),'Parent output/schedule changed')
        out=root/(stage+'-'+c['name']+'.wav');san=root/(stage+'-'+c['name']+'-asan.wav')
        run([args.renderer,source,out,old_plan]);require(sha256(out)==row['candidate_sha256'],'Current output differs from audited parent: '+c['name'])
        result=subprocess.run([str(args.sanitized),str(source),str(san),str(old_plan)],capture_output=True,text=True,timeout=120,
            env=os.environ|dict(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        require(result.returncode==0 and not result.stderr and sha256(san)==sha256(out),'Sanitizer output/stderr differs')
        rows.append(dict(stage=stage,case=c['name'],raw_gate_passed=row['passed'],current_sha256=sha256(out),parent_sha256=row['candidate_sha256'],
                         schedule_sha256=row['schedule_sha256'],audio_byte_identical=True,sanitizer_byte_identical=True))
        print('UNCHANGED',stage,c['name'],flush=True)
    for name,session_text,path_text in args.dataset:
        session=Path(session_text);path=Path(path_text);d=json.loads(path.read_text());cases=recipe(stages[name]);call=copy.copy(args);call.stage=stages[name];call.session=session
        require(d['source_sha256']==parent['source_sha256'] and d['renderer_sha256']==parent['renderer_sha256'] and d['backend']=='engine' and d['live_engine'] and d['acceptance']==ACCEPTANCE,'Parent comparison differs')
        require([r['case'] for r in d['cases']]==[c['name'] for c in cases],'Parent recipes differ')
        for c,row in zip(cases,d['cases']):
            key=(name,c['name']);old=parent_rows[key];require(key not in seen and old['comparison_sha256']==sha256(path) and old['candidate_sha256']==row['candidate_sha256'] and old['passed']==row['passed'],'Parent audit differs');seen.add(key)
            _,provenance=checked(call,c);require(all(row[k]==v for k,v in provenance.items()),'Original binding differs')
            render(name,c,session/'program.wav',path.parent,row)
    require(seen==set(parent_rows),'Incomplete audited corpus')
    call=copy.copy(args);call.session=args.precision_session;call.prediction=args.precision_prediction
    for c,row in zip(precision_cases(),precision['cases'],strict=True):
        require(row['case']==c['name'],'Precision recipe differs');_,receipt=precision_original(call,c)
        require(row['receipt_sha256']==sha256(args.precision_session/c['name']/'receipt.json'),'Precision original changed')
        render('precision',c,args.precision_session/'zero.wav',args.precision_report.parent,row)
    require(binding==source_hashes() and script==sha256(Path(__file__)) and all(sha256(Path(k))==v for k,v in binaries.items()),'Current source/binary changed')
    save_json(root/'verification.json',dict(kind='rmx-live-engine-drums-compatibility',compatibility_passed=True,all_raw_gates_passed=all(r['raw_gate_passed'] for r in rows),
        programs=len(rows),raw_programs_passed=sum(r['raw_gate_passed'] for r in rows),cases=rows,source_sha256=binding,renderer_sha256=binaries,
        parent_audit_sha256=sha256(args.parent_audit),precision_report_sha256=sha256(args.precision_report),precision_reconstruction_preserved_by_identical_outputs=True,
        verifier_sha256=script,sanitizer_compile_commands_sha256=sha256(command_path),sanitizer_compile_commands=[c['command'] for c in units],engine_symbol_hashes=symbols,
        sanitizer_stderr_empty=True,acceptance=ACCEPTANCE,
        scope='Complete audited parent corpus plus its two independent zero-input precision fixtures. Original provenance is rechecked; every current optimized output must be byte-identical to the audited parent and every sanitized output to current optimized output. Exact bytes transfer all parent scores, windows and precision reconstruction without new fitting. This is compatibility evidence, not new prospective evidence. The inherited near-null mixed wet-window failure remains failed.'))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['parent-audit','precision-report','precision-session','precision-prediction','renderer','sanitized','host','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--dataset',nargs=3,action='append',required=True)
    raise SystemExit(verify(p.parse_args()))


if __name__=='__main__':main()
