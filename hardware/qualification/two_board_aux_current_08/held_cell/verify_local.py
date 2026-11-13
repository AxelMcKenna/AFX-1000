"""Validate actual native local copper, exact circuit links and preserved references."""
import json,math
from pathlib import Path
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
from .verify_plane import library_link
H=Path(__file__).resolve().parent;BASE=H/'native-plane-04';OUT=H/'native-local-02'
EXPECTED_PAIRS={('P_R902.2','P_C902.1'),('P_C902.1','P_C905.1'),('P_C905.1','P_C903.1'),('P_C903.1','P_U901.1'),('P_U901.1','P_U901.3'),('P_U901.5','P_C904.1'),('P_C904.1','P_R903.1'),('P_R903.1','P_U902.2'),('P_U902.2','P_C906.1'),('P_R902.1','P_U902.1')}
GROUNDS={'P_C902':'2','P_C905':'2','P_U901':'2','P_C903':'2','P_C904':'2','P_R903':'2','P_U902':'5','P_C906':'2'}
def semantic(plan,capture):
 by={o['ref']+'.'+o['pin']:o for o in capture['objects'] if o.get('ref')};expected=EXPECTED_PAIRS|{(r+'.'+p,'via:'+r) for r,p in GROUNDS.items()};assert len(plan['routes'])==18 and {(r['source'],r['target']) for r in plan['routes']}==expected and not plan['failures'];vias={'via:'+v['name']:v for v in plan['new_vias']};assert len(vias)==8
 for r in plan['routes']:
  assert by[r['source']]['net']==r['net']
  if r['target'].startswith('via:'):assert r['net']=='PWR_AGND' and math.dist(r['path_mm'][-1],vias[r['target']]['position_mm'])<1e-9,'Return endpoint must be centered on via'
  else:assert by[r['target']]['net']==r['net']
 for pin,net in [('P_U901.1','/P_power_supply/AUX_HELD_IN'),('P_U901.2','PWR_AGND'),('P_U901.3','/P_power_supply/AUX_HELD_IN'),('P_U901.5','PWR_AUX_HELD3V3'),('P_U902.1','/P_power_supply/AUX_PREREG5'),('P_U902.2','PWR_AUX_HELD3V3'),('P_U902.4','PWR_AUX_FAST_RESET_N'),('P_U902.5','PWR_AGND')]:assert by[pin]['net']==net
 return by
def nmshape(polys):return unary_union([Polygon([[x/1e6,y/1e6] for x,y in p['outer']],[[[x/1e6,y/1e6] for x,y in hole] for hole in p['holes']]) for p in polys])
def verify():
 r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'local-routes.json').read_text());c=json.loads((H/'capture-04/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());gdata=json.loads((OUT/'added-copper-geometry.json').read_text());by=semantic(p,c)
 for key,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('planner_sha256',H/'local_routes.py'),('plan_sha256',H/'local-routes.json'),('script_sha256',H/'native_local.py'),('added_geometry_sha256',OUT/'added-copper-geometry.json')]:assert r[key]==sha(path)
 assert p['capture_sha256']==sha(H/'capture-04/capture.json') and any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for n,h in r['helper_sha256'].items():assert sha(H.parent/n)==h
 assert r['exact_declared_group_joins_only'] and r['all_original_objects_and_pad_identities_unchanged'] and r['all_original_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==1964 and r['opens_after']==1946
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
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];az={first(z,'uuid')[1]:z for z in children(a,'zone')};bz={first(z,'uuid')[1]:z for z in children(b,'zone')};assert len(az)==len(bz)==48 and az==bz
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 old,new=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
 proc=json.loads((OUT/'drc-process/process.json').read_text());assert proc['status']=='passed' and all(proc['inputs_unchanged'].values())
 for log in ['stdout.log','stderr.log']:assert proc[log+'_sha256']==sha(OUT/'drc-process'/log)
 library_link(OUT/'libraries',json.loads((H/'library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 result={'routes':18,'new_vias':8,'new_tracks':sum(o['kind']=='PCB_TRACK' for o in gdata['objects']),'opens':1946,'maximum_native_track_reference_gap_mm2':maxgap,'original_zones_unchanged':48,'qualified':False};print(result);return result
if __name__=='__main__':(H/'local-verification.json').write_text(json.dumps(verify(),indent=2)+'\n')
