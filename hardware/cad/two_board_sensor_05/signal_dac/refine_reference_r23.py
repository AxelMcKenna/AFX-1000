"""Bounded geometry correction for two source-bound reference residuals."""
import json,uuid,hashlib
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
import hardware.fabrication.route_nf_surface as S
R=Path(__file__).resolve().parent;I=R.parent/'signal_input';S.SIGNAL_LAYERS=('F.Cu','B.Cu','In3.Cu','In5.Cu')
r=json.loads((R/'candidate-r19/routing.json').read_text());c=json.loads((R/'capture-r19/capture.json').read_text())
base=S.Screen(c)
x=next(x for x in r['routes']if x['net']=='/A_DAC/IV_N_L'and x['layer']=='F.Cu')
f=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu']).buffer(.0015)
holes=unary_union([S.shape(ps).buffer(.215)for o in c['objects']if o['net']==x['net']and(o['kind']=='PCB_VIA'or o['kind']=='PAD'and any(o['drill_mm']))for ps in o['layers'].values()if ps]);allowed=prep(f.union(holes).buffer(-.100001));origlegal=base.legal
base.legal=lambda net,layer,path:origlegal(net,layer,path)and allowed.covers(LineString(path))
oldpath=x['path_mm'];paths=[p for p in S.candidate_paths(oldpath[0],oldpath[-1])if base.legal(x['net'],'F.Cu',p)];path=min(paths,key=lambda p:LineString(p).length)if paths else base.grid_path(x['net'],'F.Cu',oldpath[0],oldpath[-1],budget=30000);assert path;x['path_mm']=path
r['reference_residual_changes']={'IV_N_L_F_path':{'old':oldpath,'new':path}}
t=read_sexpr((I/'native-r7/signal_main.kicad_pcb').read_text())
for k,x in enumerate(r['routes']):
 for j,(p,q)in enumerate(zip(x['path_mm'],x['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),x['layer']],[a('net'),x['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r23-{k}-{j}'))]])
for k,v in enumerate(r['vias']):
 v['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r23-via-{k}'));t.append([a('via'),[a('at'),*v['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),v['net']],[a('uuid'),v['uuid']]])
o=R/'candidate-r23';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');r['reference_additions_pending']=True;r['refinement_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r19/routing.json',R/'capture-r19/capture.json']};(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print(r['reference_residual_changes'])
