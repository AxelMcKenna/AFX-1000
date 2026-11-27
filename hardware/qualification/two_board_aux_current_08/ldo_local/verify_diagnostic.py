"""Exhaustive schematic delta and isolated physical local-bypass verification."""
import csv,json,copy,xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import box,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha,shape
from ..metadata.verify import nets
from ..precision.verify import canonical
from ..metadata.build import props
from ..vin_escape.verify import saved_fill,ground_contacts,main_mount_check,nmshape
from ..main_feeds.verify import mechanical_check
from ..held_cell.verify_plane import library_link
H=Path(__file__).resolve().parent;BASE=H.parent/'main_ldo/native-03';OUT=H/'native-03';CUT='d0572a8e-b95d-5c59-9a7c-1d3514a507b4'
def semantic(before,after):
 a,b=nets(before),nets(after);extra={('P_C907','1'):'/P_power_supply/AUX_PREREG5',('P_C907','2'):'PWR_AGND'};assert set(b)==set(a)|set(extra) and not set(a)&set(extra);assert all(b[k]==v for k,v in a.items());assert {k:b[k] for k in extra}==extra
 ca,cb=[{x.attrib['ref']:x for x in t.findall('./components/comp')} for t in [before,after]];assert set(cb)==set(ca)|{'P_C907'} and len(cb)==1105
 for ref in ca:assert canonical(ca[ref])==canonical(cb[ref]),ref
 assert cb['P_C907'].findtext('value')=='1uF 25V X7R 10%';assert cb['P_C907'].findtext('footprint')=='TB05_P_Capacitor_SMD:C_0603_1608Metric';assert next(x.text for x in cb['P_C907'].findall('./fields/field') if x.attrib['name']=='MPN')=='C0603C105K3RACTU'
 return len(a)
def verify():
 r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'local-routes.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());g=json.loads((OUT/'added-copper-geometry.json').read_text());s=json.loads((H/'schematic-changes.json').read_text())
 for k,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('planner_sha256',H/'local_routes.py'),('plan_sha256',H/'local-routes.json'),('script_sha256',H/'native_exact.py'),('added_geometry_sha256',OUT/'added-copper-geometry.json'),('full_refill_sha256',H/'native-02/full-refill.kicad_pcb')]:assert r[k]==sha(path)
 for n,v in r['helper_sha256'].items():assert sha(H.parent/n)==v
 assert p['capture_sha256']==sha(H/'capture-01/capture.json');assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for n,v in s['source_schematic_sha256'].items():assert sha(H.parent/'precision/authored'/n)==v
 for n,v in s['candidate_schematic_sha256'].items():assert sha(H/'authored'/n)==v
 for k,path in [('builder_sha256',H/'build.py'),('source_netlist_sha256',H.parent/'precision/native-01/candidate-netlist.xml'),('source_bom_sha256',H.parent/'precision/candidate-bom.csv'),('candidate_bom_sha256',H/'candidate-bom.csv'),('datasheet_sha256',H/'primary/c0603c105k3ractu.pdf')]:assert s[k]==sha(path)
 oldpins=semantic(ET.parse(H.parent/'precision/native-01/candidate-netlist.xml'),ET.parse(OUT/'candidate-netlist.xml'));ab,bb=[list(csv.DictReader(x.open())) for x in [H.parent/'precision/candidate-bom.csv',H/'candidate-bom.csv']];assert bb[:-1]==ab and bb[-1]['Reference']=='P_C907'
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];af,bf=[{props(f)['Reference'][2]:f for f in children(t,'footprint')} for t in [a,b]];assert set(bf)==set(af)|{'P_C907'}
 for ref in af:assert af[ref]==bf[ref],ref
 fp=bf['P_C907'];assert list(map(float,first(fp,'at')[1:]))==[187.5,126.6,180] and first(fp,'layer')[1]=='F.Cu';assert props(fp)['MPN'][2]=='C0603C105K3RACTU';pads=children(fp,'pad');assert {x[1] for x in pads}=={'1','2'} and len(pads)==2
 for pad in pads:assert list(map(float,first(pad,'size')[1:]))==[.9,.95] and first(pad,'net')[1]=={'1':'/P_power_supply/AUX_PREREG5','2':'PWR_AGND'}[pad[1]]
 az,bz=[{first(z,'uuid')[1]:z for z in children(t,'zone')} for t in [a,b]];assert len(az)==len(bz)==49 and set(az)==set(bz)
 for uid,z in az.items():
  if uid!=CUT:assert bz[uid]==z
  else:assert [x for x in z if not isinstance(x,list) or x[0]!='filled_polygon']==[x for x in bz[uid] if not isinstance(x,list) or x[0]!='filled_polygon']
 old,new=saved_fill(az[CUT]),saved_fill(bz[CUT]);removed=old.difference(new);assert new.difference(old).area<1e-9 and removed.difference(box(187.69,125.95,188.57,127.65)).area<1e-9;contacts=ground_contacts(old,new,c,'F.Cu')
 bind=json.loads((H/'local-fill.json').read_text());assert bind['candidate_sha256']==sha(OUT/'power_protection.kicad_pcb') and bind['script_sha256']==sha(H/'local_fill.py') and bind['applied_native_run']==['replace',118,138,118,132]
 assert r['exact_declared_group_joins_only'] and r['all_original_objects_and_pad_identities_unchanged'] and r['all_48_other_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==r['opens_after']==1943
 assert len(g['objects'])==5 and set(r['added_copper_uuids'])=={o['uuid'] for o in g['objects']};assert g['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');reference=unary_union([saved_fill(bz[u]) for u in p['reference_zone_uuids']]);q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qi=set(q['retained_object_uuids']);qz={z['zone_uuid'] for z in q['plane_exclusions']};assert CUT not in qz
 for o in g['objects']:
  assert o['kind']=='PCB_TRACK' and set(o['layers_nm'])=={'F.Cu'};cu=nmshape(o['layers_nm']['F.Cu']);assert cu.difference(reference).area<1e-9
  for oldobj in c['objects']:
   if oldobj['uuid'] in qi and 'F.Cu' in oldobj['layers']:assert cu.distance(shape(oldobj['layers']['F.Cu']))>=.199
 for x in [188.275,186.725]:assert box(x-.45,126.125,x+.45,127.075).difference(reference).area<1e-9
 main_mount_check(c,g);mechanical_check({'mechanical_keepouts_sha256':sha(H.parent/'main_feeds/contact-keepouts.json'),'mechanical_keepouts_source_commit':'c39e0d3b'},c,g)
 olderc,erc=[json.loads(p.read_text()) for p in [H.parent/'precision/native-01/candidate-erc.json',OUT/'candidate-erc.json']];assert olderc['sheets']==erc['sheets'];oldrc,newrc=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(oldrc['violations'],key=key)==sorted(newrc['violations'],key=key) and len(newrc['violations'])==4
 for name in ['netlist','erc','drc']:
  d=OUT/(name+'-process');rr=json.loads((d/'process.json').read_text());assert rr['status']=='passed' and all(rr['inputs_unchanged'].values())
  for log in ['stdout.log','stderr.log']:assert rr[log+'_sha256']==sha(d/log)
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 return {'components':1105,'unchanged_old_netted_pins':oldpins,'new_capacitor':'P_C907','new_tracks':5,'opens':1943,'local_AGND_removed_mm2':removed.area,'original_ground_contacts_preserved':len(contacts),'all_48_other_zones_exact':True,'unwaived_DSE_errors':4,'effective_capacitance_qualified':False,'return_loop_qualified':False,'IN_EN_feed_complete':False,'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
