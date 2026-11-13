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
from .associations import expected_paths,NEW_REFS
H=Path(__file__).resolve().parent;BASE=H.parent/'main_ldo/native-03';OUT=H/'native-07';CUT='d0572a8e-b95d-5c59-9a7c-1d3514a507b4'
def semantic(before,after):
 a,b=nets(before),nets(after);extra={('P_C907','1'):'/P_power_supply/AUX_PREREG5',('P_C907','2'):'PWR_AGND'};assert set(b)==set(a)|set(extra) and not set(a)&set(extra);assert all(b[k]==v for k,v in a.items());assert {k:b[k] for k in extra}==extra
 ca,cb=[{x.attrib['ref']:x for x in t.findall('./components/comp')} for t in [before,after]];assert set(cb)==set(ca)|{'P_C907'} and len(cb)==1105
 for ref in ca:assert canonical(ca[ref])==canonical(cb[ref]),ref
 assert cb['P_C907'].findtext('value')=='1uF 25V X7R 10%';assert cb['P_C907'].findtext('footprint')=='TB05_P_Capacitor_SMD:C_0603_1608Metric';assert next(x.text for x in cb['P_C907'].findall('./fields/field') if x.attrib['name']=='MPN')=='C0603C105K3RACTU'
 return len(a)
def route_identity(plan,capture):
 by={o['ref']+'.'+o['pin']:o for o in capture['objects'] if o.get('ref')}
 assert [(r['source'],r['target'],r['net'],r['width_mm'],r['layer']) for r in plan['routes']]==[('P_C907.1','P_U102.8','/P_power_supply/AUX_PREREG5',.3,'F.Cu'),('P_C907.2','P_U102.9','PWR_AGND',.4,'F.Cu')]
 assert by['P_U102.8']['net']=='/P_power_supply/AUX_PREREG5' and by['P_U102.9']['net']=='PWR_AGND'
 for r in plan['routes']:
  assert abs(__import__('shapely.geometry',fromlist=['LineString']).LineString(r['path_mm']).length-r['length_mm'])<1e-9
def verify():
 r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'direct-return-plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());g=json.loads((OUT/'added-copper-geometry.json').read_text());s=json.loads((H/'schematic-changes.json').read_text())
 route_identity(p,c)
 for k,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('planner_sha256',H/'direct_return_plan.py'),('plan_sha256',H/'direct-return-plan.json'),('script_sha256',H/'native_selected_v2.py'),('added_geometry_sha256',OUT/'added-copper-geometry.json'),('full_refill_sha256',OUT/'full-refill.kicad_pcb')]:assert r[k]==sha(path)
 for n,v in r['helper_sha256'].items():assert sha(H.parent/n)==v
 assert p['capture_sha256']==sha(H/'capture-01/capture.json');assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(BASE/'power_protection.kicad_pcb') for k,v in c['source_sha256'].items())
 for n,v in s['source_schematic_sha256'].items():assert sha(H.parent/'footprint_identity/authored'/n)==v
 for n,v in s['candidate_schematic_sha256'].items():assert sha(H/'authored'/n)==v
 for k,path in [('builder_sha256',H/'build.py'),('source_netlist_sha256',H.parent/'footprint_identity/native-01/candidate-netlist.xml'),('source_bom_sha256',H.parent/'footprint_identity/candidate-bom.csv'),('candidate_bom_sha256',H/'candidate-bom.csv'),('datasheet_sha256',H/'primary/c0603c105k3ractu.pdf')]:assert s[k]==sha(path)
 oldpins=semantic(ET.parse(H.parent/'footprint_identity/native-01/candidate-netlist.xml'),ET.parse(OUT/'candidate-netlist.xml'));ab,bb=[list(csv.DictReader(x.open())) for x in [H.parent/'footprint_identity/candidate-bom.csv',H/'candidate-bom.csv']];assert bb[:-1]==ab and bb[-1]['Reference']=='P_C907'
 a,b=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];af,bf=[{props(f)['Reference'][2]:f for f in children(t,'footprint')} for t in [a,b]];assert set(bf)==set(af)|{'P_C907'}
 paths=expected_paths(H/'authored/power_protection.kicad_sch',OUT/'candidate-netlist.xml');audit=json.loads((OUT/'association-audit.json').read_text());assert r['association_audit_sha256']==sha(OUT/'association-audit.json') and audit['source_board_sha256']==sha(BASE/'power_protection.kicad_pcb') and audit['candidate_netlist_sha256']==sha(OUT/'candidate-netlist.xml') and audit['root_schematic_sha256']==sha(H/'authored/power_protection.kicad_sch') and audit['helper_sha256']==sha(H/'associations.py');assert {x['reference'] for x in audit['changes']}==NEW_REFS and len(audit['changes'])==19
 for x in audit['changes']:assert x['before'] is None and x['after']==paths[x['reference']]
 for ref in af:
  expected=copy.deepcopy(af[ref])
  if ref in NEW_REFS:assert not children(expected,'path');expected.append(copy.deepcopy(first(bf[ref],'path')))
  assert expected==bf[ref],ref
 for ref,path in paths.items():assert len(children(bf[ref],'path'))==1 and first(bf[ref],'path')[1]==path
 assert len(set(first(bf[ref],'path')[1] for ref in paths))==len(paths)

 fp=bf['P_C907'];assert list(map(float,first(fp,'at')[1:]))==[187.5,126.6,180] and first(fp,'layer')[1]=='F.Cu';assert props(fp)['MPN'][2]=='C0603C105K3RACTU';pads=children(fp,'pad');assert {x[1] for x in pads}=={'1','2'} and len(pads)==2
 for pad in pads:assert list(map(float,first(pad,'size')[1:]))==[.9,.95] and first(pad,'net')[1]=={'1':'/P_power_supply/AUX_PREREG5','2':'PWR_AGND'}[pad[1]]
 az,bz=[{first(z,'uuid')[1]:z for z in children(t,'zone')} for t in [a,b]];assert len(az)==49 and len(bz)==50 and set(bz)==set(az)|{r['new_zone_uuid']}
 for uid,z in az.items():
  if uid!=CUT:assert bz[uid]==z
  else:assert [x for x in z if not isinstance(x,list) or x[0]!='filled_polygon']==[x for x in bz[uid] if not isinstance(x,list) or x[0]!='filled_polygon']
 old,new=saved_fill(az[CUT]),saved_fill(bz[CUT]);removed=old.difference(new);assert new.difference(old).area<1e-9 and removed.difference(box(187.69,125.95,188.57,127.65)).area<1e-9;contacts=ground_contacts(old,new,c,'F.Cu')
 bind=json.loads((H/'local-fill.json').read_text());assert bind['native_source_sha256']==sha(H/'native-02/power_protection.kicad_pcb') and bind['candidate_sha256']==sha(H/'local-fill.kicad_pcb') and bz[CUT]==next(z for z in children(read_sexpr((H/'local-fill.kicad_pcb').read_text()),'zone') if first(z,'uuid')[1]==CUT) and bind['script_sha256']==sha(H/'local_fill.py') and bind['applied_native_run']==['replace',118,138,118,132]
 assert r['exact_declared_group_joins_only'] and r['all_original_objects_and_pad_identities_unchanged'] and r['all_48_other_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['opens_before']==r['opens_after']==1943
 assert len(g['objects'])==4 and set(r['added_copper_uuids'])=={o['uuid'] for o in g['objects']};assert g['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');reference=unary_union([saved_fill(bz[u]) for u in p['reference_zone_uuids']+[r['new_zone_uuid']]]);q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());qi=set(q['retained_object_uuids']);qz={z['zone_uuid'] for z in q['plane_exclusions']};assert CUT not in qz
 nz=bz[r['new_zone_uuid']];assert first(nz,'net')[1]=='PWR_AGND' and first(nz,'layer')[1]=='In1.Cu' and first(nz,'priority')[1]=='2';outline=Polygon([(float(v[1]),float(v[2])) for v in first(first(nz,'polygon'),'pts')[1:]]);assert outline.equals(box(186.7,127.8,188,130.8));fill=saved_fill(nz);assert fill.difference(outline).area<1e-9 and fill.area>3.8
 zonegeo=json.loads((OUT/'new-zone-geometry.json').read_text());assert r['new_zone_geometry_sha256']==sha(OUT/'new-zone-geometry.json') and zonegeo['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb') and zonegeo['uuid']==r['new_zone_uuid'];assert fill.symmetric_difference(nmshape(zonegeo['polygons_nm'])).area<1e-9
 anchors=[]
 for uid,count,area in [('c10eec5d-cf1f-58da-8d6d-48ce5d70e70d',16,.8),('dfd01f0a-edcf-55b7-aecb-2d44a419b9b3',4,.7)]:
  sg=saved_fill(az[uid]);assert sg.intersection(fill).area>=area;cs=[o for o in c['objects'] if o['net']=='PWR_AGND' and 'In1.Cu' in o['layers'] and sg.intersection(shape(o['layers']['In1.Cu'])).area>1e-9];assert len(cs)==count and all(o['group']=='00b41082-e346-59e4-aee2-f34d9b87e697' for o in cs);anchors.append({'zone':uid,'source_main_contacts':count,'filled_overlap_mm2':sg.intersection(fill).area})
 for o in c['objects']:
  if 'In1.Cu' in o['layers'] and (o['net']!='PWR_AGND' or o['uuid'] in qi):assert fill.distance(shape(o['layers']['In1.Cu']))>=.199
 for z in c['zones']:
  if z['uuid'] in qz and z['layer']=='In1.Cu':assert fill.distance(shape(z['authored_outline']))>=.199
 for o in g['objects']:
  assert o['kind']=='PCB_TRACK' and set(o['layers_nm'])=={'F.Cu'};cu=nmshape(o['layers_nm']['F.Cu']);assert cu.difference(reference).area<1e-9
  for oldobj in c['objects']:
   if oldobj['uuid'] in qi and 'F.Cu' in oldobj['layers']:assert cu.distance(shape(oldobj['layers']['F.Cu']))>=.199
 for x in [188.275,186.725]:assert box(x-.45,126.125,x+.45,127.075).difference(reference).area<1e-9
 mg=copy.deepcopy(g)
 for pin,x in [('1',188.275),('2',186.725)]:
  rect=box(x-.45,126.125,x+.45,127.075);mg['objects'].append({'uuid':'P_C907.'+pin,'layers_nm':{'F.Cu':[{'outer':[[round(xx*1e6),round(yy*1e6)] for xx,yy in rect.exterior.coords],'holes':[]}]}})
 main_mount_check(c,mg);mechanical_check({'mechanical_keepouts_sha256':sha(H.parent/'main_feeds/contact-keepouts.json'),'mechanical_keepouts_source_commit':'c39e0d3b'},c,mg)
 olderc,erc=[json.loads(p.read_text()) for p in [H.parent/'precision/native-01/candidate-erc.json',OUT/'candidate-erc.json']];assert olderc['sheets']==erc['sheets'];oldrc,newrc=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(oldrc['violations'],key=key)==sorted([v for v in newrc['violations'] if v['type']=='clearance'],key=key)
 diagnostic=[v for v in newrc['violations'] if v['type']!='clearance'];assert len(diagnostic)==1 and diagnostic[0]['type']=='silk_overlap' and {i['description'] for i in diagnostic[0]['items']}=={'Reference field of P_C907','Segment of P_L20 on F.Silkscreen'}
 assert r['fill_method']=='selected-new-zone-only' and r['selected_fill_script_sha256']==sha(H/'fill_one.py')
 phases=json.loads((OUT/'phases.json').read_text());assert phases[-1]['phase']=='save_completed' and phases[-1]['output_sha256']==sha(OUT/'selected-fill.kicad_pcb')
 for name in ['netlist','erc','drc','selected-fill']:
  d=OUT/(name+'-process');rr=json.loads((d/'process.json').read_text());assert rr['status']=='passed' and all(rr['inputs_unchanged'].values())
  for logged,h in rr['input_sha256'].items():
   path=H.parents[3]/logged.removeprefix('/repo/') if logged.startswith('/repo/') else OUT/logged.removeprefix('/out/')
   assert sha(path)==h,(name,logged)
  for log in ['stdout.log','stderr.log']:assert rr[log+'_sha256']==sha(d/log)
 library_link(OUT/'libraries',json.loads((H.parent/'held_cell/library-binding.json').read_text()),H.parents[3],H.parent/'shared_cutover/native-04/libraries')
 from .immutable_inputs import check_tree,check_recorded
 manifest=json.loads((H/'inputs-local-return-08.json').read_text());bundle=H/manifest['bundle_name'];check_tree(bundle,manifest);assert manifest['script_sha256']==sha(H/'prepare_final.py') and manifest['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb')
 source_libraries=json.loads((H.parent/'associations/changes.json').read_text())['library_sha256']
 for directory,expected_files in source_libraries.items():assert {str(f.relative_to(bundle/directory)):sha(f) for f in sorted((bundle/directory).rglob('*')) if f.is_file()}==expected_files
 final=read_sexpr((bundle/'power_protection.kicad_pcb').read_text());expected=copy.deepcopy(b);ef=next(f for f in children(expected,'footprint') if props(f)['Reference'][2]=='P_C907');oldref=props(ef)['Reference'];assert oldref==manifest['reference_before'];oldref[:]=manifest['reference_after'];assert expected==final
 for n in s['candidate_schematic_sha256']:assert sha(bundle/n)==sha(H/'authored-v2'/n)==s['candidate_schematic_sha256'][n]
 fr=json.loads((H/'native-08/review.json').read_text());assert fr['manifest_sha256']==sha(H/'inputs-local-return-08.json') and fr['script_sha256']==sha(H/'native_final.py') and fr['helper_sha256']==sha(H/'immutable_inputs.py') and fr['candidate_board_sha256']==sha(bundle/'power_protection.kicad_pcb')
 assert fr['uuid_associations']==1105 and fr['schematic_parity_issues']==0 and fr['host_native_all_input_hashes_equal']
 finalparity=json.loads((H/'native-08/parity.json').read_text());assert sha(H/'native-08/parity.json')==fr['parity_sha256'] and not finalparity['schematic_parity'];assert sorted(finalparity['violations'],key=key)==sorted(oldrc['violations'],key=key)
 fp=json.loads((H/'native-08/parity-process/process.json').read_text());inputs=[bundle/'power_protection.kicad_pcb',*sorted(bundle.glob('*.kicad_sch'))];check_recorded(fp,{'/repo/'+str(path.relative_to(H.parents[3])):sha(path) for path in inputs})
 for log in ['stdout.log','stderr.log']:assert sha(H/'native-08/parity-process'/log)==fp[log+'_sha256']
 return {'final_candidate':str(bundle.relative_to(H))+'/power_protection.kicad_pcb','immutable_host_native_inputs_verified':True,'native_parity_issues':0,'components':1105,'new_exact_schematic_UUID_paths':19,'unchanged_existing_UUID_paths':audit['unchanged_existing_associations'],'unchanged_old_netted_pins':oldpins,'new_capacitor':'P_C907','new_tracks':4,'new_reference_patch_area_mm2':fill.area,'source_reference_anchors':anchors,'direct_ground_trace_mm':p['routes'][1]['length_mm'],'opens':1943,'local_AGND_removed_mm2':removed.area,'original_ground_contacts_preserved':len(contacts),'all_48_other_zones_exact':True,'unwaived_DSE_errors':4,'effective_capacitance_qualified':False,'return_loop_qualified':False,'IN_EN_feed_complete':False,'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
