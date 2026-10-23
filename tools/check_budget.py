#!/usr/bin/env python3
"""Native KiCad checks and current-source evidence for the B1 hardware variant."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from generate_budget import ROOT, DEST, all_sheets, generate
from check_carrier import sha, verify_netlist, verify_footprints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--cli',type=Path,default=shutil.which('kicad-cli'))
    parser.add_argument('--footprints',type=Path)
    args=parser.parse_args()
    subprocess.run([sys.executable,str(ROOT/'tools/generate_budget.py'),'--check'],check=True)
    files={DEST/n for n in generate()}
    files.update(ROOT/'tools'/n for n in ['generate_budget.py','generate_carrier.py','generate_bypass.py','check_budget.py','check_carrier.py'])
    files.update([ROOT/'hardware/prototype.json',ROOT/'hardware/electrical/bypass.json'])
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
    record_path=DEST/'native-check.json'
    if args.check:
        record=json.loads(record_path.read_text())
        assert record['source_sha256']==hashes,'B1 native check is stale'
        assert record['erc']['violations']==0 and record['netlist']['verified']
        print('PASS: B1 native evidence matches current sources; not fabrication/bench approval')
        return
    assert args.cli and args.cli.is_file(),'Supply KiCad 10 --cli'
    cli=args.cli.resolve();fp=args.footprints or cli.parents[1]/'SharedSupport/footprints'
    out=ROOT/'build/hardware/budget-native';out.mkdir(parents=True,exist_ok=True)
    font=out/'fonts.conf'
    font.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>'+str(out/'font-cache')+'</cachedir></fontconfig>')
    env=dict(os.environ,KICAD_CONFIG_HOME=str(out/'config'),FONTCONFIG_FILE=str(font),KICAD10_FOOTPRINT_DIR=str(fp.resolve()))
    def run(*a):
        r=subprocess.run([str(cli),*map(str,a)],env=env,capture_output=True,text=True)
        if r.returncode or any(t in (r.stdout+r.stderr).lower() for t in ['warning:','error:']):
            raise RuntimeError(r.stdout+r.stderr)
        return r.stdout.strip()
    version=run('version');assert version.startswith('10.')
    master=DEST/'budget5v.kicad_sch'
    run('sch','erc','--severity-all','--format','json','--exit-code-violations','-o',out/'erc.json',master)
    erc=json.loads((out/'erc.json').read_text());assert not any(s['violations'] for s in erc['sheets'])
    sheets=all_sheets();assert len(erc['sheets'])==len(sheets)+1
    run('sch','export','netlist','--format','kicadxml','-o',out/'budget.net.xml',master)
    parts={p['ref']:p for d in sheets for p in d['components'] if not p.get('virtual')}
    globals_={v['net'] for d in sheets for p in d['components'] if p['ref'].startswith('J') for v in p['pins'] if v.get('net')}
    expected={}
    for d in sheets:
        for p in d['components']:
            if p.get('virtual'):continue
            for v in p['pins']:
                n=v.get('net');expected[p['ref'],v['number']]=n if not n or n in globals_ else '/'+d['project']+'/'+n
    netlist=verify_netlist(out/'budget.net.xml',parts,expected)
    footprints=verify_footprints(fp,parts)
    run('sch','export','svg','--output',out/'svg',master)
    plots=sorted((out/'svg').glob('*.svg'));assert len(plots)==len(sheets)+1
    record=dict(schema=1,date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='B1 circuit draft; no fabrication or physical qualification',kicad_version=version,kicad_cli_sha256=sha(cli),
        source_sha256=hashes,erc=dict(violations=0,exclusions=0,sheets=len(erc['sheets']),default_ignored_checks=erc['ignored_checks'],sha256=sha(out/'erc.json')),
        netlist=dict(verified=True,**netlist,sha256=sha(out/'budget.net.xml')),footprints=footprints,
        svg_sha256={p.name:sha(p) for p in plots})
    record_path.write_text(json.dumps(record,indent=2)+'\n')
    print(f'PASS: B1 native ERC zero violations; {len(parts)} physical components / {netlist["connected_pins"]} connected pins verified')


if __name__=='__main__':main()
