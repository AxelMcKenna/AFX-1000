import argparse,hashlib,json,math,re,importlib.util
from pathlib import Path
import numpy as np
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=importlib.util.spec_from_file_location('distance',H.parent/'r12_ground/verify.py');d=importlib.util.module_from_spec(sp);sp.loader.exec_module(d)
def verify(root):
 c=json.loads((H/'direct-exits.json').read_text());o=json.loads((H/'obstacle-sources.json').read_text());s=(root/o['root_sensor_source']).read_text();block=s[s.index('module cable_segment'):s.index('if(part==')]
 assert sha(root/o['root_sensor_source'])==o['root_sensor_sha256'] and hashlib.sha256(block.encode()).hexdigest()==o['exact_module_block_sha256']
 assert (H/'sensor-source-extract.scad').read_text().split('\n',1)[1]==block
 for n,h in c['source_sha256'].items():assert sha(R/n)==h,n
 owner=json.loads((H.parent/'r26_touch_mount/contract.json').read_text());assert owner['host']=='D_J1009'
 minsep=1e9;joins=[];sag=13*(1-math.cos(math.radians(1.5)))
 for i,e in enumerate(c['edges']):
  pts=np.array(e['points_mm']);assert e['source']=='D_J1009:'+str(i+1) and np.max(abs(pts[0]-[230+2.54*i,59,9.6]))<1e-8
  body=(H/'direct-exits.scad').read_text().split('module touch_exit_'+e['id']+'(){',1)[1].split('\n}',1)[0];modeled=np.array([json.loads(x) for x in re.findall(r'translate\((\[[^]]+\])\)',body)]);assert np.max(abs(modeled-np.array([x for a,b in zip(pts,pts[1:]) for x in [a,b]])))<1e-8
  cursor=0;last=None
  for p in e['primitives']:
   assert np.linalg.norm(pts[cursor]-p['start'])<1e-8
   if p['kind']=='line':
    T=np.array(p['end'])-pts[cursor];T/=np.linalg.norm(T);cursor+=1;endT=T;assert np.linalg.norm(pts[cursor]-p['end'])<1e-8
   else:
    assert p['kind']=='arc' and p['radius_mm']>=13
    T,N=np.array(p['tangent']),np.array(p['normal']);a=math.radians(p['angle_degrees']);count=math.ceil(p['angle_degrees']/3);angles=np.linspace(0,a,count+1);expected=pts[cursor]+13*np.sin(angles)[:,None]*T+13*(1-np.cos(angles))[:,None]*N;assert np.max(abs(pts[cursor:cursor+count+1]-expected))<1e-8;cursor+=count;endT=np.cos(a)*T+np.sin(a)*N
   if last is not None:joins.append(float(last@T));assert last@T>1-1e-9
   last=endT
  assert cursor==len(pts)-1 and pts[-1,0]==175
  for other in c['edges'][i+1:]:
   q=np.array(other['points_mm'])
   for a,b in zip(pts,pts[1:]):
    for x,y in zip(q,q[1:]):minsep=min(minsep,d.distance(a,b,x,y))
 assert minsep-1.3-2*sag>=.25, minsep
 records={}
 for case in ['sensor','population','controls','ground_supports','positive']:
  p=H/'native'/(case+'-r4')/'result.json';v=json.loads(p.read_text())
  for n,h in v['source_sha256'].items():assert sha(R/n)==h
  assert not v['runtime_failure']
  if case=='positive':assert v['mesh']['closed_oriented_boundary'] and mesh(p.parent/'positive.stl')==v['mesh']
  else:assert v['empty'] and not list(p.parent.glob('*.stl'))
  records[case]=dict(evidence=str(p.relative_to(R)),sha256=sha(p),artifact_sha256={str(q.relative_to(R)):sha(q) for q in p.parent.iterdir() if q.suffix in ['.log','.stl']})
 result=dict(minimum_mutual_wire_surface_gap_bound_mm=minsep-1.3-2*sag,minimum_radius_mm=13,minimum_join_dot=min(joins),wire_model_containment_margin_mm=.65*math.cos(math.pi/32)**2-sag-.6223,native=records,completed_touch_wires=0,completed_panel_edges=0,source_exit_only=True,termination_and_strain_relief_qualified=False,full_current_assembly_checked=False)
 assert result['wire_model_containment_margin_mm']>0
 (H/'direct-exits-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='native'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-repo',type=Path,required=True);a=p.parse_args();verify(a.source_repo)
