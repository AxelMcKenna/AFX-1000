#!/usr/bin/env python3
"""Run native KiCad ERC/export and verify every modeled physical pin/net.

--check needs no KiCad installation: it rejects evidence from different design
inputs. Passing is circuit-draft evidence, never PCB or bench qualification.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from generate_carrier import all_sheets, project_artifacts

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'hardware/electrical'
RECORD = DEST / 'native-check.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def design():
    sheets = [json.loads((DEST/'bypass.json').read_text()), *all_sheets()]
    sheets[0]['project'] = 'bypass-permission'
    parts = {p['ref']:p for s in sheets for p in s['components'] if not p.get('virtual')}
    globals_ = {v['net'] for s in sheets for p in s['components'] if p['ref'].startswith('J')
                for v in p['pins'] if v.get('net')}
    expected = {}
    for s in sheets:
        for p in s['components']:
            if p.get('virtual'):
                continue
            for v in p['pins']:
                net = v.get('net')
                if net and net not in globals_:
                    net = '/' + s['project'] + '/' + net
                expected[(p['ref'],v['number'])] = net
    inputs = {DEST/name for name in project_artifacts(all_sheets())}
    inputs.update(DEST/(s['project']+'.kicad_sch') for s in sheets)
    inputs.update(DEST/(s['project']+'.json') for s in sheets[1:])
    inputs.update([DEST/'bypass.json',ROOT/'hardware/prototype.json',
                   ROOT/'tools/generate_carrier.py',ROOT/'tools/generate_bypass.py',
                   Path(__file__).resolve()])
    fingerprint = {str(p.relative_to(ROOT)):sha(p) for p in sorted(inputs)}
    return sheets, parts, expected, fingerprint


def verify_netlist(path, parts, expected):
    root = ET.parse(path).getroot()
    components = root.findall('./components/comp')
    refs = [p.get('ref') for p in components]
    if len(refs) != len(set(refs)) or set(refs) != set(parts):
        raise ValueError('Native export dropped, duplicated or added physical components')
    for p in components:
        wanted = parts[p.get('ref')]
        if p.findtext('value') != wanted['value'] or (p.findtext('footprint') or '') != wanted.get('footprint',''):
            raise ValueError('Native component fields differ: '+p.get('ref'))
    actual = {}
    for net in root.findall('./nets/net'):
        name = net.get('name')
        for node in net.findall('node'):
            key = (node.get('ref'),node.get('pin'))
            if key in actual:
                raise ValueError('Pin occurs on multiple native nets: '+str(key))
            if key not in expected:
                raise ValueError('Unexpected native pin: '+str(key))
            # KiCad emits each explicit NC as a separate unconnected-(...) net.
            if expected[key] is None:
                if not name.startswith('unconnected-('):
                    raise ValueError('NC pin became connected: '+str(key))
            elif name != expected[key]:
                raise ValueError(f'Wrong native net at {key}: {name!r}, expected {expected[key]!r}')
            actual[key] = name
    absent = {k for k,v in expected.items() if v is not None and k not in actual}
    if absent:
        raise ValueError('Native export omitted connected pins: '+str(sorted(absent)))
    canonical = json.dumps(sorted((r,p,n) for (r,p),n in expected.items()),separators=(',',':'))
    return dict(physical_components=len(parts), connected_pins=sum(v is not None for v in expected.values()),
                explicit_nc_pins=sum(v is None for v in expected.values()),
                connectivity_sha256=hashlib.sha256(canonical.encode()).hexdigest())


def verify_footprints(directory, parts):
    """Pad-number agreement only; dimensions/orientation still need review."""
    libraries = {}
    assigned = 0
    for ref,part in parts.items():
        name = part.get('footprint')
        if not name:
            continue
        if name not in libraries:
            lib,footprint = name.split(':')
            path = directory/(lib+'.pretty')/(footprint+'.kicad_mod')
            text = path.read_text()
            pads = set(re.findall(r'\(pad\s+"([^"\n]*)"',text))-{''}
            libraries[name] = dict(pads=pads,sha256=sha(path))
        if libraries[name]['pads'] != {p['number'] for p in part['pins']}:
            raise ValueError('Symbol pin numbers differ from selected footprint pads: '+ref)
        assigned += 1
    return dict(assigned_components=assigned,unassigned_components=len(parts)-assigned,
                footprint_sha256={n:p['sha256'] for n,p in sorted(libraries.items())},
                scope='Pad-number agreement only; no manufacturer geometry, orientation or clearance approval')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--cli',type=Path,default=shutil.which('kicad-cli'))
    parser.add_argument('--footprints',type=Path,help='Directory containing KiCad .pretty libraries')
    parser.add_argument('--output',type=Path,default=ROOT/'build/hardware/native')
    args = parser.parse_args()
    for generator in ['generate_bypass.py','generate_carrier.py']:
        subprocess.run([sys.executable,str(ROOT/'tools'/generator),'--check'],check=True)
    sheets,parts,expected,fingerprint = design()
    if args.check:
        record = json.loads(RECORD.read_text())
        if record['source_sha256'] != fingerprint:
            raise ValueError('Native KiCad record is stale: rerun check_carrier.py with KiCad')
        if record['erc']['violations'] != 0 or record['erc']['exclusions'] != 0:
            raise ValueError('Recorded native ERC is not clean')
        if not record['netlist']['verified']:
            raise ValueError('Native netlist was not verified')
        print('PASS: native KiCad ERC/netlist record matches current circuit sources (not PCB/bench qualification)')
        return
    if not args.cli or not args.cli.is_file():
        raise ValueError('Provide an installed KiCad 10 kicad-cli using --cli')
    cli = args.cli.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ,KICAD_CONFIG_HOME=str(out/'config'),XDG_CACHE_HOME=str(out/'cache'))
    footprints = args.footprints
    if footprints is None:
        bundled = cli.parents[1]/'SharedSupport/footprints'
        if bundled.is_dir():
            footprints = bundled
    if footprints:
        env['KICAD10_FOOTPRINT_DIR'] = str(footprints.resolve())
    else:
        configured = env.get('KICAD10_FOOTPRINT_DIR')
        if not configured:
            raise ValueError('Provide the KiCad 10 footprint directory using --footprints')
        footprints = Path(configured)
    if sys.platform == 'darwin':
        # Use a writable task-local font cache without changing system settings.
        fontconf = out/'fonts.conf'
        fontconf.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'
            '<dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir>'
            '<cachedir>'+str(out/'font-cache')+'</cachedir></fontconfig>')
        env['FONTCONFIG_FILE'] = str(fontconf)

    def run(*arguments):
        result = subprocess.run([str(cli),*map(str,arguments)],env=env,capture_output=True,text=True,check=True)
        output = result.stdout+result.stderr
        if 'warning:' in output.lower() or 'error:' in output.lower():
            raise ValueError('Native KiCad diagnostic:\n'+output)
        return result.stdout.strip()

    version = run('version')
    if not version.startswith('10.'):
        raise ValueError('This project library table targets KiCad 10; got '+version)
    erc_path = out/'erc.json'
    master = DEST/'carrier.kicad_sch'
    run('sch','erc','--severity-all','--format','json','--exit-code-violations','-o',erc_path,master)
    erc = json.loads(erc_path.read_text())
    violations = [v for s in erc['sheets'] for v in s['violations']]
    if violations or len(erc['sheets']) != len(sheets)+1:
        raise ValueError('Native ERC did not check all ten pages cleanly')
    net_path = out/'carrier.net.xml'
    run('sch','export','netlist','--format','kicadxml','-o',net_path,master)
    netlist = verify_netlist(net_path,parts,expected)
    footprint_result = verify_footprints(footprints,parts)
    run('sch','export','svg','--output',out/'svg',master)
    plots = sorted((out/'svg').glob('*.svg'))
    if len(plots) != len(sheets)+1:
        raise ValueError('Native plot export omitted pages')
    record = dict(schema=1,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='Native schematic checks only; not fabrication or physical qualification',
        kicad_version=version,kicad_cli_sha256=sha(cli),source_sha256=fingerprint,
        erc=dict(violations=0,exclusions=0,sheets=len(erc['sheets']),
                 default_ignored_checks=erc['ignored_checks'],report_sha256=sha(erc_path)),
        netlist=dict(verified=True,**netlist,export_sha256=sha(net_path)),
        footprints=footprint_result,
        svg_pages=len(plots),svg_sha256={p.name:sha(p) for p in plots})
    RECORD.write_text(json.dumps(record,indent=2)+'\n')
    print(f'PASS: KiCad {version}; zero ERC violations; {len(parts)} physical components and '
          f'{netlist["connected_pins"]} connected pins verified in native netlist; ten SVG pages exported')


if __name__ == '__main__':
    main()
