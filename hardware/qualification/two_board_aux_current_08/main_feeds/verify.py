"""Validate actual native local copper, exact circuit links and preserved references."""
import json,math
from pathlib import Path
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
from ..held_cell.verify_plane import library_link
H=Path(__file__).resolve().parent;BASE=H.parent/'precision/native-01';OUT=H/'native-01'
def semantic(plan,capture):
 by={o['ref']+'.'+o['pin']:o for o in capture['objects'] if o.get('ref')};by.update({'uuid:'+o['uuid']:o for o in capture['objects']})
 assert len(plan['routes'])==1 and len(plan['failures'])==1 and len(plan['new_vias'])==1
 r=plan['routes'][0];assert (r['source'],r['target'],r['net'],r['layer'],r['width_mm'])==('uuid:d8d0a2da-8282-55cf-ab1d-284a22e44b2c','P_C900.1','/P_power_supply/VIN_IC','B.Cu',.3)
 assert by[r['source']]['net']==by[r['target']]['net']==r['net'];assert r['path_mm'][0]==by[r['source']]['position_mm']
 assert plan['new_vias']==[{'name':'VIN_return','position_mm':[194.,117.6],'size_mm':.6,'drill_mm':.3,'net':'PWR_AGND'}]
 return by
def nmshape(polys):return unary_union([Polygon([[x/1e6,y/1e6] for x,y in p['outer']],[[[x/1e6,y/1e6] for x,y in hole] for hole in p['holes']]) for p in polys])
def transition_check(p,c,reference):
 t=p['transition'];by={o['uuid']:o for o in c['objects']};source=by[t['source_via_uuid']];assert source['kind']=='PCB_VIA' and source['net']=='/P_power_supply/VIN_IC' and source['position_mm']==[193.2,117.8] and source['width_mm']==.6 and source['drill_mm']==.3 and source['group']==t['source_group'];hole=Polygon(t['allowed_antipad_polygon_mm']);actual=[Polygon(ring) for part in (reference.geoms if hasattr(reference,'geoms') else [reference]) for ring in part.interiors if Polygon(ring).covers(Point(source['position_mm']))];assert len(actual)==1 and hole.equals(actual[0]) and hole.area<.81
 foreign=[o['uuid'] for o in c['objects'] if o['net']!='PWR_AGND' and 'In6.Cu' in o['layers'] and hole.intersection(shape(o['layers']['In6.Cu'])).area>1e-9];assert foreign==t['antipad_foreign_object_uuids']==[source['uuid']]
 assert t['return_position_mm']==p['new_vias'][0]['position_mm'] and abs(math.dist(source['position_mm'],t['return_position_mm'])-t['return_pair_distance_mm'])<1e-9 and t['return_pair_distance_mm']<1
 q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());assert t['quiet_exclusions_sha256']==sha(H.parent/'routed/quiet-exclusion.json');quiet={z['zone_uuid'] for z in q['plane_exclusions']};refs={}
 for l,zids in t['return_reference_zone_uuids'].items():
  assert l in ['In1.Cu','In6.Cu'] and zids and not(set(zids)&quiet);zs=[z for z in c['zones'] if z['uuid'] in zids];assert len(zs)==len(zids) and all(z['layer']==l and z['net']=='PWR_AGND' and not z['keepout'] for z in zs);refs[l]=unary_union([shape(z['polygons']) for z in zs]);assert refs[l].covers(Point(t['return_position_mm']).buffer(.31))
 assert set(refs)=={'In1.Cu','In6.Cu'};assert p['transition_script_sha256']==sha(H/'transition.py') and p['surface_plan_sha256']==sha(H/'surface-plan.json');return hole,refs

def mechanical_check(p,c,gdata):
 from shapely.geometry import shape as geo_shape
 path=H/'contact-keepouts.json';assert p['mechanical_keepouts_sha256']==sha(path)=='9975b35aeb05140e87408b99d9f373c6a69588591cfa4eadfdf03cddad577d4d';assert p['mechanical_keepouts_source_commit']=='c39e0d3b'
 for f in json.loads(path.read_text())['features']:
  keep=geo_shape(f['geometry'])
  for l in f['properties']['layers']:
   for o in c['objects']:
    if l in o['layers']:
     og=shape(o['layers'][l])
     if o.get('npth'):
      assert o['net']=='' and abs((og.bounds[2]-og.bounds[0])-o['drill_mm'][0])<.003 and abs((og.bounds[3]-og.bounds[1])-o['drill_mm'][1])<.003
     else:assert og.distance(keep)>0
   for o in gdata['objects']:
    if l in o['layers_nm']:assert nmshape(o['layers_nm'][l]).distance(keep)>0
   for z in c['zones']:
    if z['layer']==l:assert shape(z['polygons']).distance(keep)>0

def verify(allow_rejected_drc=False):
 r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());gdata=json.loads((OUT/'added-copper-geometry.json').read_text());by=semantic(p,c)
 for key,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('planner_sha256',H/'plan.py'),('plan_sha256',H/'plan.json'),('script_sha256',H/'native.py'),('added_geometry_sha256',OUT/'added-copper-geometry.json')]:assert r[key]==sha(path)
 assert p['capture_sha256']==sha(H/'capture-01/capture.json') and any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for n,h in r['helper_sha256'].items():assert sha(H.parent/n)==h
 assert r['exact_declared_group_joins_only'] and r['all_original_objects_and_pad_identities_unchanged'] and r['all_original_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==1945 and r['opens_after']==1944
 assert gdata['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');assert {o['uuid'] for o in gdata['objects']}==set(r['added_copper_uuids'])
 reference=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in p['reference_zone_uuids']]);escape,return_refs=transition_check(p,c,reference);allowed=reference.union(escape);quietids=set(q['retained_object_uuids']);quietzones={x['zone_uuid'] for x in q['plane_exclusions']};maxgap=0
 for o in gdata['objects']:
  for layer,polys in o['layers_nm'].items():
   g=nmshape(polys)
   if o['kind']=='PCB_TRACK' and layer=='B.Cu':gap=g.difference(reference).area;maxgap=max(maxgap,gap);assert g.difference(allowed).area<1e-9,'Actual native track exceeds explicit antipad exception'
   if o['kind']=='PCB_VIA' and layer in return_refs:assert g.difference(return_refs[layer]).area<1e-9,'Return via lacks actual adjacent-layer fill contact'
   for old in c['objects']:
    if old['uuid'] in quietids and layer in old['layers']:assert g.distance(shape(old['layers'][layer]))>=.199
   for z in c['zones']:
    if z['uuid'] in quietzones and z['layer']==layer:assert g.distance(shape(z['authored_outline']))>=.199
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];az={first(z,'uuid')[1]:z for z in children(a,'zone')};bz={first(z,'uuid')[1]:z for z in children(b,'zone')};assert len(az)==len(bz)==49 and az==bz
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 old,new=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);baseline={key(v) for v in old['violations']};extra=[v for v in new['violations'] if key(v) not in baseline];assert baseline<={key(v) for v in new['violations']} and len(old['violations'])==4
 if allow_rejected_drc:
  assert len(extra)==7 and all(v['type']=='clearance' and any(i['uuid'] in {'bc76c316-2c04-5ecb-85b7-3e5f80b26bf1','da7a2424-3959-5829-8f62-0b3d420e6cd9'} for i in v['items']) for v in extra)
 else:assert not extra
 proc=json.loads((OUT/'drc-process/process.json').read_text());assert proc['status']=='passed' and all(proc['inputs_unchanged'].values())
 for log in ['stdout.log','stderr.log']:assert proc[log+'_sha256']==sha(OUT/'drc-process'/log)
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 mechanical_check(p,c,gdata)
 result={'routes':1,'new_vias':1,'new_tracks':sum(o['kind']=='PCB_TRACK' for o in gdata['objects']),'opens':1944,'maximum_native_track_antipad_exception_mm2':maxgap,'reference_exception_outside_single_actual_antipad_mm2':0,'original_zones_unchanged':49,'qualified':False};print(result);return result
if __name__=='__main__':(H/'verification.json').write_text(json.dumps(verify(),indent=2)+'\n')
