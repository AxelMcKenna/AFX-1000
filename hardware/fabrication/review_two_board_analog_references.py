"""Measure retained and new adjacent-ground coverage of the analog candidate."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-permission-native-04'
OUT=STAGING/'two-board-power-analog-cells-native-02'
BEFORE=STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json'
AFTER=STAGING/'two-board-power-routing-inputs-2211-analog-cells-02/capture.json'

def run():
 auditpath=OUT/'analog-connectivity-review.json';audit=json.loads(auditpath.read_text());assert audit['all_other_native_groups_preserved']
 before=json.loads(BEFORE.read_text());after=json.loads(AFTER.read_text());r=json.loads((OUT/'analog-cell-routing.json').read_text());retired=set(r['retired_objects'])
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
 sources=[Path(__file__),BEFORE,AFTER,auditpath,OUT/'analog-cell-routing.json',REPO/'hardware/fabrication/route_nf_surface.py']
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retained_reference_cases=coverage,retained_reference_complete=all(x['uncovered_mm2']<1e-6 for x in coverage),new_non_ground_paths=newrefs,new_reference_complete=all(x['uncovered_mm2']<1e-6 for x in newrefs),own_quiet_reference_complete=audit['own_quiet_reference_complete'],same_net_via_and_plated_pad_clearance_exclusions=True,projection_only=True,loaded_current_timing_noise_qualified=False,fabrication_released=False)
 with (OUT/'analog-reference-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(retained_cases=len(coverage),retained_gaps=[x for x in coverage if x['uncovered_mm2']>=1e-6],new_paths=len(newrefs),new_gaps=[x for x in newrefs if x['uncovered_mm2']>=1e-6],own_quiet_reference_complete=result['own_quiet_reference_complete'])),flush=True)
if __name__=='__main__':run()
