from pathlib import Path
import os,json,subprocess,sys
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.netlists import netlist
R=Path('/private/tmp/afx-u11-restoration');P=R/'final-paired';cli='/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli';env=dict(os.environ,KICAD_CONFIG_HOME='/private/tmp/rmx-kicad-config',FONTCONFIG_FILE='/Users/axelmckrnna/dev/rmx-publish/build-hardware/kicad-fonts.conf');cmds=[]
for name,args in [('netlist',['sch','export','netlist','--format','kicadxml','--output',str(R/'final-netlist.xml')]),('erc',['sch','erc','--format','json','--output',str(R/'final-erc.json')])]:
 cmd=[cli,*args,str(P/'rail_disconnect.kicad_sch')];r=subprocess.run(cmd,env=env,capture_output=True,text=True);(R/f'final-{name}.log').write_text(r.stdout+r.stderr);cmds.append(dict(command=cmd,returncode=r.returncode));assert r.returncode==0
parts,pins=netlist(R/'final-netlist.xml');expected=json.load(open(P/'components.json'));m=[]
for p in expected:
 if parts[p['ref']].findtext('value')!=p['part']:m.append([p['ref'],'value'])
 for x in p['pins']:
  actual=pins[p['ref']][x['number']]
  if x['net'] is None:
   if not actual.startswith('unconnected-'):m.append([p['ref'],x['number'],actual])
  elif actual!=x['net']:m.append([p['ref'],x['number'],actual,x['net']])
erc=json.load(open(R/'final-erc.json'));v=[v for s in erc['sheets'] for v in s['violations']]
report=dict(native_parts=len(parts),component_pin_value_mismatches=m,ERC_findings=v,native_commands=cmds,physical_qualified=False)
(R/'final-schematic-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(report);assert not m and not v
