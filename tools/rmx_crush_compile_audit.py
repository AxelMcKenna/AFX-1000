#!/usr/bin/env python3
"""Check the compiled Crush interval against an independent float32 replay.

The temporary probe inspects only this project's private numeric period. No
original plug-in or recorded audio is loaded. Audio acceptance is separate.
"""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

import numpy as np

from tools.reference_audio import save_json,sha256
from tools.rmx_drums import require
from tools.rmx_factory_match import new_directory

PROBE='''#include "rmx/Dsp.h"
#include "rmx/FilterEchoCalibration.h"
#include "rmx/FactoryEchoReturn.h"
#include <iostream>
#include <iomanip>
// Numeric research inspection of our own class, without a production API.
#define private public
#include "rmx/CalibratedFilterEcho.h"
#undef private
int main(){rmx::CalibratedFilterEcho model;
for(int raw=0;raw<256;++raw){model.configure(7,raw);
std::cout<<raw<<" "<<std::setprecision(17)<<model.holdPeriod<<"\\n";}}
'''


def audit(args):
    root=new_directory(args.output);repo=Path(__file__).resolve().parents[1]
    commands=json.loads(args.compile_commands.read_text())
    rows=[c for c in commands if Path(c['file']).resolve()==repo/'src/core/Scene.cpp']
    require(len(rows)==1,'Requires the production Scene compile command')
    tokens=shlex.split(rows[0]['command']);flags=[];index=1
    while index<len(tokens):
        token=tokens[index]
        if token in ('-o','-c'):index+=2;continue
        require(token not in ('-ffast-math','-Ofast'),'Fast-math build needs separate qualification')
        flags.append(token);index+=1
    source=root/'period.cpp';source.write_text(PROBE);binary=root/'period-probe'
    command=[tokens[0],*flags,str(source.resolve()),'-o',str(binary.resolve())]
    result=subprocess.run(command,capture_output=True,text=True,cwd=rows[0]['directory'],timeout=120)
    require(result.returncode==0,'Probe compilation failed: '+result.stderr)
    process=subprocess.run([str(binary.resolve())],capture_output=True,text=True,timeout=30)
    require(process.returncode==0 and not process.stderr,'Probe runtime failed')
    observed=[line.split() for line in process.stdout.splitlines()]
    require(len(observed)==256 and [int(r[0]) for r in observed]==list(range(256)),'Incomplete compiled sweep')
    f=np.float32;results=[]
    for raw,text in observed:
        raw=int(raw);scaled=f(f(raw)*f(24));period=f(scaled*f(1/255));boundary=f(period+f(1));expected=max(f(1),f(boundary-f(1)));actual=float(text)
        results.append(dict(raw_main=raw,expected_period=float(expected),compiled_period=actual,exact=actual==float(expected)))
    passed=all(r['exact'] for r in results)
    save_json(root/'verification.json',dict(kind='rmx-crush-compiled-interval-audit',passed=passed,exact_controls=sum(r['exact'] for r in results),controls=256,
        header_sha256=sha256(repo/'include/rmx/CalibratedFilterEcho.h'),auditor_sha256=sha256(Path(__file__)),compile_commands_sha256=sha256(args.compile_commands),
        production_scene_command=rows[0]['command'],probe_source=PROBE,probe_sha256=sha256(source),probe_binary_sha256=sha256(binary),compiler_command=command,
        compiler_version=subprocess.check_output([tokens[0],'--version'],text=True),compile_stderr=result.stderr,probe_stderr_empty=True,cases=results,
        scope='All256 compiled numeric periods use the production Scene compiler flags and are checked against separate NumPy float32 arithmetic. Read-only inspection of our own implementation. Does not establish original audio accuracy; original scalar and waveform campaigns provide separate evidence.'))
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compile-commands',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(audit(parser.parse_args()))


if __name__=='__main__':main()
