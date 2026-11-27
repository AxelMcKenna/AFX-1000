import argparse,hashlib,json,tempfile
from pathlib import Path
from .build import build
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(source_repo):
 c=json.loads((H/'contract.json').read_text())
 for n,s in c['source_sha256'].items():
  p=R/n
  if not p.exists():p=source_repo/n
  assert sha(p)==s,n
 assert c['host']=='D_J1009' and len(c['wires'])==4
 s=c['stack_mm'];assert abs(s['tip_min']-1.23)<1e-9 and abs(s['tip_max']-2.57)<1e-9
 assert abs(s['end_protrusion_min']-.53)<1e-9 and abs(s['full_thread_beyond_nut_min']-.13)<1e-9
 assert s['old_pocket_min_end_protrusion']<0
 assert not c['physical_qualified'] and not c['host_mate_selected']
 pcb=source_repo/next(n for n in c['source_sha256'] if n.endswith('.kicad_pcb'));net=source_repo/next(n for n in c['source_sha256'] if n.endswith('netlist.xml'))
 mutations={}
 for label,host in [('net_identical_wrong_port','D_J1010')]:
  try:build(pcb,net,host)
  except AssertionError:mutations[label]='REJECTED'
  else:raise AssertionError(label)
 rows={}
 for case in ['positive','revised_posts','upper_components','hardware_components','raw_hardware_posts','removed_material']:
  p=H/'native'/(case+'-r1')/'result.json';v=json.loads(p.read_text())
  for n,h in v['source_sha256'].items():assert sha(R/n)==h
  assert not v['runtime_failure']
  stl=p.parent/(case+'.stl')
  if v['empty']:assert not stl.exists()
  else:assert mesh(stl)==v['mesh'],case
  if case in ['upper_components','hardware_components']:assert v['empty']
  elif case in ['positive','revised_posts']:assert v['mesh']['closed_oriented_boundary']
  elif case=='raw_hardware_posts':assert v['mesh']['volume_mm3']<1e-10 and v['mesh']['min_mm'][2]==v['mesh']['max_mm'][2]
  rows[case]=dict(artifact_sha256={str(q.relative_to(R)):sha(q) for q in p.parent.iterdir() if q.suffix in ['.log','.stl']},evidence=str(p.relative_to(R)),sha256=sha(p),empty=v['empty'],mesh=v['mesh'])
 out=dict(native=rows,mutation_tests=mutations,dimensional_stack_pass_under_receiving_requirements=True,full_assembly_checked=False,raw_contacts_not_empty=True,removed_material_diagnostic_nonclosed=True,physical_qualified=False)
 (H/'verification.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-repo',type=Path,required=True);a=p.parse_args();verify(a.source_repo.resolve())
