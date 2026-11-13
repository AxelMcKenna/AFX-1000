"""One source-declared D101 translation and two stub reworks for a modeled PD_L join."""
import copy,hashlib,json,math,uuid
from pathlib import Path
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union,split
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,a
R=Path(__file__).resolve().parent;REPO=R.parents[3];plan=json.loads((R/'pd-plan-r116.json').read_text());t=read_sexpr((R/'native-r107/signal_main.kicad_pcb').read_text());r=copy.deepcopy(plan)
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-PD-r117-'+s))
fp=next(f for f in children(t,'footprint')if any(x[1]=='Reference'and x[2]=='A_D101'for x in children(f,'property')));before=sexpr(fp);assert list(map(float,first(fp,'at')[1:]))==[75,66];first(fp,'at')[1:3]=[75,66.5];r['declared_pose_change']={'uuid':first(fp,'uuid')[1],'reference':'A_D101','before_sexpr':before,'after_sexpr':sexpr(fp)}
r['declared_removed']=[];r['routes']=[{'net':'/A_ADC/PD_L','layer':'F.Cu','path_mm':plan['front_escape'],'width_mm':.2,'role':'FDA pin7 escape'},{'net':'/A_ADC/PD_L','layer':'In3.Cu','path_mm':plan['inner_path'],'width_mm':.2,'role':'FDA PD join'}]
for s in plan['exact_stub_reworks']:
 row=next(sg for sg in children(t,'segment')if first(sg,'uuid')[1]==s['uuid']);assert first(row,'net')[1]==s['net']and list(map(float,first(row,'start')[1:]))==s['before_path_mm'][0]and list(map(float,first(row,'end')[1:]))==s['before_path_mm'][1];r['declared_removed'].append({'uuid':s['uuid'],'before_sexpr':sexpr(row)});t.remove(row);r['routes'].append({**s,'role':'D101 supply stub recenter'})
for j,row in enumerate(r['routes']):
 for i,(p,q)in enumerate(zip(row['path_mm'],row['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),row['width_mm']],[a('layer'),row['layer']],[a('net'),row['net']],[a('uuid'),uid(f'track-{j}-{i}')]])
p=plan['signal_via_at'];t.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),'/A_ADC/PD_L'],[a('uuid'),uid('via')]])
r['vias']=[{'uuid':uid('via'),'at':p,'net':'/A_ADC/PD_L'}];r['transitions']=[{'signal_at':p,'return_at':plan['return_at'],'return_uuid':'a7458126-f91b-5950-b26b-97ba2f3e99a3','distance_mm':math.dist(p,plan['return_at']),'kind':'existing ground via'}]
proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]=='7174b53e-d6c3-5d96-88bf-06b6f6d225a4');zones=[]
for layer,signal_layers in [('In4.Cu',['In3.Cu']),('In6.Cu',['B.Cu'])]:
 shapes=[LineString(x['path_mm']).buffer(1.3)for x in r['routes']if x['layer']in signal_layers and x['net']!='LINK_AGND'];shapes.append(LineString([p,plan['return_at']]).buffer(.7));g=unary_union(shapes);parts=list(g.geoms)if g.geom_type=='MultiPolygon'else[g]
 for _ in range(100):
  if not any(x.interiors for x in parts):break
  parts=[q for x in parts for q in (split(x,LineString([(x.bounds[0]-1,Polygon(x.interiors[0]).representative_point().y),(x.bounds[2]+1,Polygon(x.interiors[0]).representative_point().y)])).geoms if x.interiors else[x])]
 for i,g in enumerate(parts):
  assert not g.interiors;z=copy.deepcopy(proto);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])];first(z,'layer')[1]=layer;first(z,'uuid')[1]=uid(f'zone-{layer}-{i}');first(z,'priority')[1]=12000+i;z.append([a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)]for x,y in list(g.exterior.coords)[:-1]]]]);t.append(z);zones.append({'uuid':first(z,'uuid')[1],'layer':layer})
r['new_reference_zones']=zones;r['expected_opens']=166;r['source_sha256']={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'pd-plan-r116.json',R/'native-r107/signal_main.kicad_pcb',R/'native-r107/signal_main.kicad_dru']}
out=R/'candidate-r117';out.mkdir();(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'signal_main.kicad_dru').write_bytes((R/'native-r107/signal_main.kicad_dru').read_bytes());(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('one pose, two exact stubs, one PD_L join; native and mechanical acceptance pending')
