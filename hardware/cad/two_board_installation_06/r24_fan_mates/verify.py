"""Verify frozen-cell ownership, six exact entries and conditional native witnesses."""
import argparse,json,hashlib,re,math
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=H.parents[3];B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,required=True);a=p.parse_args();c=json.loads((H/'contract.json').read_text());assert sha(a.pcb)==c['native_pcb']['sha256']
 for f,s in c['source_sha256'].items():assert sha(R/f)==s,f
 assert c['conditional_only'] and not c['dimensionally_qualified'] and not c['fabrication_released'] and not c['route_changed']
 assert c['primary']['body_maximum_or_tolerances_available'] is False
 for row in c['headers']:
  old,new=row['captured_box'],row['conditional_receiving_box'];assert old[:5]==new[:5] and new[5]==20<old[5]
 oldsc=(B/'r7/fan_harness.scad').read_text();newsc=(H/'harness.scad').read_text();cells=0
 for i,t in enumerate(c['fanout_transition']):
  points=json.loads(re.search('tbh06_points_'+str(i)+r'=(\[.*?\]);',oldsc).group(1));n=t['retained_original_segment_count'];assert n==math.ceil(t['fanout_start_parameter']*160) and n/160>=t['fanout_start_parameter']
  body=newsc.split('module fan_prefix_'+str(i)+'(){',1)[1].split('\n',1)[0];coords=[json.loads(q) for q in re.findall(r'translate\((\[[^]]+\])\)',body)];assert coords==[p for a,b in zip(points[:n],points[1:n+1]) for p in [a,b]]
  assert body.count('sphere(r=2.56,$fn=24)')==2*n;cells+=n
  assert len(t['strands'])==3 and all(q['tangent_dot']>1-1e-8 and q['complete_start_sphere_containment_margin_mm']>0 for q in t['strands'])
 assert 'module reconciled_fan_harness(){retained_fan_bundle();tbh08_terminal_wires();}' in newsc
 masks=(H/'mates.scad').read_text().split('module fan_entry_masks(){',1)[1];coords=[json.loads(q) for q in re.findall(r'translate\((\[[^]]+\])\)',masks)];assert coords==[p['xy_mm']+[18.3] for h in c['headers'] for p in h['pads']]
 assert masks.count('cylinder(r=.98,h=1.70001,$fn=64)')==6
 checks={}
 for name in ['scoped_corrected','start_containment','prefix_subset','wrongmask_corrected','positive_corrected','positive','unmasked_corrected']:
  f=H/'native'/(name+'-r2')/'result.json';v=json.loads(f.read_text());assert not v['runtime_failure']
  for src,s in v['source_sha256'].items():assert sha(R/src)==s,src
  if name in ['scoped_corrected','start_containment']:assert v['empty'];status='PASS'
  elif name=='prefix_subset':
   # Coincident face residual is not a watertight collision, nor an empty native pass.
   assert not v['empty'] and not v['mesh']['closed_oriented_boundary'];status='NONCLOSED_COINCIDENT_DIAGNOSTIC; exact cell inclusion is independent proof'
  else:assert not v['empty'] and v['mesh']['closed_oriented_boundary'] and v['mesh']['volume_mm3']>0;status='POSITIVE_WITNESS'
  checks[name]=dict(status=status,evidence=str(f.relative_to(R)),sha256=sha(f))
 report=dict(source_sha256={str(p.relative_to(R)):sha(p) for p in [H/'contract.json',H/'mates.scad',H/'harness.scad',Path(__file__)]},retained_cells_exactly_match_frozen_cells=cells,unchanged_individual_wire_paths=6,native=checks,conditional_receiving_height_only=True,actual_assembled_maximum_and_entry_axis_registration_qualified=False,full_current_assembly_checked=False,fabrication_released=False)
 (H/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
