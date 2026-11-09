"""Measure retained and new adjacent-ground coverage of the startup-reference candidate."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-support-references-native-01'
OUT=STAGING/'two-board-power-startup-references-native-04'
BEFORE=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2210-startup-references-04/capture.json'

def run():
 auditpath=OUT/'startup-reference-review.json';audit=json.loads(auditpath.read_text());assert audit['all_native_groups_preserved']
 before=json.loads(BEFORE.read_text());after=json.loads(AFTER.read_text());r=json.loads((OUT/'startup-reference-routing.json').read_text());retired=set(r['retired_objects'])
 aliases=audit['generated_pad_identity_aliases']
 for o in after['objects']:o['uuid']=aliases.get(o['uuid'],o['uuid']);o['group']=aliases.get(o['group'],o['group'])
 old,new=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
 def hits(g,layer,cap):return [o for o in cap['objects'] if o['net']=='PWR_AGND' and o['layers'].get(layer) and g.buffer(.0015).intersection(shape(o['layers'][layer])).area>1e-9]
 def references(c):
  regions={}
  for z in c['zones']:
   if z['net']!='PWR_AGND':continue
   for p in z['polygons']:
    g=Polygon(p['outer'],p['holes']);contact=hits(g,z['layer'],c)
    if not contact:continue
    groups={o['group'] for o in contact};assert len(groups)==1
    regions.setdefault((z['layer'],next(iter(groups))),[]).append(g)
  return {key:unary_union(ps) for key,ps in regions.items()}
 refs0,refs1=references(before),references(after);coverage=[];layers=after['copper_layers']
 def holes(objects,plated=False):
  rows={}
  for o in objects.values():
   if o['kind']=='PCB_VIA':rows.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
   elif plated and o['kind']=='PAD' and any(o['drill_mm']):
    for ps in o['layers'].values():
     if ps:rows.setdefault(o['net'],[]).append(shape(ps).buffer(.215))
  return {net:unary_union(gs) for net,gs in rows.items()}
 oldholes=holes(old);newholes=holes(new,plated=True)
 addedviaids={v['uuid'] for v in r['vias']}
 retainedholes=holes({u:o for u,o in new.items() if u not in addedviaids})
 retained_transition_contacts=[]
 for u,o in old.items():
  if u in retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)};g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  if o['net'] in oldholes:g=g.difference(oldholes[o['net']])
  if g.is_empty:continue
  # Compare each board against its actual transition geometry. A newly added
  # via may exclude its standard clearance only where it physically intersects
  # this retained trace and belongs to the same native connection group.
  raw=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  current=raw.difference(retainedholes.get(o['net'],Polygon()))
  actual_layer=next(iter(o['layers']))
  for vid in addedviaids:
   v=new[vid]
   if v['net']!=o['net']:continue
   overlap=shape(new[u]['layers'][actual_layer]).intersection(shape(v['layers'][actual_layer])).area
   if overlap<=1e-9:continue
   assert v['group']==new[u]['group'] and v['group']
   current=current.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
   retained_transition_contacts.append(dict(track_uuid=u,via_uuid=vid,native_group=v['group'],copper_overlap_mm2=overlap,clearance_exclusion_radius_mm=v['width_mm']/2+.215))
  for (layer,gid),reference in refs0.items():
   if layer not in adj or g.difference(reference.buffer(.0015)).area>=1e-6:continue
   anchors=[x for x in before['all_groups'][gid] if x in new];assert anchors
   target=refs1[(layer,new[anchors[0]]['group'])];area=current.difference(target.buffer(.0015)).area
   coverage.append(dict(track_uuid=u,net=o['net'],reference_layer=layer,uncovered_mm2=area))
 main=next(o['group'] for o in new.values() if o.get('ref')=='P_C103' and o.get('pin')=='2');newrefs=[]
 for route in r['routes']:
  if route['net']=='PWR_AGND':continue
  layer=route['layer'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
  g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  if route['net'] in newholes:g=g.difference(newholes[route['net']])
  target=unary_union([v for (l,gid),v in refs1.items() if l in adj and gid==main]);missing=g.difference(target.buffer(.0015))
  newrefs.append(dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),net=route['net'],layer=layer,adjacent_ground_layers=sorted(l for l,gid in refs1 if l in adj and gid==main),screened_area_mm2=g.area,uncovered_mm2=missing.area))
 planpath=STAGING/'two-board-startup-reference-plan-01/reference-plan.json'
 targeted=[];routebylabel={rr['label']:rr for rr in r['routes']}
 replacement_labels={'E_U33.1':['E_U33.1 replacement'],'E_U16.3':['E_U16.3 replacement'],'E_U15.3':['E_U15.3 replacement'],'E_R103.1':['E_R103.1 replacement'],
                     'E_R107.1':['E_R107.1 replacement','DIG_PG1 inner continuation']}
 def measure(rr,cap,fields,viaholes,ownerzones=None):
  layer=rr['layer'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
  g=LineString(rr['path_mm']).buffer(rr['width_mm']/2)
  if rr['net'] in viaholes:g=g.difference(viaholes[rr['net']])
  if ownerzones is None:field=unary_union([f for (l,gid),f in fields.items() if l in adj])
  else:field=unary_union([shape(z['polygons']) for z in cap['zones'] if z['uuid'] in ownerzones and z['layer'] in adj])
  missing=g.difference(field.buffer(.0015))
  return dict(uncovered_mm2=missing.area,missing_bounds=list(missing.bounds) if not missing.is_empty else [])
 for rec in json.loads(planpath.read_text())['remaining_paths']:
  before_result=measure(rec['route'],before,refs0,oldholes)
  if rec['label'] in replacement_labels:current=[routebylabel[label] for label in replacement_labels[rec['label']]]
  else:
   current=[rec['route']]
   assert all(uid in new and uid not in retired for uid in rec['route']['segment_uuids'])
  after_results=[dict(label=rr.get('label',rec['label']),layer=rr['layer'],**measure(rr,after,refs1,newholes)) for rr in current]
  targeted.append(dict(label=rec['label'],before_uncovered_mm2=before_result['uncovered_mm2'],replacement_paths=after_results,
                       after_uncovered_mm2=sum(row['uncovered_mm2'] for row in after_results)))
 localpath=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json'
 replacepath=STAGING/'two-board-power-digital-reference-native-02/digital-reference-track-routing.json'
 supportpath=BASE/'support-reference-routing.json'
 quietpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json'
 rep=json.loads(replacepath.read_text());own={q['ref']:q['zone_uuids'] for q in json.loads(quietpath.read_text())['quiet_ground_islands']}
 supports={frozenset(rr['previous_route']['segment_uuids']):rr for rr in json.loads(supportpath.read_text())['routes']}
 ownerparts={ref:chip for chip,parts in {'E_U15':['E_U15','E_R105','E_R106','E_C43'],'E_U16':['E_U16','E_R109','E_R110','E_C45'],'E_U17':['E_U17','E_R113','E_R114','E_C47'],'E_U33':['E_U33','E_R121','E_R122','E_C51']}.items() for ref in parts}
 ownrefs=[]
 for rr in json.loads(localpath.read_text())['routes']:
  if rr.get('label')==rep['retired_route']['label']:rr=rep['replacement_route']
  if rr['net'] in ['PWR_AGND','PWR_5V_DIG_SRC']:continue
  chip=rr.get('chip',ownerparts.get(rr.get('ref')));assert chip in own
  rr=supports.get(frozenset(rr['segment_uuids']),rr)
  assert all(uid in old and uid in new for uid in rr['segment_uuids'])
  b=measure(rr,before,refs0,oldholes,own[chip]);a=measure(rr,after,refs1,newholes,own[chip])
  assert b['uncovered_mm2']<1e-6
  ownrefs.append(dict(label=rr.get('label',rr.get('ref','')+'.'+rr.get('pin','')),owner=chip,before_uncovered_mm2=b['uncovered_mm2'],**a))
 assert len(targeted)==8 and len(ownrefs)==22
 sources=[Path(__file__),BEFORE,AFTER,auditpath,OUT/'startup-reference-routing.json',planpath,localpath,replacepath,supportpath,quietpath,REPO/'hardware/fabrication/route_nf_surface.py']
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retained_reference_cases=coverage,
             retained_trace_new_transition_contacts=retained_transition_contacts,
             retained_reference_complete=all(x['uncovered_mm2']<1e-6 for x in coverage),new_non_ground_paths=newrefs,
             new_reference_complete=all(x['uncovered_mm2']<1e-6 for x in newrefs),startup_paths=targeted,
             startup_references_complete=all(x['after_uncovered_mm2']<1e-6 for x in targeted),
             digital_own_quiet_paths=ownrefs,digital_own_quiet_reference_complete=all(x['uncovered_mm2']<1e-6 for x in ownrefs),
             same_net_via_and_plated_pad_clearance_exclusions=True,projection_only=True,loaded_current_timing_noise_qualified=False,fabrication_released=False)
 with (OUT/'startup-reference-coverage.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(retained_cases=len(coverage),retained_gaps=[x for x in coverage if x['uncovered_mm2']>=1e-6],
     new_paths=len(newrefs),new_gaps=[x for x in newrefs if x['uncovered_mm2']>=1e-6],
     startup_gaps=[x for x in targeted if x['after_uncovered_mm2']>=1e-6],
     own_quiet_gaps=[x for x in ownrefs if x['uncovered_mm2']>=1e-6])),flush=True)
if __name__=='__main__':run()
