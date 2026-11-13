"""Require source-bound connected fill bridge without changing any old object/group."""
import json,copy
from pathlib import Path
from shapely.ops import unary_union
from ..routed.plan import sha,shape
from ..held_cell.verify_local import nmshape
from ..held_cell.verify_plane import library_link
from ..held_cell.preflight import zone_coordinates
from hardware.electronics.common.sexpr import read_sexpr,children,first
H=Path(__file__).resolve().parent;BASE=H.parent/'distribution/native-01';OUT=H/'native-01'
def physical_bridge(c,p,g):
 z={x['uuid']:x for x in c['zones']};main=shape(z[p['main_source_zone_uuid']]['polygons']);other=shape(z[p['other_main_zone_uuid']]['polygons']);assert g.geom_type=='Polygon' and g.intersection(main).area>1 and g.intersection(other).area>1,'Filled extension must physically contact both reference regions';assert g.difference(shape([{'outer':p['outline_mm']}])).area<1e-9
 contacts=[]
 for o in c['objects']:
  if o['net']=='PWR_AGND' and 'In6.Cu' in o['layers'] and other.intersects(shape(o['layers']['In6.Cu'])):
   assert o['group']==p['main_group_uuid'];contacts.append({'uuid':o['uuid'],'kind':o['kind'],'group':o['group'],'contact_area_mm2':other.intersection(shape(o['layers']['In6.Cu'])).area})
 assert contacts==p['other_main_zone_contacts'] and len(contacts)==13 and all(x['contact_area_mm2']>0 for x in contacts)
 q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());assert sha(H.parent/'routed/quiet-exclusion.json')==p['quiet_exclusions_sha256'];ids=set(q['retained_object_uuids']);zs={x['zone_uuid'] for x in q['plane_exclusions']};assert p['other_main_zone_uuid'] not in zs
 for o in c['objects']:
  if o['uuid'] in ids and 'In6.Cu' in o['layers']:assert g.distance(shape(o['layers']['In6.Cu']))>=.199
 for z in c['zones']:
  if z['uuid'] in zs and z['layer']=='In6.Cu':assert g.distance(shape(z['authored_outline']))>=.199
 return g.intersection(main).area,g.intersection(other).area

def verify():
 p=json.loads((H/'plan.json').read_text());r=json.loads((OUT/'review.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());gd=json.loads((OUT/'new-zone-geometry.json').read_text());assert p['capture_sha256']==sha(H/'capture-01/capture.json');assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for k,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('plan_sha256',H/'plan.json'),('script_sha256',H/'native.py'),('adapter_sha256',H.parent/'held_cell/process_adapter.py'),('full_refill_sha256',OUT/'full-refill.kicad_pcb'),('geometry_sha256',OUT/'new-zone-geometry.json')]:assert r[k]==sha(path)
 assert p['builder_sha256']==sha(H/'build.py') and p['authored_board_sha256']==sha(H/'authored-01/power_protection.kicad_pcb');assert r['all_original_groups_unchanged'] and r['all_original_objects_unchanged'] and r['all_original_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==r['opens_after']==1945
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];zs=children(b,'zone');added=[z for z in zs if first(z,'uuid')[1]==p['new_zone_uuid']];assert len(added)==1 and len(zs)==49 and len(children(a,'zone'))==48;assert [x for x in b if x is not added[0]]==a;assert zone_coordinates(added[0])==[p['outline_mm']] and int(first(added[0],'priority')[1])==2
 assert gd['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb') and gd['zone_uuid']==p['new_zone_uuid'];g=nmshape(gd['polygons_nm']);overlap,other=physical_bridge(c,p,g)
 old,new=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
 for name in ['refill-process','final-drc-process']:
  rr=json.loads((OUT/name/'process.json').read_text());assert rr['status']=='passed' and all(rr['inputs_unchanged'].values())
  for n in ['stdout.log','stderr.log']:assert rr[n+'_sha256']==sha(OUT/name/n)
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 return {'main_fill_overlap_mm2':overlap,'other_main_fill_overlap_mm2':other,'new_fill_area_mm2':g.area,'unchanged_zones':48,'original_groups_unchanged':r['original_group_count'],'source_main_contacts':13,'opens':1945,'unwaived_DSE_errors':4,'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
