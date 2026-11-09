"""Measure retained and new adjacent-ground coverage of the support-reference candidate."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-digital-return-native-03'
OUT=STAGING/'two-board-power-support-references-native-01'
BEFORE=STAGING/'two-board-power-routing-inputs-2210-digital-return-03/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'

def run():
 auditpath=OUT/'support-reference-review.json';audit=json.loads(auditpath.read_text());assert audit['all_native_groups_preserved']
 before=json.loads(BEFORE.read_text());after=json.loads(AFTER.read_text());r=json.loads((OUT/'support-reference-routing.json').read_text());retired=set(r['retired_objects'])
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
 for u,o in old.items():
  if u in retired or o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
  layer,=o['layers'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)};g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  if o['net'] in oldholes:g=g.difference(oldholes[o['net']])
  if g.is_empty:continue
  for (layer,gid),reference in refs0.items():
   if layer not in adj or g.difference(reference.buffer(.0015)).area>=1e-6:continue
   anchors=[x for x in before['all_groups'][gid] if x in new];assert anchors
   target=refs1[(layer,new[anchors[0]]['group'])];area=g.difference(target.buffer(.0015)).area
   coverage.append(dict(track_uuid=u,net=o['net'],reference_layer=layer,uncovered_mm2=area))
 main=next(o['group'] for o in new.values() if o.get('ref')=='P_C103' and o.get('pin')=='2');newrefs=[]
 for route in r['routes']:
  if route['net']=='PWR_AGND':continue
  layer=route['layer'];i=layers.index(layer);adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
  g=LineString(route['path_mm']).buffer(route['width_mm']/2)
  if route['net'] in newholes:g=g.difference(newholes[route['net']])
  target=unary_union([v for (l,gid),v in refs1.items() if l in adj and gid==main]);missing=g.difference(target.buffer(.0015))
  newrefs.append(dict(label=route.get('label',route.get('ref','')+'.'+route.get('pin','')),net=route['net'],layer=layer,adjacent_ground_layers=sorted(l for l,gid in refs1 if l in adj and gid==main),screened_area_mm2=g.area,uncovered_mm2=missing.area))
 # Preserve the existing incomplete reference geometry as well as complete
 # cases; this prevents a new change from hiding behind an earlier open gap.
 legacy_path=STAGING/'two-board-digital-return-plan-01/retained-reference-diagnosis.json'
 legacy=[]
 replacements={frozenset(rr['previous_route']['segment_uuids']):rr for rr in r['routes']}
 for rec in json.loads(legacy_path.read_text())['gaps']:
  rr=rec['route'];replacement=replacements.get(frozenset(rr['segment_uuids']));layer=rec['reference_layer'];g=LineString(rr['path_mm']).buffer(rr['width_mm']/2)
  if rr['net'] in oldholes:g=g.difference(oldholes[rr['net']])
  misses=[]
  for ii,refs in enumerate([refs0,refs1]):
   projection=g
   if ii and replacement:
    projection=LineString(replacement['path_mm']).buffer(replacement['width_mm']/2)
    if rr['net'] in newholes:projection=projection.difference(newholes[rr['net']])
   field=unary_union([v for (l,gid),v in refs.items() if l==layer])
   misses.append(projection.difference(field.buffer(.0015)))
  regression=misses[1].difference(misses[0].buffer(.000002)).area
  legacy.append(dict(label=rec['label'],repaired=replacement is not None,before_uncovered_mm2=misses[0].area,after_uncovered_mm2=misses[1].area,regression_mm2=regression))
 localpath=STAGING/'two-board-power-digital-cells-native-03/digital-cell-routing.json'
 replacepath=STAGING/'two-board-power-digital-reference-native-02/digital-reference-track-routing.json'
 quietpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json'
 rep=json.loads(replacepath.read_text());own={q['ref']:q['zone_uuids'] for q in json.loads(quietpath.read_text())['quiet_ground_islands']}
 ownerparts={ref:chip for chip,refs in {'E_U15':['E_U15','E_R105','E_R106','E_C43'],'E_U16':['E_U16','E_R109','E_R110','E_C45'],'E_U17':['E_U17','E_R113','E_R114','E_C47'],'E_U33':['E_U33','E_R121','E_R122','E_C51']}.items() for ref in refs}
 ownrefs=[]
 for rr in json.loads(localpath.read_text())['routes']:
  if rr.get('label')==rep['retired_route']['label']:rr=rep['replacement_route']
  if rr['net'] in ['PWR_AGND','PWR_5V_DIG_SRC']:continue
  chip=rr.get('chip',ownerparts.get(rr.get('ref')));assert chip in own
  layer={'F.Cu':'In1.Cu','B.Cu':'In6.Cu'}[rr['layer']];g=LineString(rr['path_mm']).buffer(rr['width_mm']/2)
  if rr['net'] in oldholes:g=g.difference(oldholes[rr['net']])
  misses=[]
  replacement=replacements.get(frozenset(rr['segment_uuids']))
  for ii,cap in enumerate([before,after]):
   projection=g
   if ii and replacement:
    projection=LineString(replacement['path_mm']).buffer(replacement['width_mm']/2)
    if rr['net'] in newholes:projection=projection.difference(newholes[rr['net']])
   fields=unary_union([shape(z['polygons']) for z in cap['zones'] if z['uuid'] in own[chip] and z['layer']==layer]);misses.append(projection.difference(fields.buffer(.0015)))
  regression=misses[1].difference(misses[0].buffer(.000002)).area
  ownrefs.append(dict(label=rr.get('label',rr.get('ref','')+'.'+rr.get('pin','')),owner=chip,before_uncovered_mm2=misses[0].area,after_uncovered_mm2=misses[1].area,regression_mm2=regression))
 assert len(legacy)==12 and len(ownrefs)==22
 assert sum(x['repaired'] for x in legacy)==4
 assert all(x['after_uncovered_mm2']<1e-6 for x in legacy if x['repaired'])
 sources=[Path(__file__),BEFORE,AFTER,auditpath,OUT/'support-reference-routing.json',REPO/'hardware/fabrication/route_nf_surface.py',legacy_path,localpath,replacepath,quietpath]
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retained_reference_cases=coverage,retained_reference_complete=all(x['uncovered_mm2']<1e-6 for x in coverage),new_non_ground_paths=newrefs,new_reference_complete=all(x['uncovered_mm2']<1e-6 for x in newrefs),own_quiet_reference_preserved=all(x['regression_mm2']<1e-6 for x in ownrefs),own_quiet_reference=ownrefs,legacy_incomplete_paths_preserved=all(x['regression_mm2']<1e-6 for x in legacy),legacy_incomplete_paths=legacy,legacy_paths_repaired=4,remaining_legacy_reference_gaps=sum(x['after_uncovered_mm2']>=1e-6 for x in legacy),own_quiet_reference_complete=all(x['after_uncovered_mm2']<1e-6 for x in ownrefs),same_net_via_and_plated_pad_clearance_exclusions=True,projection_only=True,loaded_current_timing_noise_qualified=False,fabrication_released=False)
 with (OUT/'support-reference-coverage.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(retained_cases=len(coverage),retained_gaps=[x for x in coverage if x['uncovered_mm2']>=1e-6],new_paths=len(newrefs),new_gaps=[x for x in newrefs if x['uncovered_mm2']>=1e-6],own_quiet_reference_preserved=result['own_quiet_reference_preserved'],own_quiet_reference_complete=result['own_quiet_reference_complete'],legacy_paths_repaired=4,remaining_legacy_reference_gaps=result['remaining_legacy_reference_gaps'],legacy_incomplete_paths_preserved=result['legacy_incomplete_paths_preserved'])),flush=True)
if __name__=='__main__':run()
