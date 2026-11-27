"""Fail closed on ownership, wire compatibility and curve reconstruction; never certify fit."""
import json,hashlib,math,re,importlib.util
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def validate(c,r):
 for n,h in c['source_sha256'].items():assert sha(R/n)==h,n
 lo,hi=c['wire_insulation_od_mm'];a,b=c['contact_insulation_od_mm'];assert a<=lo<=hi<=b
 assert c['contact_awg'][0]<=c['wire_awg']<=c['contact_awg'][1]
 # Explicitly reject general gauge/OD as proof of Molex hand-tool insulation support.
 assert hi<c['molex_handtool_24awg_recommended_od_mm'][0]
 assert not c['tooling_qualified'] and not c['physical_qualified']
 prior=json.loads((H.parent/'r27_touch_host/direct-exits.json').read_text())
 owner=json.loads((H.parent/'r26_touch_mount/contract.json').read_text());assert owner['host']=='D_J1009'
 assert len(r['edges'])==4
 joins=[];allpts=[]
 for i,(e,auth) in enumerate(zip(r['edges'],owner['wires'])):
  assert e['segments'][0]['primitives'][:len(prior['edges'][i]['primitives'])-1]==prior['edges'][i]['primitives'][:-1]
  assert e['host']=='D_J1009:'+auth['pin'] and e['net']==auth['net'] and e['trill_pin']==auth['trill_pin']
  assert np.max(abs(np.array(e['segments'][0]['points_mm'][0])-[*auth['native_xy_mm'],9.6]))<1e-8
  assert np.max(abs(np.array(e['segments'][1]['points_mm'][-1])-[*auth['trill_xy_mm'],22.25]))<1e-8
  modeled=[]
  for seg in e['segments']:
   pts=np.array(seg['points_mm']);allpts.append((i,pts));modeled.extend(x for a,b in zip(pts,pts[1:]) for x in [a,b]);cursor=0;last=None
   for p in seg['primitives']:
    assert np.linalg.norm(pts[cursor]-p['start'])<1e-8
    if p['kind']=='line':
     T=np.array(p['end'])-pts[cursor];T/=np.linalg.norm(T);cursor+=1;endT=T;assert np.linalg.norm(pts[cursor]-p['end'])<1e-8
    else:
     assert p['kind']=='arc' and p['radius_mm']>=13
     T,N=np.array(p['tangent']),np.array(p['normal']);assert abs(T@N)<1e-8 and abs(np.linalg.norm(T)-1)<1e-8 and abs(np.linalg.norm(N)-1)<1e-8
     a=math.radians(p['angle_degrees']);count=math.ceil(p['angle_degrees']/3);angles=np.linspace(0,a,count+1);expected=pts[cursor]+p['radius_mm']*np.sin(angles)[:,None]*T+p['radius_mm']*(1-np.cos(angles))[:,None]*N;assert np.max(abs(pts[cursor:cursor+count+1]-expected))<1e-8;cursor+=count;endT=np.cos(a)*T+np.sin(a)*N
    if last is not None:joins.append(float(last@T));assert last@T>1-1e-9
    last=endT
   assert cursor==len(pts)-1
  body=(H/'route-draft.scad').read_text().split('module touch_wire_'+e['id']+'(){',1)[1].split('\n}',1)[0];assert body.count('rotate([11,7,3])sphere(r=.65,$fn=32)')==len(modeled)
  actual=[json.loads(x) for x in re.findall(r'translate\((\[[^]]+\])\)',body)];assert np.max(abs(np.array(actual)-modeled))<1e-8
 assert .65*math.cos(math.pi/32)**2-13*(1-math.cos(math.radians(1.5)))-.6223>0
 return min(joins)
def main():
 c=json.loads((H/'parts-study.json').read_text());r=json.loads((H/'route-draft.json').read_text());dot=validate(c,r)
 mutations=[]
 for kind in ['wrong_port','wrong_net','wire_tolerance','tooling_claim']:
  cc=json.loads(json.dumps(c));rr=json.loads(json.dumps(r))
  if kind=='wrong_port':rr['edges'][0]['host']='D_J1010:1'
  if kind=='wrong_net':rr['edges'][0]['net']='LINK_V3V3_IO'
  if kind=='wire_tolerance':cc['wire_insulation_od_mm'][0]=.99
  if kind=='tooling_claim':cc['tooling_qualified']=True
  try:validate(cc,rr)
  except AssertionError:mutations.append(kind)
  else:raise AssertionError(kind)
 result={'status':'ANALYTIC_STUDY_ONLY','minimum_join_dot':dot,'radius_mm':13,'mutations_rejected':mutations,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'parts-study.json',H/'route-draft.json',H/'route-draft.scad',H/'build_draft.py']},'full_assembly_checked':False,'minimum_wire_separation_bound_verified':False,'physical_qualified':False,'completed_touch_wires':0,'completed_panel_edges':0}
 (H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
