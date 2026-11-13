"""Validate actual native local copper, exact circuit links and preserved references."""
import json,math
from pathlib import Path
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
from ..held_cell.verify_plane import library_link
from ..vin_escape.verify import saved_fill,ground_contacts,main_mount_check
from ..main_feeds.verify import mechanical_check
H=Path(__file__).resolve().parent;BASE=H.parent/'vin_escape/native-04';OUT=H/'native-03'
def semantic(plan,capture):
 by={o['ref']+'.'+o['pin']:o for o in capture['objects'] if o.get('ref')}
 assert len(plan['routes'])==1 and not plan['failures'] and not plan['new_vias']
 r=plan['routes'][0];assert (r['source'],r['target'],r['net'],r['layer'],r['width_mm'])==('P_C901.1','P_C102.1','/P_power_supply/AUX_PREREG5','B.Cu',.3)
 assert by[r['source']]['net']==by[r['target']]['net']==r['net']
 return by
def nmshape(polys):return unary_union([Polygon([[x/1e6,y/1e6] for x,y in p['outer']],[[[x/1e6,y/1e6] for x,y in hole] for hole in p['holes']]) for p in polys])
def zone_preservation(az,bz,cut):
 assert len(az)==len(bz)==49 and set(az)==set(bz)
 for uid,z in az.items():
  if uid!=cut:assert bz[uid]==z,'Undeclared source zone changed'
  else:assert [x for x in z if not isinstance(x,list) or x[0]!='filled_polygon']==[x for x in bz[uid] if not isinstance(x,list) or x[0]!='filled_polygon']

def verify():
 r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());gdata=json.loads((OUT/'added-copper-geometry.json').read_text());by=semantic(p,c)
 for key,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('planner_sha256',H/'plan.py'),('plan_sha256',H/'plan.json'),('script_sha256',H/'native_exact.py'),('added_geometry_sha256',OUT/'added-copper-geometry.json')]:assert r[key]==sha(path)
 assert p['capture_sha256']==sha(H/'capture-01/capture.json') and any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for n,h in r['helper_sha256'].items():assert sha(H.parent/n)==h
 assert r['exact_declared_group_joins_only'] and r['all_original_objects_and_pad_identities_unchanged'] and r['all_48_other_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==1944 and r['opens_after']==1943
 assert len(gdata['objects'])==15 and all(o['kind']=='PCB_TRACK' and set(o['layers_nm'])=={'B.Cu'} for o in gdata['objects'])
 assert by['P_C901.1']['group']==p['source_group']
 assert gdata['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');assert {o['uuid'] for o in gdata['objects']}==set(r['added_copper_uuids'])
 reference=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in p['reference_zone_uuids']]);quietids=set(q['retained_object_uuids']);quietzones={x['zone_uuid'] for x in q['plane_exclusions']};maxgap=0
 for o in gdata['objects']:
  for layer,polys in o['layers_nm'].items():
   g=nmshape(polys)
   if o['kind']=='PCB_TRACK' and layer=='B.Cu':gap=g.difference(reference).area;maxgap=max(maxgap,gap);assert gap<1e-9,'Actual native track lacks reference'
   if o['kind']=='PCB_VIA' and layer=='In6.Cu':assert g.difference(reference).area<1e-9,'Return via lacks actual main fill contact'
   for old in c['objects']:
    if old['uuid'] in quietids and layer in old['layers']:assert g.distance(shape(old['layers'][layer]))>=.199
   for z in c['zones']:
    if z['uuid'] in quietzones and z['layer']==layer:assert g.distance(shape(z['authored_outline']))>=.199
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];az={first(z,'uuid')[1]:z for z in children(a,'zone')};bz={first(z,'uuid')[1]:z for z in children(b,'zone')};assert len(az)==len(bz)==49 and set(az)==set(bz)
 cut='bc76c316-2c04-5ecb-85b7-3e5f80b26bf1';assert r['cutback_zone_uuids']==p['cutback_zone_uuids']==[cut]
 zone_preservation(az,bz,cut)
 assert first(az[cut],'net')[1]=='PWR_AGND';oldfill=saved_fill(az[cut]);newfill=saved_fill(bz[cut]);copper=unary_union([nmshape(o['layers_nm']['B.Cu']) for o in gdata['objects']]);removed=oldfill.difference(newfill);added=newfill.difference(oldfill);outside=removed.difference(copper.buffer(.254));delta={'added_mm2':added.area,'removed_mm2':removed.area,'removed_outside_0_254mm_track_envelope_mm2':outside.area,'outside_bounds':list(outside.bounds) if not outside.is_empty else [],'candidate_board_sha256':sha(OUT/'power_protection.kicad_pcb')};(H/'fill-delta.json').write_text(json.dumps(delta,indent=2)+'\n');assert added.area<1e-9 and outside.area<1e-9,'Nonlocal fill change'
 binding=json.loads((H/'exact-local-fill.json').read_text());assert binding['candidate_sha256']==sha(OUT/'power_protection.kicad_pcb') and binding['script_sha256']==sha(H/'local_fill_exact.py');assert first(az[cut],'min_thickness')[1]=='0.25'
 contacts=ground_contacts(oldfill,newfill,c,'B.Cu');delta['ground_contacts_preserved']=contacts
 main_mount_check(c,gdata);mechanical_check({'mechanical_keepouts_sha256':sha(H.parent/'main_feeds/contact-keepouts.json'),'mechanical_keepouts_source_commit':'c39e0d3b'},c,gdata)
 source=unary_union([shape(o['layers']['B.Cu']) for o in c['objects'] if o['group']==p['source_group'] and 'B.Cu' in o['layers']]);assert source.covers(Point(p['path_mm'][0])) and shape(by['P_C102.1']['layers']['B.Cu']).covers(Point(p['path_mm'][-1]))
 assert r['full_refill_sha256']==sha(H/'native-01/full-refill.kicad_pcb') and r['authored_board_sha256']==sha(OUT/'authored.kicad_pcb')
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 old,new=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
 refill=json.loads((H/'native-01/refill-process/process.json').read_text());assert refill['status']=='passed' and all(refill['inputs_unchanged'].values())
 proc=json.loads((OUT/'drc-process/process.json').read_text());assert proc['status']=='passed' and all(proc['inputs_unchanged'].values())
 for log in ['stdout.log','stderr.log']:assert proc[log+'_sha256']==sha(OUT/'drc-process'/log)
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 result={'routes':1,'new_vias':0,'new_tracks':sum(o['kind']=='PCB_TRACK' for o in gdata['objects']),'opens':1943,'maximum_native_track_reference_gap_mm2':maxgap,'original_zones_unchanged':48,'AGND_local_cutback':delta,'qualified':False};print({k:v for k,v in result.items() if k!='AGND_local_cutback'});return result
if __name__=='__main__':(H/'verification.json').write_text(json.dumps(verify(),indent=2)+'\n')
