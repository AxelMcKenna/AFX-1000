"""Independent source, local antipad, reference, contact and group-delta gates."""
import json,math
from pathlib import Path
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
from ..held_cell.verify_local import nmshape
from ..held_cell.verify_plane import library_link
from ..main_feeds.verify import mechanical_check
H=Path(__file__).resolve().parent;SRC=H.parent/'main_feeds';BASE=H.parent/'precision/native-01';OUT=H/'native-04';VIN=[198.,118.6];RETURN=[198.8,118.8]
EXPECTED={'d41ab58e-16e9-5d76-8b14-dc335aff8371','787e0385-5c4c-5b8f-9a2a-017054f7da0e','1893ea20-0fe1-5364-8239-d1853c450ce0','78fadc71-5bdb-5968-8ca8-0e3b4b40722f','38c31b6e-bfc4-5702-b059-ff9efeabba60'}
def semantics(p,c):
 assert not p['failures'] and {(r['source'],r['target'],r['net'],r['layer'],r['width_mm']) for r in p['routes']}=={('P_U101.1','via:VIN','/P_power_supply/VIN_IC','F.Cu',.25),('via:VIN','P_C900.1','/P_power_supply/VIN_IC','B.Cu',.3)}
 assert p['new_vias']==[{'name':'VIN','net':'/P_power_supply/VIN_IC','position_mm':VIN,'size_mm':.6,'drill_mm':.3},{'name':'VIN_return','net':'PWR_AGND','position_mm':RETURN,'size_mm':.6,'drill_mm':.3}];assert abs(p['return_pair_mm']-math.dist(VIN,RETURN))<1e-9 and p['return_pair_mm']<1
 by={o['ref']+'.'+o['pin']:o for o in c['objects'] if o.get('ref')};assert by['P_U101.1']['net']==by['P_C900.1']['net']=='/P_power_supply/VIN_IC' and by['P_U101.1']['group']=='04693f6e-fbbf-53d2-8cb7-16d7e4b68b5a';assert set(p['declared_cutback_zone_uuids'])==EXPECTED
 for r in p['routes']:
  assert r['path_mm'][-1 if r['target']=='via:VIN' else 0]==VIN

def saved_fill(z):
 # KiCad stores holes as repeated bridges; buffer(0) resolves those exact paths.
 return unary_union([Polygon([(float(x[1]),float(x[2])) for x in first(f,'pts')[1:]]).buffer(0) for f in children(z,'filled_polygon')])

def local_cutback(old,new,via):
 added=new.difference(old).area;removed=old.difference(new);outside=removed.difference(via.buffer(.206)).area
 assert added<1e-9 and outside<1e-9,'Fill changes exceed declared local via antipad envelope'
 return {'added_mm2':added,'removed_mm2':removed.area,'removed_outside_antipad_envelope_mm2':outside,'old_components':len(old.geoms) if hasattr(old,'geoms') else 1,'new_components':len(new.geoms) if hasattr(new,'geoms') else 1}

def ground_contacts(old,new,c,layer):
 contacts=[]
 for o in c['objects']:
  if o['net']=='PWR_AGND' and layer in o['layers']:
   copper=shape(o['layers'][layer]);before=old.intersection(copper).area
   if before>1e-9:assert before-new.intersection(copper).area<1e-9,'Original ground contact reduced';contacts.append(o['uuid'])
 return contacts

def main_mount_check(c,gdata):
 from shapely.geometry import shape as geo_shape
 path=H/'main-mount-keepouts.json';assert sha(path)=='38854f6356625631ad32ec4578c989c2c3e06a6f8c48754ec768c55f53e04d71'
 features=[f for f in json.loads(path.read_text())['features'] if f['properties']['board']=='power'];assert len(features)==13
 for f in features:
  keep=geo_shape(f['geometry'])
  for l in f['properties']['layers']:
   for o in c['objects']:
    if l not in o['layers']:continue
    og=shape(o['layers'][l])
    if o.get('npth'):assert o['net']=='' and abs((og.bounds[2]-og.bounds[0])-o['drill_mm'][0])<.003 and abs((og.bounds[3]-og.bounds[1])-o['drill_mm'][1])<.003
    else:assert og.distance(keep)>0,(f['properties']['mount'],o['uuid'])
   for o in gdata['objects']:
    if l in o['layers_nm']:assert nmshape(o['layers_nm'][l]).distance(keep)>0
   for z in c['zones']:
    if z['layer']==l:assert shape(z['polygons']).distance(keep)>0

def verify():
 p=json.loads((H/'plan.json').read_text());r=json.loads((OUT/'review.json').read_text());c=json.loads((SRC/'capture-01/capture.json').read_text());gdata=json.loads((OUT/'geometry.json').read_text());semantics(p,c)
 assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for k,path in [('capture_sha256',SRC/'capture-01/capture.json'),('source_board_sha256',BASE/'power_protection.kicad_pcb'),('planner_sha256',H/'plan.py'),('local_site_screen_sha256',H/'local-sites.json'),('zone_helper_sha256',SRC/'routing_zones.py'),('mechanical_keepouts_sha256',SRC/'contact-keepouts.json'),('quiet_exclusions_sha256',H.parent/'routed/quiet-exclusion.json')]:assert p[k]==sha(path)
 sites=json.loads((H/'local-sites.json').read_text());assert sites['script_sha256']==sha(H/'local_sites.py');assert any(s['vin_via_mm']==VIN and RETURN in s['return_sites_mm'] for s in sites['legal_paired_sites'])
 for k,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('authored_board_sha256',OUT/'authored.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('plan_sha256',H/'plan.json'),('script_sha256',H/'native_exact_visible.py'),('geometry_sha256',OUT/'geometry.json')]:assert r[k]==sha(path)
 prior=json.loads((H/'native-01/review.json').read_text());assert prior['initial_script_sha256']==sha(H/'native_initial.py') and prior['script_sha256']==sha(H/'native.py')
 binding=json.loads((H/'exact-antipads.json').read_text());assert binding['script_sha256']==sha(H/'local_fill_exact.py') and binding['board_sha256']==sha(H/'exact-antipads.kicad_pcb')
 for n,v in r['helper_sha256'].items():assert sha(H.parent/n)==v
 assert r['local_antipad_only_from_recorded_native_refill']
 assert r['exact_declared_group_joins_only'] and r['all_original_objects_and_pad_identities_unchanged'] and r['all_other_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==1945 and r['opens_after']==1944
 assert gdata['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');assert {o['uuid'] for o in gdata['objects']}==set(r['added_copper_uuids']);assert sum(o['kind']=='PCB_TRACK' for o in gdata['objects'])==13 and sum(o['kind']=='PCB_VIA' for o in gdata['objects'])==2
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];az={first(z,'uuid')[1]:z for z in children(a,'zone')};bz={first(z,'uuid')[1]:z for z in children(b,'zone')};assert set(az)==set(bz) and len(az)==49
 for uid,z in az.items():
  if uid not in EXPECTED:assert bz[uid]==z
  else:assert [x for x in bz[uid] if not isinstance(x,list) or x[0]!='filled_polygon']==[x for x in z if not isinstance(x,list) or x[0]!='filled_polygon']
 oldz={z['uuid']:z for z in c['zones']};newz={z['uuid']:z for z in gdata['zones']};assert set(newz)==EXPECTED;quiet=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qids=set(quiet['retained_object_uuids']);qzones={z['zone_uuid'] for z in quiet['plane_exclusions']};assert not EXPECTED&qzones;vin=next(o for o in gdata['objects'] if o['kind']=='PCB_VIA' and o['net']=='/P_power_supply/VIN_IC');ret=next(o for o in gdata['objects'] if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND');deltas=[]
 for uid,z in newz.items():
  assert z['net']==oldz[uid]['net']=='PWR_AGND' and z['layer']==oldz[uid]['layer'];old=saved_fill(az[uid]);new=saved_fill(bz[uid]);extracted=nmshape(z['polygons_nm']);delta=extracted.symmetric_difference(new);assert delta.difference(new.boundary.buffer(.0000011)).area<1e-12,'Native polygon extraction differs beyond integer-grid rounding';d=local_cutback(old,new,nmshape(vin['layers_nm'][z['layer']]));contacts=[]
  contacts=ground_contacts(old,new,c,z['layer'])
  d.update(native_unfracture_rounding_area_mm2=delta.area,zone_uuid=uid,layer=z['layer'],original_contacts_preserved=contacts);deltas.append(d)
 reference={layer:unary_union([saved_fill(bz[uid]) if uid in newz else shape(oldz[uid]['polygons']) for uid in ids]) for layer,ids in p['reference_zone_uuids'].items()};holes={}
 for l,ref in reference.items():
  hs=[Polygon(ring) for part in (ref.geoms if hasattr(ref,'geoms') else [ref]) for ring in part.interiors if Polygon(ring).covers(Point(VIN))];assert len(hs)==1 and hs[0].area<.81 and max(math.dist(v,VIN) for v in hs[0].exterior.coords)<.51;holes[l]=hs[0]
  rl='In1.Cu' if l=='F.Cu' else 'In6.Cu';assert nmshape(ret['layers_nm'][rl]).difference(ref).area<1e-9,'Paired return lacks actual filled contact'
 gaps={l:0 for l in reference}
 for o in gdata['objects']:
  for l,ps in o['layers_nm'].items():
   copper=nmshape(ps)
   if o['kind']=='PCB_TRACK':assert copper.difference(reference[l].union(holes[l])).area<1e-9;gaps[l]+=copper.difference(reference[l]).area
   for old in c['objects']:
    if old['uuid'] in qids and l in old['layers']:assert copper.distance(shape(old['layers'][l]))>=.199
   for z in c['zones']:
    if z['uuid'] in qzones and z['layer']==l:assert copper.distance(shape(z['authored_outline']))>=.199
 mechanical_check({**p,'mechanical_keepouts_source_commit':'c39e0d3b'},c,gdata)
 main_mount_check(c,gdata)
 oldrc,newrc=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(oldrc['violations'],key=key)==sorted(newrc['violations'],key=key) and len(newrc['violations'])==4
 for tag in ['default','legacy-in6']:
  assert r['contexts'][tag]['full_refill_sha256']==sha(H/'native-01'/(tag+'-full-refill.kicad_pcb'));assert r['contexts'][tag]['omitted_zone_uuids']==(['38c31b6e-bfc4-5702-b059-ff9efeabba60'] if tag=='legacy-in6' else [])
 for tag in ['default-process','legacy-in6-process','drc-process']:
  d=(OUT if tag=='drc-process' else H/'native-01')/tag;rr=json.loads((d/'process.json').read_text());assert rr['status']=='passed' and all(rr['inputs_unchanged'].values())
  for log in ['stdout.log','stderr.log']:assert rr[log+'_sha256']==sha(d/log)
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 return {'opens':1944,'tracks':13,'vias':2,'pair_distance_mm':p['return_pair_mm'],'AGND_only_antipad_zones':5,'unchanged_zones':44,'DC_IN_and_all_other_net_fills_unchanged':True,'deltas':deltas,'reference_exceptions_inside_actual_new_via_antipads_mm2':gaps,'reference_exception_outside_antipads_mm2':0,'unwaived_DSE_errors':4,'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='deltas'})
