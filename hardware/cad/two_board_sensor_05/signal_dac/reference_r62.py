"""Add physical LINK_AGND corridors for the new buffer route, retaining every old zone."""
import json,uuid,copy,math,hashlib
from pathlib import Path
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union,split
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;old=json.loads((R/'candidate-r50/routing.json').read_text());new=json.loads((R/'candidate-r61/routing.json').read_text());capture=json.loads((R/'capture-r53/capture.json').read_text());t=read_sexpr((R/'candidate-r61/signal_main.kicad_pcb').read_text())
new_ground=[]
for k,p in enumerate(new['planned_ground_returns']):
 uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r62-ground-{k}'));t.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),'LINK_AGND'],[a('uuid'),uid]]);new_ground.append({'at':p,'uuid':uid,'size_mm':.6,'drill_mm':.3})
trans=[]
for row in new['used_return_sites']:
 q=next((g for g in new_ground if g['at']==row['return_at']),None)
 if q is None:q=next(o for o in capture['objects']if o['kind']=='PCB_VIA'and o['net']=='LINK_AGND'and o['position_mm']==row['return_at'])
 trans.append({**row,'return_uuid':q['uuid'],'kind':'new corridor ground'if 'at'in q else'existing native ground via','distance_mm':math.dist(row['signal_at'],row['return_at'])})
proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]=='7174b53e-d6c3-5d96-88bf-06b6f6d225a4');assert first(proto,'net')[1]=='LINK_AGND';zones=[]
# Widen only the new physical route-reference corridor by 0.1 mm to remove a native In4 copper sliver. Keepouts and old copper remain fixed.
for layer,signal_layers in [('In4.Cu',['In3.Cu','In5.Cu']),('In6.Cu',['B.Cu'])]:
 shapes=[LineString(x['path_mm']).buffer(1.3)for x in new['routes']if x['layer']in signal_layers]
 shapes.extend(LineString([x['signal_at'],x['return_at']]).buffer(.7)for x in trans)
 shape=unary_union(shapes);parts=list(shape.geoms)if shape.geom_type=='MultiPolygon'else[shape]
 for _ in range(100):
  if not any(p.interiors for p in parts):break
  revised=[]
  for p in parts:
   if not p.interiors:revised.append(p);continue
   y=Polygon(p.interiors[0]).representative_point().y;revised.extend(split(p,LineString([(p.bounds[0]-1,y),(p.bounds[2]+1,y)])).geoms)
  parts=revised
 for k,p in enumerate(parts):
  assert not p.interiors
  z=copy.deepcopy(proto);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])]
  first(z,'layer')[1]=layer;uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r62-reference-{layer}-{k}'));first(z,'uuid')[1]=uid
  priority=first(z,'priority')
  if priority:priority[1]=4000+k
  else:z.append([a('priority'),4000+k])
  z.append([a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)]for x,y in list(p.exterior.coords)[:-1]]]]);t.append(z);zones.append({'uuid':uid,'layer':layer,'area_mm2':p.area})
r=copy.deepcopy(old);base_metadata=json.loads((R/'candidate-r26/routing.json').read_text());r.setdefault('ground_stitches',base_metadata['ground_stitches']);r.setdefault('new_reference_zones',base_metadata['new_reference_zones']);r['routes']+=new['routes'];r['vias']+=new['vias'];r['ground_stitches']+=new_ground;r['transitions']+=trans;r['new_reference_zones']+=zones;r['blocked']=[v for v in old['blocked']if v['net']not in {x['net']for x in new['routes']}];r['expected_opens']=new['expected_opens']
placement=json.loads((R/'candidate-r53/routing.json').read_text());r['moves']+=placement['moves'];r['supplemental_lowcap_exclusions']=placement['supplemental_lowcap_exclusions']
r['remaining_reference_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r53/routing.json',R/'sensitive_placement.py',R/'candidate-r26/routing.json',R/'candidate-r50/routing.json',R/'candidate-r61/routing.json',R/'candidate-r61/signal_main.kicad_pcb',R/'capture-r53/capture.json',R/'reference_r24.py']}
out=R/'candidate-r62';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('new ground vias',len(new_ground),'new physical zones',zones)
