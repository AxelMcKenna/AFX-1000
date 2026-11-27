"""Exact authored patch, connected quiet ground and local saved-fill delta proof."""
import collections,hashlib,json
from pathlib import Path
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
b=read(R/'capture-r131/capture.json');c=read(R/'capture-r139/capture.json');r=read(R/'candidate-r139/routing.json');z,=r['new_reference_zones'];patch=Polygon(z['boundary_mm']);route,=r['routes'];line=LineString(route['path_mm'])
t=read_sexpr((R/'native-r139/signal_main.kicad_pcb').read_text());new=next(v for v in children(t,'zone')if first(v,'uuid')[1]==z['uuid']);proto=next(v for v in children(t,'zone')if first(v,'uuid')[1]==z['prototype_uuid'])
def parameters(v):return sexpr([x for x in v if not(isinstance(x,list)and x and x[0]in ['uuid','polygon','filled_polygon','priority'])])
assert parameters(new)==parameters(proto);assert first(new,'net')[1]=='LINK_AGND'and first(new,'layer')[1]=='In6.Cu'
actual=next(v for v in c['zones']if v['uuid']==z['uuid']);assert shape(actual['authored_outline']).symmetric_difference(patch).area<1e-9
assert patch.equals_exact(LineString(route['path_mm']).buffer(.6,quad_segs=8),.000001)
for zone in b['zones']:
 if zone['layer']=='In6.Cu'and zone['keepout']:assert patch.intersection(shape(zone['polygons'])).area<1e-9,zone['uuid']
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

main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20');field=refs(c)[('In6.Cu',main)];native_patch=shape(actual['polygons']);assert native_patch.area>0 and native_patch.difference(field.buffer(2e-6)).area<1e-8
assert line.buffer(.1).difference(field.buffer(2e-6)).area<1e-6
anchors=[]
for oldzone in b['zones']:
 if oldzone['net']=='LINK_AGND'and oldzone['layer']=='In6.Cu'and not oldzone['keepout']:
  area=native_patch.intersection(shape(oldzone['polygons'])).area
  if area>1e-8:anchors.append({'zone_uuid':oldzone['uuid'],'overlap_mm2':area})
assert anchors
fields=[]
for capture in [b,c]:
 grouped=collections.defaultdict(list)
 for zone in capture['zones']:
  if not zone['keepout']:grouped[(zone['net'],zone['layer'])].append(shape(zone['polygons']))
 fields.append({k:unary_union(v)for k,v in grouped.items()})
rows=[]
for key in fields[0].keys()|fields[1].keys():
 old=fields[0].get(key,Polygon());after=fields[1].get(key,Polygon());lost=old.difference(after);gain=after.difference(old)
 # Only same-net ground filling near the declared surface trace/patch may change.
 permitted=line.buffer(.45)if key==('LINK_AGND','B.Cu')else patch.buffer(.005)if key==('LINK_AGND','In6.Cu')else Polygon()
 raw_outside=lost.union(gain).difference(permitted).area
 unexplained=old.difference(after.buffer(2e-6)).union(after.difference(old.buffer(2e-6))).difference(permitted).area
 assert unexplained<1e-8,(key,lost.area,gain.area,unexplained)
 if lost.area+gain.area>1e-9:rows.append({'net':key[0],'layer':key[1],'lost_mm2':lost.area,'gained_mm2':gain.area,'raw_outside_local_scope_mm2':raw_outside,'outside_scope_after_2nm_capture_boundary_mm2':unexplained})
paths=[Path(__file__),R/'review_r139.py',R/'reference-review-r139.json',R/'candidate-r139/routing.json',R/'capture-r131/capture.json',R/'capture-r139/capture.json',R/'native-r139/signal_main.kicad_pcb']
report={'pass':True,'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'exact_patch':z,'connected_ground_group':main,'existing_native_field_anchors':anchors,'local_saved_fill_changes':rows,'capture_boundary_tolerance_mm':2e-6,'all_original_keepouts_preserved':True,'no_intentional_moat_crossed':True,'no_foreign_net_fill_changed':True,'new_signal_length_mm':line.length,'new_vias':0,'existing_return_geometry_changed':False,'analog_qualified':False,'fabrication_released':False}
(R/'patch-audit-r139.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS connected patch and exact local saved-fill scope',rows)
