"""Bounded ground corridor and native filled-field delta audit for PD_R."""
import collections,hashlib,json
from pathlib import Path
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
b=read(R/'capture-r139/capture.json');c=read(R/'capture-r148/capture.json');r=read(R/'candidate-r148/routing.json');t=read_sexpr((R/'native-r148/signal_main.kicad_pcb').read_text())
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
 patch=Polygon(declared['boundary_mm']);zone=next(z for z in c['zones']if z['uuid']==declared['uuid']);actual=shape(zone['polygons']);assert zone['layer']==declared['layer'] and zone['net']=='LINK_AGND';assert shape(zone['authored_outline']).symmetric_difference(patch).area<1e-9
 new=next(z for z in children(t,'zone')if first(z,'uuid')[1]==declared['uuid']);proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]==declared['prototype_uuid']);assert parameters(new)==parameters(proto)and first(new,'net')[1]=='LINK_AGND';assert float(first(new,'min_thickness')[1])==.25 and float(first(first(new,'connect_pads'),'clearance')[1])==.2
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
precision=read(R/'capture-r148/precision.json');assert precision['boards']['after']['max_polygonization_error_mm']==.005
projection=unary_union([Polygon(z['boundary_mm'])for z in r['new_reference_zones']])
via_scope=unary_union([Point(v['at']).buffer(.63)for v in r['vias']+r['new_ground_vias']]);rows=[]
for key in sorted(fields[0].keys()|fields[1].keys()):
 old=fields[0].get(key,Polygon());after=fields[1].get(key,Polygon());lost=old.difference(after);gain=after.difference(old);layer=key[1]
 parts=[via_scope]
 for route in r['routes']:
  if route['layer']!=layer:continue
  parts.append(LineString(route['path_mm']).buffer(route['width_mm']/2+.33))
  if 'before_path_mm'in route:parts.append(LineString(route['before_path_mm']).buffer(route['width_mm']/2+.33))
 if key[0]=='LINK_AGND':parts.extend(Polygon(z['boundary_mm']).buffer(.005)for z in r['new_reference_zones']if z['layer']==layer)
 scope=unary_union(parts);raw=lost.union(gain).difference(scope).area
 # Native minimum-width cleanup can reconnect an existing authored ground sliver
 # at a new same-net patch contact. Only gains inside unchanged old outlines and
 # within min_thickness/2 + native precision (0.125 + 0.005 mm) are permitted.
 old_authored=unary_union([shape(z['authored_outline'])for z in b['zones']if not z['keepout']and(z['net'],z['layer'])==key])
 cleanup=unary_union([Polygon(z['boundary_mm']).buffer(.13)for z in r['new_reference_zones']if z['layer']==layer]).intersection(old_authored)if key[0]=='LINK_AGND'else Polygon()
 local_guard=projection.union(cleanup).intersection(old_authored).intersection(old.buffer(.005))if key[0]=='LINK_AGND'else Polygon()
 boundary_gain=after.difference(old.buffer(2e-6)).difference(scope);attributed=boundary_gain.intersection(local_guard);witnesses=[];mapped=[]
 for zone in b['zones']:
  if zone['keepout']or(zone['net'],zone['layer'])!=key:continue
  for index,auth in enumerate(zone['authored_outline']):
   native_boundary=shape(zone['polygons']).buffer(.005);piece=attributed.intersection(shape([auth])).intersection(native_boundary)
   if piece.area<=1e-12:continue
   pieces=list(piece.geoms)if piece.geom_type=='MultiPolygon'else[piece];polys=[{'outer':list(x.exterior.coords)[:-1],'holes':[list(h.coords)[:-1]for h in x.interiors]}for x in pieces if x.geom_type=='Polygon'];mapped.append(piece)
   witnesses.append({'existing_zone_uuid':zone['uuid'],'authored_polygon_index':index,'native_boundary_distance_limit_mm':.005,'local_gained_area_mm2':piece.area,'raw_gain_polygons':polys})
 assert attributed.difference(unary_union(mapped)).area<1e-8
 for keep in b['zones']:
  if keep['keepout']and keep['layer']==layer:assert attributed.intersection(shape(keep['polygons']).buffer(-2e-6)).area<1e-8
 unexplained=old.difference(after.buffer(2e-6)).difference(scope).area+boundary_gain.difference(local_guard).area
 assert unexplained<1e-8,(key,lost.area,gain.area,raw,unexplained)
 if lost.area+gain.area>1e-9:rows.append({'net':key[0],'layer':layer,'lost_mm2':lost.area,'gained_mm2':gain.area,'raw_outside_primary_scope_mm2':raw,'source_bound_local_boundary_gain_mm2':attributed.area,'exact_old_polygon_gain_witnesses':witnesses,'outside_scope_after_2nm_capture_mm2':unexplained})
paths=[Path(__file__),R/'candidate-r148/routing.json',R/'capture-r139/capture.json',R/'capture-r148/capture.json',R/'native-r148/signal_main.kicad_pcb',R/'capture-r148/precision.json']
report={'pass':True,'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'patches':patches,'main_ground_group':main,'saved_fill_changes':rows,'new_patch_fill_does_not_cross_original_keepouts':True,'no_unexplained_remote_fill_changes':True,'capture_boundary_tolerance_mm':2e-6,'native_min_width_cleanup_gain_radius_mm':.13,'cleanup_gains_require_unchanged_old_ground_outline':True,'boundary_gains_require_local_patch_projection_and_exact_old_polygon':True,'no_global_native_tolerance_waiver':True,'noise_qualified':False,'fabrication_released':False}
(R/'patch-audit-r148.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS exact connected patches, preserved original keepouts, local saved-fill changes',rows)
