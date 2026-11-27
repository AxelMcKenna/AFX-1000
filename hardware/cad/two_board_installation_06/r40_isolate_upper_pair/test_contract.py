"""Reject terminal identity, electrical net, sampled endpoint and bend mutations."""
import copy,hashlib,json,runpy
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;R=H.parents[3]
route=H/'routes.json';original_read=Path.read_text;original=json.loads(route.read_text());rejected=[]
for mutation in ['wrong_cavity','wrong_net','moved_terminal','tight_bend','changed_source_tangent','undersized_clearance_probe','coarse_clearance_probe','missing_segment_hull','wrong_receiving_radius']:
 changed=copy.deepcopy(original);edge=changed['edges'][0]
 if mutation=='wrong_receiving_radius':changed['wire_radius_mm']=.5
 if mutation=='wrong_cavity':edge['source']='D_J2002:8'
 if mutation=='wrong_net':edge['net']='/D_CONTROLS/CONTROL_24'
 if mutation=='moved_terminal':edge['points_mm'][-1][0]+=.2
 if mutation=='tight_bend':next(p for p in edge['primitives'] if p['kind']=='arc')['radius_mm']=11.9
 if mutation=='changed_source_tangent':next(p for p in edge['primitives'] if p['kind']=='arc')['tangent'][0]+=.01
 def read(path,*args,**kwargs):
  if path.resolve()==route.resolve():return json.dumps(changed)
  value=original_read(path,*args,**kwargs)
  if path.resolve()==(H/'clearance.scad').resolve():
   if mutation=='undersized_clearance_probe':value=value.replace('r=.863','r=.853')
   if mutation=='coarse_clearance_probe':value=value.replace('$fn=32','$fn=24')
   if mutation=='missing_segment_hull':value=value.replace('hull(){','union(){',1)
  return value
 with patch.object(Path,'read_text',read):
  try:runpy.run_path(str(H/'verify.py'),run_name='__main__')
  except AssertionError:rejected.append(mutation)
  else:raise AssertionError('Invalid candidate accepted: '+mutation)
report={'rejected':rejected,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),route,H/'verify.py',H/'clearance.scad']}}
(H/'mutation-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rejected))
