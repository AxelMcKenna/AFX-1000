"""Independent reference/quiet-copper geometry and native semantic evidence checks."""
import json,copy
from pathlib import Path
from shapely.geometry import Point,LineString
from ..routed.plan import shape,sha
from hardware.electronics.common.sexpr import read_sexpr,children
H=Path(__file__).resolve().parent;BASE=H.parent/'held_cutover/board-native-01';OUT=H/'native-02'
def geometry(plan,c,q):
 by={o['uuid']:o for o in c['objects']};quietids=set(q['retained_object_uuids']);qzones={x['zone_uuid'] for x in q['plane_exclusions']};new=[]
 for r in plan['routes']:
  assert r['source_pad_net']=='PWR_AGND';o=by[r['source_uuid']];assert o['net']=='PWR_AGND' and o['pin']==('4' if o['ref'].startswith('E_U') else '2')
  g=LineString(r['path_mm']).buffer(r['width_mm']/2);ref=shape(next(z['polygons'] for z in c['zones'] if z['uuid']==r['reference_zone_uuid']));assert g.difference(ref).area<1e-10
  assert shape(o['layers'][r['layer']]).covers(Point(r['path_mm'][0]));new.append((r['layer'],g))
  if 'target_uuid' in r:assert r['target_uuid'] not in quietids and shape(by[r['target_uuid']]['layers'][r['layer']]).covers(Point(r['path_mm'][-1]))
 for v in plan['new_vias']:
  for layer in c['copper_layers']:new.append((layer,Point(v['position_mm']).buffer(v['size_mm']/2)))
 for layer,g in new:
  for o in c['objects']:
   if o['uuid'] in quietids and layer in o['layers']:assert g.distance(shape(o['layers'][layer]))>=.199,'Retained quiet copper contact'
  for z in c['zones']:
   if z['uuid'] in qzones and z['layer']==layer:assert g.distance(shape(z['authored_outline']))>=.199,'Quiet plane outline crossed'
 return len(new)
def verify():
 p=json.loads((H/'plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());r=json.loads((OUT/'review.json').read_text())
 assert p['source_capture_sha256']==sha(H/'capture-01/capture.json') and p['planner_sha256']==sha(H/'plan.py');assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for key,path in [('source_sha256',BASE/'power_protection.kicad_pcb'),('candidate_sha256',OUT/'power_protection.kicad_pcb'),('script_sha256',H/'native.py'),('plan_sha256',H/'plan.json')]:assert r[key]==sha(path)
 geometry(p,c,q)
 assert r['opens_before']-r['opens_after']==len(p['routes'])==5 and r['native_groups_before']-r['native_groups_after']==5
 assert r['exact_declared_group_merges_only'] and r['all_original_pad_identities_unchanged'] and r['all_original_copper_unchanged'] and r['all_original_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 a,b=[read_sexpr((x/'power_protection.kicad_pcb').read_text()) for x in [BASE,OUT]];assert children(a,'zone')==children(b,'zone')
 old,new=[json.loads((x/'drc.json').read_text()) for x in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
 print('PASS: five declared main-ground joins, full reference coverage, no quiet-object/plane contacts, original copper and zones preserved; four unwaived DSE errors')
if __name__=='__main__':verify()
