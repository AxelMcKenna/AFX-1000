"""Exact source-bound repair of three original D_H4 copper objects; no placement change."""
import copy,hashlib,json,uuid
from pathlib import Path
from shapely.geometry import LineString,shape,Point
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;REPO=R.parents[3]
K=REPO/'hardware/cad/assembly_workflow/verification/main-fasteners-r1/contact-keepouts.json'
assert hashlib.sha256(K.read_bytes()).hexdigest()=='38854f6356625631ad32ec4578c989c2c3e06a6f8c48754ec768c55f53e04d71'
k=json.loads(K.read_text());t=read_sexpr((R/'native-r98/signal_main.kicad_pcb').read_text())
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-mount-r105-'+s))
ids={'ddc4f060-acad-5cdf-b2c5-eacdce6eecf9','f9f46967-df4b-52ce-b081-6c81851d0ff4','ecea17e2-69ed-5621-9e63-7ff6ca085a4f','31bc344d-b4e1-51bf-8de8-d76f7082df5b','bf298509-8042-5fe0-a905-34ead3d3e6a9'}
removed=[]
for tag in ['segment','via']:
 for row in children(t,tag):
  if first(row,'uuid')[1]in ids:removed.append({'uuid':first(row,'uuid')[1],'before_sexpr':sexpr(row)});t.remove(row)
assert len(removed)==5
path=[[190.5,85.1],[191.394049,84.558567],[188.5,68.9]]
for i,(p,q)in enumerate(zip(path,path[1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),'LINK_SDA'],[a('uuid'),uid('sda-'+str(i))]])
signal=[189.2,77.5];ground=[188.45,77.0]
for i,(layer,p,q) in enumerate([('In3.Cu',[191.3,79.9],signal),('In5.Cu',signal,[189.2,67.6])]):
 t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),layer],[a('net'),'/D_LED/LED_39'],[a('uuid'),uid('led-track-'+str(i))]])
for name,p,net in [('led',signal,'/D_LED/LED_39'),('ground',ground,'LINK_AGND')]:t.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid(name)]])
proto=next(z for z in children(t,'zone')if first(z,'uuid')[1]=='7174b53e-d6c3-5d96-88bf-06b6f6d225a4')
for layer in ['In4.Cu','In6.Cu']:
 p=LineString([signal,ground]).buffer(.7);z=copy.deepcopy(proto);z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['polygon','filled_polygon'])];first(z,'layer')[1]=layer;first(z,'uuid')[1]=uid(layer)
 if first(z,'priority'):first(z,'priority')[1]=11000
 else:z.append([a('priority'),11000])
 z.append([a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)]for x,y in list(p.exterior.coords)[:-1]]]]);t.append(z)
regions=[f for f in k['features']if f['properties']['board']=='signal'];assert len(regions)==9
for f in regions:
 name=f['properties']['mount'];assert name not in ['D_H2','D_H5']
 # Full disc track/via/pour prohibition; companion native pad rule excludes only copper-free round NPTH apertures.
 t.append([a('zone'),[a('net'),0],[a('net_name'),''],[a('layer'),'F.Cu'],[a('uuid'),uid('keepout-'+name)],[a('name'),'Main mount '+name+' conductive receiving disc r2.4'],[a('hatch'),a('edge'),.5],[a('connect_pads'),[a('clearance'),0]],[a('min_thickness'),.25],[a('keepout'),*[[a(x),a('not_allowed')]for x in ['tracks','vias','copperpour']], [a('pads'),a('allowed')],[a('footprints'),a('allowed')]],[a('fill'),[a('thermal_gap'),.3],[a('thermal_bridge_width'),.3]],[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)]for x,y in f['geometry']['coordinates'][0][:-1]]]]])
assert LineString(path).distance(Point(188,80))-.1>2.4
assert Point(signal).distance(Point(188,80))-.3>2.4
r={'base':'native-r98','expected_opens':167,'declared_removed':removed,'routes':[{'net':'LINK_SDA','layer':'F.Cu','path_mm':path}],'signal_via':{'uuid':uid('led'),'at':signal,'net':'/D_LED/LED_39'},'ground_via':{'uuid':uid('ground'),'at':ground},'transitions':[{'signal_at':signal,'return_at':ground,'return_uuid':uid('ground')}],'keepout_uuids':{f['properties']['mount']:uid('keepout-'+f['properties']['mount'])for f in regions},'physical_qualified':False,'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),K,R/'native-r98/signal_main.kicad_pcb',R/'capture-r98/capture.json']}}
out=R/'candidate-r105';out.mkdir();(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('candidate',len(regions),'keepouts; exact replacements',len(removed))

rules=(R/'native-r98/signal_main.kicad_dru').read_text()
for f in regions:
 name='Main mount '+f['properties']['mount']+' conductive receiving disc r2.4'
 condition="A.Type == 'Pad' && A.intersectsArea('"+name+"') && (A.Pad_Type != 'NPTH, mechanical' || A.Pad_Shape != 'Circle' || A.Size_X > A.Hole_Size_X || A.Size_Y > A.Hole_Size_Y)"
 rules+='\n(rule "'+name+' copper pads" (layer F.Cu) (condition "'+condition+'") (constraint disallow pad))\n'
(out/'signal_main.kicad_dru').write_text(rules)
