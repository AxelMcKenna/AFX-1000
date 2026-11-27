"""Source-bound native plated return-path and per-plane change inventory."""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent
b=json.loads((R/'capture-baseline/capture.json').read_text());r3=json.loads((R/'capture-after-r3/capture.json').read_text());c=json.loads((R/'capture-after-r4/capture.json').read_text());routing=json.loads((R/'candidate-r4/routing.json').read_text())
objects={o['uuid']:o for o in c['objects']};main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20')
fields={l:unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']==l])for l in ['In4.Cu','In6.Cu']}
rows=[]
for v in routing['return_stitches']:
 o=objects[v['uuid']];assert o['group']==main and o['net']=='LINK_AGND'and o['span']==['F.Cu','B.Cu']
 xy=v['signal_at'];near=[]
 for old in r3['objects']:
  if old['net']!='LINK_AGND'or old['group']!=next(x['group']for x in r3['objects']if x.get('ref')=='D_U1001'and x.get('pin')=='20'):continue
  if old['kind']not in ['PAD','PCB_VIA']:continue
  if old['kind']=='PAD'and not any(old['drill_mm']):continue
  if not all(old['layers'].get(l)for l in fields):continue
  near.append({'uuid':old['uuid'],'ref':old.get('ref'),'pin':old.get('pin'),'at':old['position_mm'],'distance_mm':math.dist(xy,old['position_mm'])})
 contacts={l:fields[l].intersection(shape(o['layers'][l])).area for l in fields};assert all(a>1e-5 for a in contacts.values())
 # Existing signal plated copper/clearance is necessarily a hole in reference.
 signal=next(x for x in c['objects']if x['net']in ['LINK_SCL','LINK_SDA']and x['kind']in ['PAD','PCB_VIA']and math.dist(x['position_mm'],xy)<1e-6)
 hole=unary_union([shape(ps)for ps in signal['layers'].values()]).buffer(.215)
 corridor=LineString([xy,v['at']]).buffer(.1).difference(hole)
 lost={l:corridor.difference(f.buffer(.0015)).area for l,f in fields.items()};assert all(a<1e-6 for a in lost.values()),(v,lost)
 baseline_contacts=[{'zone':z['uuid'],'net':z['net'],'layer':z['layer'],'area_mm2':shape(z['polygons']).intersection(Point(v['at']).buffer(.3)).area}for z in b['zones']if shape(z['polygons']).intersection(Point(v['at']).buffer(.3)).area>1e-6]
 rows.append({**v,'same_native_group_as_D_U1001_20':True,'native_group':main,'direct_reference_contact_area_mm2':contacts,'local_corridor_uncovered_mm2':lost,'nearest_r3_plated_return':min(near,key=lambda x:x['distance_mm']),'baseline_plane_contacts':baseline_contacts})
oldzones={(z['uuid'],z['layer']):z for z in b['zones']};changes=[]
for z in c['zones']:
 k=(z['uuid'],z['layer']);new=shape(z['polygons']);old=shape(oldzones[k]['polygons'])if k in oldzones else Point().buffer(0)
 lost=old.difference(new).area;gained=new.difference(old).area
 if lost+gained>1e-7:changes.append({'uuid':k[0],'layer':k[1],'net':z['net'],'new_authored_zone':k not in oldzones,'lost_filled_area_mm2':lost,'gained_filled_area_mm2':gained})
paths=[Path(__file__),R/'candidate-r4/routing.json',R/'capture-baseline/capture.json',R/'capture-after-r3/capture.json',R/'capture-after-r4/capture.json']
report={'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'scope':'Local return connections and geometric path continuity only; no noise or complete-board qualification','stitches':rows,'all_changed_native_filled_planes':changes,'control_join_extension':'J402.3/.4 adjacent stitches connect existing analog In1 ground to the new In4/In6 ground; not limited to J402.1 anymore','pass':True}
(R/'transitions-r4.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(rows),'transitions;',len(changes),'changed plane fills')
