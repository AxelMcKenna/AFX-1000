"""Fail closed on source drift, allocation drift and missing native evidence."""
import json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 c=json.loads((H/'contract.json').read_text())
 for n,s in c['source_sha256'].items():assert sha(R/n)==s,n
 r=json.loads((R/'hardware/cad/a12/trill_mount_candidate/report.json').read_text())
 assert len(c['components'])==13 and len(c['tails'])==36
 for old,new in zip(r['component_terminal_reserves'],c['components']):
  b=old['box_mm'].copy();b[1]+=34.5;b[2]-=10.6
  assert new==dict(id=old['id'],box_mm=b)
 assert not c['mount']['fastener_selected'] and not c['physical_qualified']
 rows={}
 for case in ['positive','posts_components','heads_components','posts_board','old_box_witness']:
  p=H/'native'/(case+'-r1')/'result.json';v=json.loads(p.read_text())
  for n,s in v['source_sha256'].items():assert sha(R/n)==s,n
  assert not v['runtime_failure']
  if case in ['posts_components','heads_components']:assert v['empty']
  elif case=='posts_board':assert v['mesh']['volume_mm3']==0 and v['mesh']['min_mm'][2]==v['mesh']['max_mm'][2]==20
  else:assert v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0
  rows[case]=dict(evidence=str(p.relative_to(R)),sha256=sha(p),empty=v['empty'],mesh=v['mesh'])
 out=dict(native=rows,local_allocations_clear=True,raw_seat_plane_retained=True,full_current_assembly_checked=False,fastener_selected=False,physical_qualified=False)
 (H/'verification.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':verify()
