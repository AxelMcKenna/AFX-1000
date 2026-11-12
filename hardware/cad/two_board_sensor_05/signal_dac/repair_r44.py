"""Correct two local CM_DRV_L reference gaps without moving vias or old copper."""
import json,uuid,hashlib
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
import hardware.fabrication.route_nf_surface as S
R=Path(__file__).resolve().parent;I=R.parent/'signal_input';S.SIGNAL_LAYERS=('F.Cu','B.Cu','In3.Cu','In5.Cu')
b=json.loads((I/'capture-r7/capture.json').read_text());c=json.loads((R/'capture-r43/capture.json').read_text());r=json.loads((R/'candidate-r43/routing.json').read_text());oldr=json.loads((R/'candidate-r26/routing.json').read_text());changes=[]
for k,x in enumerate(r['routes']):
 if k<len(oldr['routes']):continue
 net=x['net'];layer=x['layer'];ref={'F.Cu':'In1.Cu','B.Cu':'In6.Cu','In3.Cu':'In4.Cu','In5.Cu':'In4.Cu'}[layer]
 field=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']==ref]).buffer(2e-6)
 holes=unary_union([S.shape(ps).buffer(.215)for o in c['objects']if o['net']==net and(o['kind']=='PCB_VIA'or o['kind']=='PAD'and any(o['drill_mm']))for ps in o['layers'].values()if ps])
 existing=unary_union([S.shape(o['layers'][layer])for o in b['objects']if o['net']==net and o['layers'].get(layer)])
 allowed=field.union(holes).union(existing);center=prep(allowed.buffer(-.100001));old=x['path_mm']
 if LineString(old).buffer(.1).difference(allowed).area<1e-6:continue
 screen=S.Screen(c);base=screen.legal
 screen.legal=lambda n,l,path:base(n,l,path)and center.covers(LineString(path))
 new=[old[0]]
 for start,end in zip(old,old[1:]):
  if screen.legal(net,layer,[start,end]):new.append(end);continue
  choices=[q for q in S.candidate_paths(start,end)if screen.legal(net,layer,q)]
  path=min(choices,key=lambda q:LineString(q).length)if choices else screen.grid_path(net,layer,start,end,budget=15000)
  assert path,('no bounded local reference detour',k,start,end)
  new.extend(path[1:])
 assert screen.legal(net,layer,new) and LineString(new).buffer(.1).difference(allowed).area<1e-6
 x['path_mm']=new;changes.append({'route':k,'net':net,'layer':layer,'before':old,'after':new});print('repaired',layer,flush=True)
assert len(changes)==2
base=read_sexpr((R/'native-r26/signal_main.kicad_pcb').read_text());old_ids={first(x,'uuid')[1]for x in children(base,'segment')};t=read_sexpr((R/'native-r43/signal_main.kicad_pcb').read_text());t[:]=[x for x in t if not(isinstance(x,list)and x and x[0]=='segment'and first(x,'uuid')[1]not in old_ids)]
for k,x in enumerate(r['routes'][len(oldr['routes']):]):
 for j,(p,q)in enumerate(zip(x['path_mm'],x['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),x['layer']],[a('net'),x['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r44-{k}-{j}'))]])
r['local_reference_detours']=changes;r['detour_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),I/'capture-r7/capture.json',R/'capture-r43/capture.json',R/'candidate-r43/routing.json',R/'native-r43/signal_main.kicad_pcb',R/'native-r26/signal_main.kicad_pcb',R/'candidate-r26/routing.json']}
out=R/'candidate-r44';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
