"""PD_R join with exactly three authorized endpoint-preserving detours."""
import copy,hashlib,json,math,uuid
from pathlib import Path
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union,split
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,a
R=Path(__file__).resolve().parent;REPO=R.parents[3];plan=json.loads((R/'pd-join-r145.json').read_text());source=R/'native-r139/signal_main.kicad_pcb';t=read_sexpr(source.read_text());uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-PD-r146-'+s));r={'planning_only':False,'candidate_not_selected':True,'candidate_geometry_changed':True,'declared_removed':[],'routes':[{'net':'/A_ADC/PD_R','layer':'F.Cu','path_mm':plan['front_escape_mm'],'width_mm':.2,'role':'FDA pin7 escape'},{'net':'/A_ADC/PD_R','layer':'In3.Cu','path_mm':plan['inner_path_mm'],'width_mm':.2,'role':'FDA PD_R join'}]}
for s in plan['exact_three_authorized_replacements']:
 row=next(v for v in children(t,'segment')if first(v,'uuid')[1]==s['uuid']);assert first(row,'net')[1]==s['net']and first(row,'layer')[1]==s['layer']and float(first(row,'width')[1])==s['width_mm'];assert list(map(float,first(row,'start')[1:]))==s['before_path_mm'][0]and list(map(float,first(row,'end')[1:]))==s['before_path_mm'][1];assert s['path_mm'][0]==s['before_path_mm'][0]and s['path_mm'][-1]==s['before_path_mm'][-1]
 r['declared_removed'].append({'uuid':s['uuid'],'before_sexpr':sexpr(row)});t.remove(row);r['routes'].append({**s,'role':'authorized obstacle replacement','replaced_original_uuid':s['uuid']})
for j,row in enumerate(r['routes']):
 row['added_track_uuids']=[]
 for i,(p,q)in enumerate(zip(row['path_mm'],row['path_mm'][1:])):
  track=uid(f'track-{j}-{i}');row['added_track_uuids'].append(track);t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),row['width_mm']],[a('layer'),row['layer']],[a('net'),row['net']],[a('uuid'),track]])
for name,p,net in [('signal',plan['via_mm'],'/A_ADC/PD_R'),('return',plan['return_at'],'LINK_AGND')]:t.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid(name+'-via')]])
r['vias']=[{'uuid':uid('signal-via'),'at':plan['via_mm'],'net':'/A_ADC/PD_R'}];r['new_ground_vias']=[{'uuid':uid('return-via'),'at':plan['return_at'],'net':'LINK_AGND'}];r['transitions']=[{'signal_at':plan['via_mm'],'return_at':plan['return_at'],'return_uuid':uid('return-via'),'distance_mm':math.dist(plan['via_mm'],plan['return_at']),'kind':'new source-bound ground return'}]
proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]=='7174b53e-d6c3-5d96-88bf-06b6f6d225a4');zones=[]
for layer,signal_layers in [('In4.Cu',['In3.Cu']),('In6.Cu',['B.Cu'])]:
 shapes=[LineString(x['path_mm']).buffer(1.3)for x in r['routes']if x['layer']in signal_layers];shapes.append(LineString([plan['via_mm'],plan['return_at']]).buffer(.7));g=unary_union(shapes);parts=list(g.geoms)if g.geom_type=='MultiPolygon'else[g]
 for _ in range(100):
  if not any(x.interiors for x in parts):break
  parts=[q for x in parts for q in (split(x,LineString([(x.bounds[0]-1,Polygon(x.interiors[0]).representative_point().y),(x.bounds[2]+1,Polygon(x.interiors[0]).representative_point().y)])).geoms if x.interiors else[x])]
 for i,g in enumerate(parts):
  assert not g.interiors;z=copy.deepcopy(proto);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])];first(z,'layer')[1]=layer;first(z,'uuid')[1]=uid(f'zone-{layer}-{i}');first(z,'priority')[1]=14000+i;boundary=[[round(x,6),round(y,6)]for x,y in list(g.exterior.coords)[:-1]];z.append([a('polygon'),[a('pts'),*[[a('xy'),*p]for p in boundary]]]);t.append(z);zones.append({'uuid':first(z,'uuid')[1],'layer':layer,'net':'LINK_AGND','boundary_mm':boundary,'prototype_uuid':first(proto,'uuid')[1]})
r.update(new_reference_zones=zones,expected_opens=162,physical_pose_changes=[],analog_qualified=False,fabrication_released=False);r['source_sha256']={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'pd-join-r145.json',source,R/'native-r139/signal_main.kicad_dru']};o=R/'candidate-r146';o.mkdir();(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'signal_main.kicad_dru').write_bytes((R/'native-r139/signal_main.kicad_dru').read_bytes());(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('PD_R: 3 exact detours, 2 vias, 2 reference patches; verification pending')
