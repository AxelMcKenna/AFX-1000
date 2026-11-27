"""Add explicit analog return corridors and local transition ground stitches."""
import json,math,uuid,copy,hashlib
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;I=R.parent/'i2c_routing';c=json.loads((I/'capture-after-r4/capture.json').read_text());r=json.loads((R/'candidate-r5/routing.json').read_text());objects={o['uuid']:o for o in c['objects']}
foreign=[(o['net'],shape(ps))for o in c['objects']if o['net']!='LINK_AGND'for ps in o['layers'].values()if ps]
foreign +=[(x['net'],LineString(x['path_mm']).buffer(.1))for x in r['routes']]+[(v['net'],Point(v['at']).buffer(.3))for v in r['vias']]
tree=STRtree([g for _,g in foreign]);ground=[o for o in c['objects']if o['net']=='LINK_AGND'and o['kind']in ['PAD','PCB_VIA']and all(o['layers'].get(l)for l in ['In1.Cu','In4.Cu','In6.Cu'])]
in1=unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu']);stitches=[];trans=[]
pts={tuple(v['at'])for v in r['vias']}
for route in r['routes']:
 if route['layer']not in ['B.Cu','In3.Cu']:continue
 for p in [route['path_mm'][0],route['path_mm'][-1]]:
  if any(o['net']==route['net']and o['kind']=='PAD'and any(o['drill_mm'])and math.dist(p,o['position_mm'])<1e-6 for o in c['objects']):pts.add(tuple(p))
for p in sorted(pts):
 near=min(ground,key=lambda o:math.dist(p,o['position_mm']));distance=math.dist(p,near['position_mm'])
 if distance<=1.5:q=near['position_mm'];kind='existing';uid=near['uuid']
 else:
  candidates=sorted(([round(p[0]+i*.1,6),round(p[1]+j*.1,6)]for i in range(-25,26)for j in range(-25,26)),key=lambda q:math.dist(p,q))
  q=None
  for v in candidates:
   pt=Point(v)
   if not in1.covers(pt.buffer(.31)):continue
   if any(pt.distance(foreign[int(ix)][1])<.51 for ix in tree.query(pt.buffer(.52))):continue
   if any(o['kind']=='PCB_VIA'and math.dist(v,o['position_mm'])<.86 for o in c['objects']):continue
   if any(math.dist(v,x['at'])<.86 for x in r['vias']):continue
   close=next((s for s in stitches if math.dist(p,s['at'])<=1.5),None)
   if close:q=close['at'];uid=close['uuid'];kind='shared new';break
   if any(math.dist(v,s['at'])<.86 for s in stitches):continue
   q=v;uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-ref-{len(stitches)}'));kind='new';stitches.append({'at':q,'uuid':uid,'size_mm':.6,'drill_mm':.3});break
  assert q is not None,('no local return site',p)
  assert math.dist(p,q)<=2.5,('return distance allocation exceeded',p,q)
 trans.append({'signal_at':list(p),'return_at':q,'return_uuid':uid,'kind':kind,'distance_mm':math.dist(p,q),'nearest_original_return_mm':distance})
t=read_sexpr((R/'candidate-r5/signal_main.kicad_pcb').read_text())
for s in stitches:t.append([a('via'),[a('at'),*s['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),'LINK_AGND'],[a('uuid'),s['uuid']]])
base=next(z for z in children(t,'zone')if first(z,'uuid')[1]=='7174b53e-d6c3-5d96-88bf-06b6f6d225a4');newzones=[]
for layer,trace in [('In4.Cu','In3.Cu'),('In6.Cu','B.Cu')]:
 geoms=[LineString(x['path_mm']).buffer(1.2)for x in r['routes']if x['layer']==trace]
 geoms +=[LineString([x['signal_at'],x['return_at']]).buffer(.7)for x in trans]
 geom=unary_union(geoms)
 for k,g in enumerate(geom.geoms if geom.geom_type=='MultiPolygon'else[geom]):
  z=copy.deepcopy(base);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])];first(z,'layer')[1]=layer;uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-input-ref-{layer}-{k}'));first(z,'uuid')[1]=uid
  assert not g.interiors
  z.append([a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)]for x,y in list(g.exterior.coords)[:-1]]]]);t.append(z);newzones.append({'uuid':uid,'layer':layer,'area_mm2':g.area})
o=R/'candidate-r6';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');r['ground_stitches']=stitches;r['transitions']=trans;r['new_reference_zones']=newzones;r['reference_additions_pending']=False;r['reference_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r5/signal_main.kicad_pcb',R/'candidate-r5/routing.json']};(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('stitches',len(stitches),'transitions',len(trans),'max distance',max(x['distance_mm']for x in trans),'zones',len(newzones))
