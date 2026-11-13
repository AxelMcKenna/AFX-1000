"""Author only the successful IN feed and owned C907 relocation; freeze run inputs."""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
from ..ldo_local.immutable_inputs import prepare,sha
from ..routed.plan import shape
H=Path(__file__).resolve().parent;SRC=H.parent/'reference_fix/inputs-reference-09';STAGE=H/'stage-IN-slot-01';OUT=H/'inputs-IN-slot-01';p=json.loads((H/'route-probe.json').read_text());c=json.loads((H/'capture-02/capture.json').read_text());assert p['source_capture_sha256']==sha(H/'capture-02/capture.json') and p['script_sha256']==sha(H/'route_probe.py');routes=p['routes'][:4];assert all(r['path_mm'] for r in routes);assert not STAGE.exists();shutil.copytree(SRC,STAGE)
t=read_sexpr((SRC/'power_protection.kicad_pcb').read_text());removed=set(p['removed_only_owned_track_UUIDs']);found={first(x,'uuid')[1] for x in children(t,'segment') if first(x,'uuid')[1] in removed};assert found==removed;t[:]=[x for x in t if not(isinstance(x,list) and x[0]=='segment' and first(x,'uuid')[1] in removed)];f=next(f for f in children(t,'footprint') if any(x[1:3]==['Reference','P_C907'] for x in children(f,'property')));assert first(f,'at')[1:]==['187.5','126.6','180'];first(f,'at')[1]=Atom('186.5');ref=next(x for x in children(f,'property') if x[1]=='Reference');first(ref,'at')[1:]=[Atom('2'),Atom('-2.4'),Atom('0')]
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:IN-SLOT-01:'+s));num=lambda x:Atom(str(round(x,6)));added=[];vias=[]
for name in ['IN','INreturn']:
 xy,n=p['vias'][name];u=uid('via:'+name);vias.append({'name':name,'position_mm':xy,'net':n,'uuid':u,'size_mm':.6,'drill_mm':.3});added.append(u);t.append([Atom('via'),[Atom('at'),*map(num,xy)],[Atom('size'),Atom('.6')],[Atom('drill'),Atom('.3')],[Atom('layers'),'F.Cu','B.Cu'],[Atom('net'),n],[Atom('uuid'),u]])
for i,r in enumerate(routes):
 for j,(a,b) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  u=uid(f'track:{i}:{j}');added.append(u);t.append([Atom('segment'),[Atom('start'),*map(num,a)],[Atom('end'),*map(num,b)],[Atom('width'),num(r['width_mm'])],[Atom('layer'),r['layer']],[Atom('net'),r['net']],[Atom('uuid'),u]])
(STAGE/'power_protection.kicad_pcb').write_text(sexpr(t)+'\n');cuts=[]
for z in c['zones']:
 if z['net']!='PWR_AGND':continue
 scope=[Point(v['position_mm']).buffer(.506) for v in vias if v['net']!='PWR_AGND']
 scope += [LineString(r['path_mm']).buffer(r['width_mm']/2+.254) for r in routes if r['net']!='PWR_AGND' and r['layer']==z['layer']]
 if z['layer']=='F.Cu':scope.append(box(186.825,126.125,187.725,127.075).buffer(.254))
 if shape(z['polygons']).intersection(unary_union(scope)).area>1e-9:cuts.append(z['uuid'])
r=prepare(STAGE,OUT);r.update(builder_sha256=sha(Path(__file__)),source_board_sha256=sha(SRC/'power_protection.kicad_pcb'),source_capture_sha256=sha(H/'capture-02/capture.json'),source_reference_fix_manifest_sha256=sha(H.parent/'reference_fix/manifest.json'),route_probe_sha256=sha(H/'route-probe.json'),bundle_name=OUT.name,removed_owned_track_UUIDs=sorted(removed),added_UUIDs=added,vias=vias,routes=routes,allowed_AGND_zone_UUIDs=cuts,foreign_fills_must_remain_exact=True,new_C907_position_mm=[186.5,126.6],expected_reference_global_mm=[184.5,129],qualified=False);(H/'manifest-IN-slot-01.json').write_text(json.dumps(r,indent=2)+'\n');print({'cuts':cuts,'tracks':len(added)-2,'vias':2})
