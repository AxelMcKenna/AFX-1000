"""Bounded ground corridor and native filled-field delta audit for PD_R."""
import collections,hashlib,json
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
b=read(R/'capture-r139/capture.json');c=read(R/'capture-r146/capture.json');r=read(R/'candidate-r146/routing.json');t=read_sexpr((R/'native-r146/signal_main.kicad_pcb').read_text())
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


main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20');ground=refs(c);patches=[]
def parameters(v):return sexpr([x for x in v if not(isinstance(x,list)and x and x[0]in ['uuid','polygon','filled_polygon','priority','layer'])])
for declared in r['new_reference_zones']:
 patch=Polygon(declared['boundary_mm']);zone=next(z for z in c['zones']if z['uuid']==declared['uuid']);actual=shape(zone['polygons']);assert shape(zone['authored_outline']).symmetric_difference(patch).area<1e-9
 new=next(z for z in children(t,'zone')if first(z,'uuid')[1]==declared['uuid']);proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]==declared['prototype_uuid']);assert parameters(new)==parameters(proto)and first(new,'net')[1]=='LINK_AGND'
 assert actual.area>0 and actual.difference(ground[(zone['layer'],main)].buffer(2e-6)).area<1e-8
 for keep in b['zones']:
  if keep['layer']==zone['layer']and keep['keepout']:assert actual.intersection(shape(keep['polygons']).buffer(-2e-6)).area<1e-8,keep['uuid']
 anchors=[{'uuid':o['uuid'],'kind':o['kind'],'group':o['group'],'area_mm2':actual.intersection(shape(o['layers'][zone['layer']])).area}for o in c['objects']if o['net']=='LINK_AGND'and o['layers'].get(zone['layer'])and actual.intersection(shape(o['layers'][zone['layer']])).area>1e-8];assert anchors and all(o['group']==main for o in anchors)
 patches.append({'declared':declared,'actual_area_mm2':actual.area,'same_main_ground_anchors':anchors})
fields=[]
for capture in [b,c]:
 grouped=collections.defaultdict(list)
 for zone in capture['zones']:
  if not zone['keepout']:grouped[(zone['net'],zone['layer'])].append(shape(zone['polygons']))
 fields.append({k:unary_union(v)for k,v in grouped.items()})
via_scope=unary_union([Point(v['at']).buffer(.63)for v in r['vias']+r['new_ground_vias']]);rows=[]
for key in fields[0].keys()|fields[1].keys():
 old=fields[0].get(key,Polygon());after=fields[1].get(key,Polygon());lost=old.difference(after);gain=after.difference(old);layer=key[1]
 parts=[via_scope]
 for route in r['routes']:
  if route['layer']!=layer:continue
  parts.append(LineString(route['path_mm']).buffer(route['width_mm']/2+.33))
  if 'before_path_mm'in route:parts.append(LineString(route['before_path_mm']).buffer(route['width_mm']/2+.33))
 if key[0]=='LINK_AGND':parts.extend(Polygon(z['boundary_mm']).buffer(.005)for z in r['new_reference_zones']if z['layer']==layer)
 scope=unary_union(parts);raw=lost.union(gain).difference(scope).area;unexplained=old.difference(after.buffer(2e-6)).union(after.difference(old.buffer(2e-6))).difference(scope).area
 assert unexplained<1e-8,(key,lost.area,gain.area,raw,unexplained)
 if lost.area+gain.area>1e-9:rows.append({'net':key[0],'layer':layer,'lost_mm2':lost.area,'gained_mm2':gain.area,'raw_outside_scope_mm2':raw,'outside_scope_after_2nm_capture_mm2':unexplained})
paths=[Path(__file__),R/'candidate-r146/routing.json',R/'capture-r139/capture.json',R/'capture-r146/capture.json',R/'native-r146/signal_main.kicad_pcb']
report={'pass':True,'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'patches':patches,'main_ground_group':main,'saved_fill_changes':rows,'new_patch_fill_does_not_cross_original_keepouts':True,'no_unexplained_remote_fill_changes':True,'capture_boundary_tolerance_mm':2e-6,'noise_qualified':False,'fabrication_released':False}
(R/'patch-audit-r146.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS exact connected patches, preserved original keepouts, local saved-fill changes',rows)
