"""Verify exact shared-pin changes, retained copper and complete schematic pin-net alignment."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString,Point
from ..routed.plan import sha,shape
from hardware.electronics.common.sexpr import read_sexpr,children,first
H=Path(__file__).resolve().parent;BASE=H.parent/'bypass_local/native-03';OUT=H/'native-04'
EXPECTED={('E_U31','6'):'PWR_AUX_FAST_RESET_N',('E_U31','8'):'PWR_AUX_HELD3V3',('E_C76','1'):'PWR_AUX_HELD3V3',('E_U29','8'):'PWR_AUX_HELD3V3',('E_C74','1'):'PWR_AUX_HELD3V3',('P_U102','5'):'/P_power_supply/AUX_PREREG5',('P_U102','8'):'/P_power_supply/AUX_PREREG5',('P_C102','1'):'/P_power_supply/AUX_PREREG5'}
def pins(tree):
 out={}
 for f in children(tree,'footprint'):
  ref=next(p[2] for p in children(f,'property') if p[1]=='Reference')
  for p in children(f,'pad'):
   if not p[1]:continue
   key=(ref,p[1]);net=first(p,'net');name=net[-1] if net else '';assert key not in out or out[key]==name;out[key]=name
 return out
def check_pin_delta(old,new,schematic):
 moves={k:v for k,v in new.items() if old.get(k)!=v};assert moves==EXPECTED;assert set(old)==set(new)
 missing={k:(new.get(k),v) for k,v in schematic.items() if new.get(k)!=v};assert not missing,missing
 return len(schematic)
def verify():
 p=json.loads((H/'plan.json').read_text());r=json.loads((OUT/'review.json').read_text());routes=json.loads((H/'routes.json').read_text());c=json.loads((H.parent/'bypass_local/capture-01/capture.json').read_text())
 assert p['planner_sha256']==sha(H/'plan.py') and p['source_capture_sha256']==sha(H.parent/'bypass_local/capture-01/capture.json') and p['netlist_sha256']==sha(H.parent/'held_cutover/native-03/candidate-netlist.xml')
 for key,path in [('source_sha256',BASE/'power_protection.kicad_pcb'),('candidate_sha256',OUT/'power_protection.kicad_pcb'),('script_sha256',H/'native.py'),('plan_sha256',H/'plan.json'),('routes_sha256',H/'routes.json')]:assert r[key]==sha(path)
 assert routes['cut_plan_sha256']==sha(H/'plan.json') and routes['router_sha256']==sha(H/'routes.py')
 assert r['exact_declared_pin_isolations_and_local_joins_only'] and r['all_original_fills_unchanged'] and r['all_other_original_copper_unchanged'] and r['anonymous_identity_bijection_preserved']==55
 assert r['opens_before']==1957 and r['opens_after']==1964 and len(r['removed_copper_uuids'])==31 and len(r['added_track_uuids'])==2
 a,b=[read_sexpr((x/'power_protection.kicad_pcb').read_text()) for x in [BASE,OUT]];assert children(a,'zone')==children(b,'zone');netlist=ET.parse(H.parent/'held_cutover/native-03/candidate-netlist.xml');schematic={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in netlist.findall('./nets/net') for n in net.findall('node')};count=check_pin_delta(pins(a),pins(b),schematic)
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 old,new=[json.loads((x/'drc.json').read_text()) for x in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
 for route in routes['routes']:
  g=LineString(route['path_mm']).buffer(route['width_mm']/2);ref=shape(next(z['polygons'] for z in c['zones'] if z['uuid']==route['reference_zone_uuid']));assert g.difference(ref).area<1e-10
 print('PASS: exact eight pin changes; %s schematic netted pin assignments aligned; 31 obsolete objects removed and local U29 bypass joined; 4 DSE errors unchanged'%count)
if __name__=='__main__':verify()
