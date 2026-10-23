#!/usr/bin/env python3
"""Check the saved carrier board against the circuit and native KiCad DRC.

The carrier contains the first four B1 sheets, excluding the two offboard
switches. Panel logic and the Seed are wired assemblies, not hidden PCB parts.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from generate_budget import ROOT,DEST,all_sheets
from check_carrier import sha


def inspect(path):
    # Only run this branch with KiCad's Python / pcbnew environment.
    config=ROOT/'build/hardware/pcb-config';config.mkdir(parents=True,exist_ok=True)
    os.environ['KICAD_CONFIG_HOME']=str(config)
    import pcbnew as p
    board=p.LoadBoard(str(path));parts={}
    for f in board.GetFootprints():
        parts[f.GetReference()]=dict(value=f.GetValue(),footprint=f.GetFPIDAsString(),
            pads={pad.GetNumber():pad.GetNetname() or None for pad in f.Pads() if pad.GetNumber()})
    print(json.dumps(dict(copper_layers=board.GetCopperLayerCount(),parts=parts,
                         tracks=sum(not isinstance(t,p.PCB_VIA) for t in board.GetTracks()),
                         vias=sum(isinstance(t,p.PCB_VIA) for t in board.GetTracks()))))


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--check',action='store_true');a.add_argument('--inspect',type=Path)
    a.add_argument('--cli',type=Path);a.add_argument('--python',type=Path);args=a.parse_args()
    board=DEST/'pcb/carrier.kicad_pcb';record_path=DEST/'pcb/native-check.json'
    if args.inspect:inspect(args.inspect);return
    files=[ROOT/'tools'/n for n in ['layout_budget.py','check_budget_pcb.py','generate_budget.py','generate_carrier.py','generate_bypass.py']]
    files += [board,DEST/'pcb/layout.json',DEST/'pcb/fp-lib-table',DEST/'pcb/carrier.kicad_pro',ROOT/'hardware/electrical/bypass.json',ROOT/'hardware/prototype.json',DEST/'mechanics.json']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
    if args.check:
        r=json.loads(record_path.read_text());assert r['source_sha256']==hashes,'B1 board evidence is stale'
        assert r['drc_violations']==0 and r['unconnected']==0 and r['pad_matrix_verified']
        print('PASS: saved B1 PCB / native DRC record current; fabrication/analog/fit review still required');return
    assert args.cli and args.cli.is_file(),'Specify native KiCad --cli'
    python=args.python or args.cli.parents[1]/'Frameworks/Python.framework/Versions/Current/bin/python3'
    result=subprocess.run([str(python),str(Path(__file__).resolve()),'--inspect',str(board)],check=True,capture_output=True,text=True)
    actual=json.loads(result.stdout);assert actual['copper_layers']==4
    sheets=all_sheets();global_={v['net'] for d in sheets for p in d['components'] if p['ref'].startswith('J') for v in p['pins'] if v.get('net')}
    wanted={}
    for d in sheets[:4]:
        for p in d['components']:
            if p.get('virtual') or p['ref'] in ('SW32','SW34'):continue
            pads={}
            for v in p['pins']:
                n=v.get('net');pads[v['number']]=n if not n or n in global_ else '/'+d['project']+'/'+n
            wanted[p['ref']]=dict(value=p['value'],footprint=p['footprint'],pads=pads)
    assert {r:v for r,v in actual['parts'].items() if not r.startswith('H')}==wanted,'Saved PCB pads/values/footprints differ from modeled circuit'
    assert set(actual['parts'])==set(wanted)|{'H1','H2','H3','H4'}
    out=ROOT/'build/hardware/budget-native';out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,KICAD_CONFIG_HOME=str(out/'config'),FONTCONFIG_FILE=str(out/'fonts.conf'),
             KICAD10_FOOTPRINT_DIR=str(args.cli.parents[1]/'SharedSupport/footprints'))
    report=out/'pcb-drc.json'
    result=subprocess.run([str(args.cli),'pcb','drc','--severity-all','--format','json','--exit-code-violations','--output',str(report),str(board)],env=env,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    drc=json.loads(report.read_text());assert not drc['violations'] and not drc['unconnected_items']
    r=dict(scope='Carrier subset only; offboard/panel wiring checked separately. No physical audio, assembly or fabrication approval.',
           date=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=hashes,
           kicad_version=drc['kicad_version'],drc_violations=0,unconnected=0,
           default_ignored_checks=drc['ignored_checks'],pad_matrix_verified=True,
           circuit_footprints=len(wanted),**{k:actual[k] for k in ['copper_layers','tracks','vias']},
           drc_sha256=sha(report))
    record_path.write_text(json.dumps(r,indent=2)+'\n')
    print(f'PASS: {len(wanted)} PCB components/pad matrices; native DRC zero violations / zero unconnected')


if __name__=='__main__':main()
