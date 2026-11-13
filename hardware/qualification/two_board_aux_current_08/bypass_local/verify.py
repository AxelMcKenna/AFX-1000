"""Verify local bypass geometry, explicit native deltas and unresolved process gates."""
import json,math
from pathlib import Path
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
from ..routed.plan import sha,shape
from ..held_loops.verify import geometry
from hardware.electronics.common.sexpr import read_sexpr,children,first
H=Path(__file__).resolve().parent

def local_geometry(plan,c,q):
 by={(o['ref'],o['pin']):o for o in c['objects'] if o.get('ref')};quietids=set(q['retained_object_uuids']);qzones={r['zone_uuid'] for r in q['plane_exclusions']};reference=shape(next(z['polygons'] for z in c['zones'] if z['uuid']=='13cfea4d-d36e-5757-b531-ed680e4c4562'))
 for row in plan['rows']:
  r=row['chosen']
  if not r:continue
  assert by[r['driver'],'4']['net']=='PWR_AGND' and by[r['driver'],'2']['net'].endswith('_TT')
  pads={p:translate(rotate(box(x-.5,-.725,x+.5,.725),-r['orientation_degrees'],origin=(0,0)),*r['position_mm']) for p,x in [('1',-.95),('2',.95)]};new=[]
  for kind,pin in [('supply','1'),('ground','2')]:
   path=r[kind+'_path_mm'];g=LineString(path).buffer(.15);assert pads[pin].buffer(1e-10).covers(Point(path[0]));assert g.difference(reference).area<1e-10;new.append(('F.Cu',g))
  assert shape(by[r['driver'],'1']['layers']['F.Cu']).buffer(1e-10).covers(Point(r['supply_path_mm'][-1]))
  if r['new_ground_via']:
   v=r['new_ground_via'];assert math.dist(v['position_mm'],r['ground_path_mm'][-1])<1e-9
   new.extend((l,Point(v['position_mm']).buffer(.3)) for l in c['copper_layers'])
  for l,g in new:
   for o in c['objects']:
    if o['uuid'] in quietids and l in o['layers']:assert g.distance(shape(o['layers'][l]))>=.199
   for z in c['zones']:
    if z['uuid'] in qzones and z['layer']==l:assert g.distance(shape(z['authored_outline']))>=.199

def verify():
 c=json.loads((H/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());p=json.loads((H/'plan.json').read_text());cp=json.loads((H/'c36-return.json').read_text())
 assert p['source_capture_sha256']==cp['source_capture_sha256']==sha(H/'capture-01/capture.json');assert p['planner_sha256']==sha(H/'plan.py') and cp['planner_sha256']==sha(H/'c36_return.py');assert p['courtyards_sha256']==sha(H/'courtyards.json');local_geometry(p,c,q);geometry(cp,c,q)
 for name,baseline,script,plan,delta in [('native-02',H.parent/'held_loops/native-02','native.py','plan.json',1),('native-03',H/'native-02','c36_native.py','c36-return.json',1)]:
  out=H/name;r=json.loads((out/'review.json').read_text())
  for key,path in [('source_sha256',baseline/'power_protection.kicad_pcb'),('candidate_sha256',out/'power_protection.kicad_pcb'),('script_sha256',H/script),('plan_sha256',H/plan)]:assert r[key]==sha(path)
  assert r['opens_before']-r['opens_after']==delta and r['anonymous_identity_bijection_preserved']==55 and r['all_original_fills_unchanged']
  old,new=[json.loads((x/'drc.json').read_text()) for x in [baseline,out]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
  for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (baseline/n).read_bytes()==(out/n).read_bytes()
  a,b=[read_sexpr((x/'power_protection.kicad_pcb').read_text()) for x in [baseline,out]];assert children(a,'zone')==children(b,'zone')
  if name=='native-02':
   assert r['exact_declared_group_changes_only'] and r['all_other_original_pad_identities_unchanged'] and r['all_other_original_copper_unchanged']
   chosen=next(x['chosen'] for x in p['rows'] if x['capacitor']=='E_C13');fp=next(f for f in children(b,'footprint') if any(x[1]=='Reference' and x[2]=='E_C13' for x in children(f,'property')));assert list(map(float,first(fp,'at')[1:]))==chosen['position_mm']+[chosen['orientation_degrees']]
  else:assert r['exact_declared_group_merges_only'] and r['all_original_pad_identities_unchanged'] and r['all_original_copper_unchanged']
 print('PASS: relocated U4 bypass and C36 return; exact native semantic deltas; quiet/reference preservation; four DSE errors unwaived')
if __name__=='__main__':verify()
