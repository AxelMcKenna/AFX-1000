from pathlib import Path
import json,hashlib,shutil,subprocess,os
ROOT=Path('/private/tmp/afx-p03-strict-current');source=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/electronics/power_distribution/p03/candidates/aux-u10-combined');dest=ROOT/'strict-db83';dest.mkdir(exist_ok=True)
keys=['missing_courtyard','track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch','footprint_type_mismatch']
sourcehash={}
for p in source.iterdir():
 if p.is_file() and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym'] or p.name in ['components.json','component-selections.json','construction.json','fp-lib-table','sym-lib-table']):
  shutil.copy2(p,dest/p.name);sourcehash[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 elif p.is_dir() and p.suffix=='.pretty':shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
pro=dest/'power_p03.kicad_pro';j=json.load(open(pro));j['board']['design_settings'].setdefault('rule_severities',{}).update({k:'error' for k in keys});pro.write_text(json.dumps(j,indent=2)+'\n')
assert hashlib.sha256((dest/'power_p03.kicad_pcb').read_bytes()).hexdigest()==sourcehash['power_p03.kicad_pcb']
cmd=['/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--all-track-errors','--schematic-parity','--severity-all','--refill-zones','--format','json','--output',str(ROOT/'strict-drc.json'),str(dest/'power_p03.kicad_pcb')]
env=dict(os.environ,KICAD_CONFIG_HOME='/private/tmp/rmx-kicad-config',FONTCONFIG_FILE='/Users/axelmckrnna/dev/rmx-publish/build-hardware/kicad-fonts.conf')
r=subprocess.run(cmd,env=env,capture_output=True,text=True);(ROOT/'strict-drc.log').write_text(r.stdout+r.stderr)
report=dict(source=str(source),source_sha256=sourcehash,command=cmd,returncode=r.returncode,enabled_prior_ignored_checks=keys,
 source_PCB_geometry_unchanged=True,no_source_current_or_thermal_allocation_changes=True,profile_only_private_successor=True,physical_qualified=False)
(ROOT/'input.json').write_text(json.dumps(report,indent=2)+'\n')
for name,h in sourcehash.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h
assert hashlib.sha256((dest/'power_p03.kicad_pcb').read_bytes()).hexdigest()==sourcehash['power_p03.kicad_pcb']
print(r.stdout+r.stderr);print('sourcefilesunchanged',len(sourcehash))
