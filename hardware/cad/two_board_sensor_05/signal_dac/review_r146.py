"""Source-bound DAC group, reference, exclusion and connected-transition review."""
import json,collections,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from shapely import make_valid
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def local(p):
 p=Path(p);owner=Path('/private/tmp/rmx-lever-sensor-20261112')
 return REPO/p.relative_to(owner) if p.is_absolute() else REPO/p
b=json.loads((R.parent/'signal_input/capture-r7/capture.json').read_text());a=json.loads((R/'capture-r146/capture.json').read_text());routing=json.loads((R/'candidate-r146/routing.json').read_text());prior_patch=json.loads((R/'candidate-r139/routing.json').read_text());routing['routes']=prior_patch['routes']+routing['routes'];previous_surface=json.loads((R/'candidate-r131/routing.json').read_text());routing['routes']=previous_surface['routes']+routing['routes'];prior_candidate=json.loads((R/'candidate-r125/routing.json').read_text());new_candidate={**routing,'routes':prior_candidate['routes']+routing['routes'],'vias':prior_candidate['vias']+routing['vias'],'declared_removed':prior_candidate['declared_removed']+routing['declared_removed']};mount=json.loads((R/'candidate-r107/routing.json').read_text());routing=json.loads((R/'candidate-r98/routing.json').read_text());routing['routes']+= [{**v,'width_mm':.2,'role':'mount rework'}for v in mount['routes']];routing['routes'] += [{'net':'/D_LED/LED_39','layer':layer,'path_mm':path,'width_mm':.2,'role':'mount via recenter'}for layer,path in [('In3.Cu',[[191.3,79.9],[189.2,77.5]]),('In5.Cu',[[189.2,77.5],[189.2,67.6]])]];routing['vias'].append(mount['signal_via']);routing['vias']+=new_candidate['vias'];routing['routes']+=[x for x in new_candidate['routes']if x['net']!='LINK_AGND'];routing['expected_opens']=162;routing['ADC_selected_nets'].append('/A_ADC/NBIAS_L');removed={x['uuid']for x in mount['declared_removed']+new_candidate['declared_removed']};native=json.loads((R/'native-r146/review.json').read_text())
for cap in [b,a]:
 for f,h in cap['source_sha256'].items():assert hashlib.sha256(local(f).read_bytes()).hexdigest()==h,f
for f,h in native['source_sha256'].items():assert hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h,f
precision=json.loads((R/'capture-r146/precision.json').read_text())
assert all(hashlib.sha256(local(p).read_bytes()).hexdigest()==h for p,h in precision['source_sha256'].items())
assert precision['native_version']==a['native_version']==b['native_version']
assert precision['boards']['after']['pcb_sha256']==native['output_pcb_sha256']
fill_tol=precision['boards']['after']['max_polygonization_error_mm']
assert fill_tol==precision['boards']['before']['max_polygonization_error_mm']==.005
transition_proof=json.loads((R/'transitions-r146.json').read_text())
assert all(hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h for p,h in transition_proof['source_sha256'].items())
assert all(v['verified_return_corridor_length_mm']<=2.5+1e-9 and all(q<1e-6 for q in v['corridor_uncovered_mm2'].values())for v in transition_proof['transitions'])
old,new=[{v['uuid']:v for v in c['objects']}for c in [b,a]];after={u:k for k,vs in a['all_groups'].items()for u in vs};merged=collections.defaultdict(list)
for k,vs in b['all_groups'].items():
 dst={after[u]for u in vs if u in after};assert len(dst)==1,(k,dst);assert all(u in new or u in removed for u in vs);merged[next(iter(dst))].append(k)
verified={v['signal_uuid']:v for v in transition_proof['transitions']}
new_signal_vias={uid:o for uid,o in new.items()if uid not in old and o['kind']=='PCB_VIA'and o['net']!='LINK_AGND'}
assert set(new_signal_vias)=={v['uuid']for v in routing['vias']}
for uid,o in new_signal_vias.items():
 assert uid in verified,('unverified excluded transition',uid)
 v=verified[uid]
 assert v['signal_net']==o['net'] and v['signal_at']==o['position_mm'] and v['signal_native_group']==o['group']
 assert new[v['return_uuid']]['net']=='LINK_AGND' and new[v['return_uuid']]['group']==v['same_native_group']
merges=[]
for k,olds in merged.items():
 if len(olds)==1:continue
 net=old[b['all_groups'][olds[0]][0]]['net'];assert net.startswith('/A_DAC/')or net in routing['ADC_selected_nets']
 groups=[]
 for gid in olds:
  members=b['all_groups'][gid];assert all(old[u]['net']==net for u in members)
  groups.append({'group':gid,'all_member_uuids':members,'pads':[{k:old[u].get(k)for k in ['ref','pin','uuid','position_mm']}for u in members if old[u]['kind']=='PAD']})
 merges.append({'net':net,'old_groups':groups,'after_group':k})
assert {m['net']for m in merges}=={v['net']for v in routing['routes']if v['role']not in ['mount rework','mount via recenter','D101 supply stub recenter','authorized obstacle replacement']}
assert sum(len(m['old_groups'])-1 for m in merges)==230-routing['expected_opens']
main=next(o['group']for o in a['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20')
def refs(c):
 from shapely.strtree import STRtree
 fields=collections.defaultdict(list)
 for layer in c['copper_layers']:
  ground=[(o['group'],shape(o['layers'][layer]))for o in c['objects']if o['net']=='LINK_AGND'and o['group']and o['layers'].get(layer)]
  if not ground:continue
  gt=STRtree([g for _,g in ground]);polys=[];hits=[]
  for z in c['zones']:
   if z['net']!='LINK_AGND'or z['keepout']or z['layer']!=layer:continue
   for p in z['polygons']:
    g=Polygon(p['outer'],p['holes']);assert g.is_valid
    pad=g
    hits.append({ground[int(i)][0]for i in gt.query(pad)if pad.intersection(ground[int(i)][1]).area>1e-9});polys.append(g)
  tree=STRtree(polys);neighbors=[]
  for i,g in enumerate(polys):neighbors.append([int(j)for j in tree.query(g.buffer(2e-6))if int(j)!=i and g.distance(polys[int(j)])<=2e-6])
  for _ in range(len(polys)):
   updated=[h.union(*(hits[j]for j in ns))for h,ns in zip(hits,neighbors)]
   if updated==hits:break
   hits=updated
  for g,h in zip(polys,hits):
   if not h:continue
   assert len(h)==1,(layer,h)
   fields[(layer,next(iter(h)))].append(g)
 return {k:unary_union(v)for k,v in fields.items()}
f0,f1=refs(b),refs(a);layers=a['copper_layers']
def adjacent(layer):
 i=layers.index(layer);return{layers[j]for j in [i-1,i+1]if 0<=j<len(layers)}
def transition_holes(objects,net):
 hs=[]
 for o in objects.values():
  if o['net']!=net:continue
  if o['kind']=='PCB_VIA':hs.append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
  elif o['kind']=='PAD'and any(o['drill_mm']):
   hs.extend(shape(ps).buffer(.215)for ps in o['layers'].values()if ps)
 return unary_union(hs)
holes0={};holes1={};retained=[]
reference_before={l:unary_union([v for (ll,_),v in f0.items()if ll in adjacent(l)])for l in layers}
reference_after={l:unary_union([v for (ll,_),v in f1.items()if ll in adjacent(l)])for l in layers}
reference_after_numerical={l:p.buffer(fill_tol)for l,p in reference_after.items()}
new_fields={l:unary_union([p for (ll,gid),p in f1.items()if ll in adjacent(l)and gid==main]).buffer(2e-6)for l in layers}
from hardware.electronics.common.sexpr import read_sexpr,children,first
board_tree=read_sexpr((R.parent/'signal_input/native-r7/signal_main.kicad_pcb').read_text())
in1_zones=[z for z in children(board_tree,'zone')if not children(z,'keepout')and first(z,'layer')[1]=='In1.Cu'and first(z,'net')[1]=='LINK_AGND']
zone_parameters=[{'uuid':first(z,'uuid')[1],'clearance_mm':float(first(first(z,'connect_pads'),'clearance')[1]),'min_thickness_mm':float(first(z,'min_thickness')[1])}for z in in1_zones]
assert zone_parameters and all(z['clearance_mm']==.2 and z['min_thickness_mm']==.25 for z in zone_parameters)
for uid,o in old.items():
 if o['kind']!='PCB_TRACK'or o['net']=='LINK_AGND'or uid in removed:continue
 net=o['net'];layer,=o['layers'];adj=adjacent(layer)
 if net not in holes0:holes0[net]=transition_holes(old,net);holes1[net]=transition_holes(new,net)
 g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes0[net])
 before=reference_before[layer];afterfield=reference_after[layer];covered=g.intersection(before)
 lost=covered.difference(afterfield);raw_loss=lost.area
 remainder=covered.difference(reference_after_numerical[layer]);numerical_area=raw_loss-remainder.area
 linked=[]
 if (layer=='F.Cu' or (layer in ['In3.Cu','In5.Cu']and net=='/D_LED/LED_39')) and not remainder.is_empty:
  for vuid,via in new_signal_vias.items():
   if via['net']!=net or via['group']!=new[uid]['group']:continue
   contact=shape(o['layers'][layer]).intersection(shape(via['layers'][layer])).area
   if contact<=1e-9:continue
   radius=via['width_mm']/2+.2+.25/2+fill_tol
   region=remainder.intersection(Point(via['position_mm']).buffer(radius))
   if region.area<=1e-9:continue
   linked.append({'via_uuid':vuid,'signal_net':net,'signal_group':via['group'],'old_track_copper_contact_mm2':contact,'return_uuid':verified[vuid]['return_uuid'],'verified_return_length_mm':verified[vuid]['verified_return_corridor_length_mm'],'native_knockout_pruning_envelope_radius_mm':radius,'attributed_loss_mm2':region.area})
   remainder=remainder.difference(region)
 if covered.area>1e-8:retained.append({'uuid':uid,'net':net,'layer':layer,'previous_covered_mm2':covered.area,'lost_mm2':raw_loss,'native_polygonization_boundary_change_mm2':numerical_area,'linked_new_transition_losses':linked,'unexplained_loss_mm2':remainder.area})
sensitive={o['net']for o in b['objects']if o.get('ref')in ['A_U301','A_U302','A_U303','A_U304']and o.get('pin')in ['2','6']}
lowcap_zones=[z for z in b['zones']if z['keepout']and not z['prohibit_tracks']and z['layer']=='In1.Cu']
lowcap=unary_union([shape(z['polygons'])for z in lowcap_zones])
from hardware.cad.two_board_sensor_05.signal_dac.sensitive_placement import validated_exclusions
transported=validated_exclusions(b,a,routing['supplemental_lowcap_exclusions'])
newrefs=[]
for v in routing['routes']:
 if v['net']not in holes1:holes1[v['net']]=transition_holes(new,v['net'])
 net=v['net'];g=LineString(v['path_mm']).buffer(v['width_mm']/2).difference(holes1[net]);field=new_fields[v['layer']];missing=g.difference(field)
 oldcopper=unary_union([shape(o['layers'][v['layer']])for o in b['objects']if o['net']==net and o['layers'].get(v['layer'])])
 introduced=missing.difference(oldcopper)
 intentional=unary_union([shape(ps).buffer(.5)for o in b['objects']if o['net']==net for l,ps in o['layers'].items()if l in ['F.Cu','B.Cu']and ps]).intersection(lowcap)if net in sensitive and v['layer']=='F.Cu'else Point().buffer(0)
 transport=unary_union([x['geometry']for x in transported if x['net']==net])if v['layer']=='F.Cu'else Point().buffer(0)
 accepted_lowcap=introduced.intersection(intentional);accepted_transported=introduced.difference(intentional).intersection(transport);unexplained=introduced.difference(intentional).difference(transport)
 newrefs.append({'name':net+' '+v['role'],'layer':v['layer'],'raw_uncovered_mm2':missing.area,'existing_copper_uncovered_mm2':missing.intersection(oldcopper).area,'source_derived_sensitive_exclusion_mm2':accepted_lowcap.area,'transported_sensitive_pad_exclusion_mm2':accepted_transported.area,'unexplained_uncovered_mm2':unexplained.area,'unexplained_bounds':list(unexplained.bounds)if not unexplained.is_empty else[],'source_keepouts':[z['uuid']for z in lowcap_zones if accepted_lowcap.intersection(shape(z['polygons'])).area>1e-9],'lowcap_noise_or_stability_qualified':False})
oldzones={z['uuid']for z in b['zones']};contacts=[]
for z in a['zones']:
 if z['uuid']in oldzones or z['keepout']:continue
 g=shape(z['polygons']);hit=[]
 for o in b['objects']:
  if o['net']=='LINK_AGND'and o['layers'].get(z['layer'])and g.intersection(shape(o['layers'][z['layer']])).area>1e-9:hit.append({k:o.get(k)for k in ['uuid','ref','pin','position_mm','kind','group']})
 contacts.append({'zone':z['uuid'],'layer':z['layer'],'authored_outline':z['authored_outline'],'filled_area_mm2':g.area,'contacts':hit,'existing_zone_overlap_mm2':sum(g.intersection(shape(zz['polygons'])).area for zz in b['zones']if zz['net']=='LINK_AGND'and zz['layer']==z['layer'])})

paths=[Path(__file__),R/'sensitive_placement.py',R/'candidate-r53/routing.json',R/'native-r146/review.json',R.parent/'signal_input/capture-r7/capture.json',R/'capture-r146/capture.json',R/'candidate-r146/routing.json',R/'candidate-r139/routing.json',R/'candidate-r98/routing.json',R/'candidate-r107/routing.json',R/'candidate-r125/routing.json',R/'candidate-r131/routing.json',R/'transitions-r146.json',R/'capture-r146/precision.json',R/'REFERENCE-POLICY.md',REPO/'hardware/fabrication/audio_main_ground.py',REPO/'hardware/electronics/dac_receiver/README.md']
report={'verified_transported_pad_exclusions':[{k:v for k,v in x.items()if k!='geometry'}for x in transported],'scope':'Source-bound reference geometry screen with explicit low-capacitance and physically connected transition accounting; no noise/stability qualification','source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'all_original_native_groups_preserved':True,'only_approved_net_groups_merged':merges,'new_reference_cases':newrefs,'new_ground_contacts':contacts,'retained_reference_cases':retained,'maximum_retained_loss_mm2':max(x['lost_mm2']for x in retained),'full_noise_acceptance':False,'all_new_signal_via_holes_have_uuid_bound_return_proof':sorted(new_signal_vias),'native_polygonization_boundary_tolerance_mm':fill_tol,'new_route_field_tolerance_mm':2e-6,'native_transition_zone_parameters':zone_parameters}
(R/'reference-review-r146.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'new_refs':newrefs,'retained_cases':len(retained),'max_loss':report['maximum_retained_loss_mm2'],'ground_contacts':contacts},indent=2)[:3500]);assert all(v['unexplained_uncovered_mm2']<1e-6 for v in newrefs);assert all(v['unexplained_loss_mm2']<1e-6 for v in retained);print('PASS',len(newrefs),'new route cases',len(retained),'retained reference cases')
