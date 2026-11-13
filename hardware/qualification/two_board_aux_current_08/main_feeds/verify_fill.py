"""Accept only explicitly bounded native B.Cu cutbacks, never unrelated refill drift."""
import json
from pathlib import Path
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
from ..held_cell.verify_plane import library_link
from .verify import verify as verify_route,nmshape,H
from .routing_zones import obstacles
BASE=H/'native-01';OUT=H/'native-02'
def evaluate_delta(old,new,allowed):
 added=new.difference(old).area;removed=old.difference(new);outside=removed.difference(allowed).area
 return {'added_mm2':added,'removed_mm2':removed.area,'removed_outside_declared_clearance_mm2':outside,'remaining_area_mm2':new.area,'old_area_mm2':old.area,'old_components':len(old.geoms) if hasattr(old,'geoms') else 1,'new_components':len(new.geoms) if hasattr(new,'geoms') else 1}
def verify():
 route=verify_route(allow_rejected_drc=True);r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'fill-plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());g=json.loads((BASE/'added-copper-geometry.json').read_text());newgeo=json.loads((OUT/'changed-zone-geometry.json').read_text());assert p['routed_board_sha256']==sha(BASE/'power_protection.kicad_pcb') and p['rejected_drc_sha256']==sha(BASE/'drc.json') and p['route_plan_sha256']==sha(H/'plan.json')
 for k,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('fill_plan_sha256',H/'fill-plan.json'),('script_sha256',H/'native_fill.py'),('full_refill_sha256',OUT/'full-refill.kicad_pcb'),('changed_geometry_sha256',OUT/'changed-zone-geometry.json')]:assert r[k]==sha(path)
 assert r['all_groups_unchanged_from_routed_candidate'] and r['all_copper_objects_and_pad_identities_unchanged'] and r['opens_before']==r['opens_after']==1944
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];az={first(z,'uuid')[1]:z for z in children(a,'zone')};bz={first(z,'uuid')[1]:z for z in children(b,'zone')};assert set(az)==set(bz) and len(az)==49
 assert [x for x in a if not isinstance(x,list) or x[0]!='zone']==[x for x in b if not isinstance(x,list) or x[0]!='zone']
 for uid in az:
  if uid not in p['cutback_zone_uuids']:assert az[uid]==bz[uid]
  else:assert [x for x in az[uid] if not isinstance(x,list) or x[0]!='filled_polygon']==[x for x in bz[uid] if not isinstance(x,list) or x[0]!='filled_polygon']
 assert newgeo['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');oldz={z['uuid']:z for z in c['zones']};q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet={x['zone_uuid'] for x in q['plane_exclusions']};assert not(set(p['cutback_zone_uuids'])&quiet);deltas=[]
 for z in newgeo['zones']:
  assert z['uuid'] in p['cutback_zone_uuids'] and z['layer']=='B.Cu';old=shape(oldz[z['uuid']]['polygons']);new=nmshape(z['polygons_nm']);copper=unary_union([nmshape(o['layers_nm']['B.Cu']) for o in g['objects'] if 'B.Cu' in o['layers_nm'] and o['net']!=z['net']]);allowed=copper.buffer(.202);d=evaluate_delta(old,new,allowed);d.update(zone_uuid=z['uuid'],net=z['net']);deltas.append(d)
 (H/'cutback-delta.json').write_text(json.dumps({'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'deltas':deltas},indent=2)+'\n')
 assert len(deltas)==2 and all(d['added_mm2']<1e-9 and d['removed_outside_declared_clearance_mm2']<1e-9 for d in deltas),'Native refill exceeds local removal-only clearance permission; inspect cutback-delta.json'
 for o in g['objects']:
  if o['kind']=='PCB_TRACK':assert nmshape(o['layers_nm']['B.Cu']).intersection(obstacles(c['zones'],'B.Cu',o['net'],0,p['cutback_zone_uuids'])).area<1e-9
 oldrc=json.loads((H.parent/'precision/native-01/drc.json').read_text());drc=json.loads((OUT/'drc.json').read_text());key=lambda x:json.dumps(x,sort_keys=True);assert sorted(oldrc['violations'],key=key)==sorted(drc['violations'],key=key) and len(drc['violations'])==4
 for name in ['refill-process','drc-process']:
  d=OUT/name;rr=json.loads((d/'process.json').read_text());assert rr['status']=='passed' and all(rr['inputs_unchanged'].values())
  for log in ['stdout.log','stderr.log']:assert rr[log+'_sha256']==sha(d/log)
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 return {'opens':1944,'declared_cutback_zones':2,'unchanged_other_zones':47,'deltas':deltas,'unwaived_DSE_errors':4,'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
