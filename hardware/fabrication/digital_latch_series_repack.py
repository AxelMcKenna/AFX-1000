"""Translate R3017 and reconnect both sides of its series resistor with bounded routes.

No footprint flip, net reassignment or unrelated copper retirement is allowed.
Native checks and independent verification are required before adoption.
"""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import translate
from shapely.ops import nearest_points
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options
from hardware.fabrication.digital_multilayer_escape_routes_v3 import multilayer_portals
from hardware.fabrication.digital_control_pulldowns_repack_v5 import surface_connection
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
REF='R3017';SRC='/LED/LATCH_5V_SRC';OUT='/LED/LATCH_5V'
REMOVED={'b5be175a-6407-420d-bdca-a534a938e3ed'}
def polys(g):return [dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]
def contacts_for(objects,net):
 return {(face,tuple(p)) for o in objects if o['net']==net for face in surface.SIGNAL_LAYERS if o['layers'].get(face) for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else [])}
def add_to_screen(screen,net,result):
 assert all(screen.legal(net,face,path) for face,path in result['runs'])
 assert all(screen.via_legal(net,p) for p in result['vias'])
 assert all(math.dist(p,q)>.563 for p,q in itertools.combinations(result['vias'],2))
 screen.added += [(net,face,LineString(path)) for face,path in result['runs']]
 screen.new_vias += [(net,tuple(p)) for p in result['vias']]
def connect(screen,net,pad,targets,deadline):
 face=next(iter(pad['layers']));start=pad['position_mm']
 same=[LineString([o['position_mm'],o['end_mm']]) if o['kind']=='PCB_TRACK' else Point(o['position_mm']) for o in targets if o['net']==net and o['layers'].get(face)]
 if face=='B.Cu' and same:
  path=surface_connection(screen,net,start,same,min(deadline,time.monotonic()+5))
  if path:return dict(runs=[(face,path)],vias=[])
 start_contacts={(face,tuple(start))};end_contacts=contacts_for(targets,net)
 starts=multilayer_portals(start_contacts,escape_options(screen,net,start_contacts,'moved-pad',min(deadline,time.monotonic()+6)),'moved-pad')
 # Retained inner copper already provides layer access; source-only surface
 # pads require their own screened escape options.
 end_escapes=escape_options(screen,net,end_contacts,'retained-net',min(deadline,time.monotonic()+6))
 ends=multilayer_portals(end_contacts,end_escapes,'retained-net')
 return search.route_multi(screen,net,starts,{face:ends for face in search.LAYERS},min(deadline,time.monotonic()+18),max_visits=1200000)
def run():
 cp=ROOT/'staging/digital-blank-pullup-inputs-43/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
 removed=[n for n in children(board,'segment') if first(n,'uuid')[1] in REMOVED];assert len(removed)==1 and first(removed[0],'net')[1]==OUT
 for n in removed:board.remove(n)
 fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(board,'footprint')};old=fps[REF];origin=list(map(float,first(old,'at')[1:3]));assert first(old,'layer')[1]=='B.Cu'
 oldpads=[o for o in cap['objects'] if o.get('ref')==REF];assert {o['net'] for o in oldpads}=={SRC,OUT}
 c=copy.deepcopy(cap);c['objects']=[o for o in c['objects'] if o['uuid'] not in REMOVED and o.get('ref')!=REF]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');search.LAYERS=surface.SIGNAL_LAYERS
 sides={r:first(f,'layer')[1][0] for r,f in fps.items()};courts={r:box(*courtyard(f,sides[r]+'.CrtYd')) for r,f in fps.items() if r!=REF};oldcourt=box(*courtyard(old,'B.CrtYd'))
 profile=Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
 mounts=[box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
 tht=[box(*pad_box(f,p,.5)) for r,f in fps.items() if r!=REF and sides[r]!='B' for p in children(f,'pad') if p[2]=='thru_hole']
 geometries=[(o['net'],surface.shape(o['layers']['B.Cu'])) for o in c['objects'] if o['layers'].get('B.Cu')];tree=STRtree([g for n,g in geometries]);base=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS);drilled=[(Point(p),r) for _,p,r,_ in base.drilled]
 targets={net:[LineString([o['position_mm'],o['end_mm']]) if o['kind']=='PCB_TRACK' else Point(o['position_mm']) for o in c['objects'] if o['net']==net] for net in (SRC,OUT)}
 poses=[];counts=dict(screened=0,mechanical=0,pad_clear=0)
 for x,y in itertools.product([55+i*.5 for i in range(61)],[10+i*.5 for i in range(61)]):
  counts['screened']+=1;dx,dy=x-origin[0],y-origin[1];cc=translate(oldcourt,dx,dy)
  if not profile.covers(cc) or cc.distance(profile.boundary)<.5-1e-8 or any(cc.distance(m)<.15-1e-8 for m in mounts):continue
  if any(cc.distance(g)<.3-1e-8 for r,g in courts.items() if sides[r]=='B') or any(cc.intersection(g).area>1e-10 for g in tht):continue
  counts['mechanical']+=1;pads=[]
  for p in oldpads:
   g=translate(surface.shape(p['layers']['B.Cu']),dx,dy)
   if any(net!=p['net'] and g.distance(obstacle)<.21-1e-8 for i in tree.query(g.buffer(.22)) for net,obstacle in [geometries[int(i)]]):break
   if any(point.distance(g)-radius<.16-1e-8 for point,radius in drilled):break
   new=copy.deepcopy(p);new['position_mm']=[p['position_mm'][0]+dx,p['position_mm'][1]+dy];new['layers']={'B.Cu':polys(g)};pads.append(new)
  if len(pads)!=2:continue
  counts['pad_clear']+=1
  score=sum((1 if p['net']==SRC else .25)*min(Point(p['position_mm']).distance(g) for g in targets[p['net']]) for p in pads)
  poses.append(dict(x=x,y=y,pads=pads,score=score))
 poses.sort(key=lambda p:p['score']);print('Placement screen',counts,flush=True);assert poses
 attempts=[];selected=None;deadline=time.monotonic()+300
 for pose in poses[:24]:
  if time.monotonic()>deadline:break
  work=copy.deepcopy(c);work['objects']+=pose['pads'];screen=DigitalViaScreen(work,signal_layers=surface.SIGNAL_LAYERS);routes=[]
  attempt=dict(position_mm=[pose['x'],pose['y']],nets=[]);attempts.append(attempt)
  for net,maxlen in [(SRC,18),(OUT,35)]:
   pad=next(p for p in pose['pads'] if p['net']==net);result=connect(screen,net,pad,c['objects'],deadline)
   length=sum(LineString(p).length for _,p in result['runs']) if result else None
   attempt['nets'].append(dict(net=net,connected=bool(result),length_mm=length));print(attempt,flush=True)
   if result is None or length>maxlen:break
   add_to_screen(screen,net,result);routes.append(dict(net=net,runs=result['runs'],new_vias_mm=result['vias'],planar_length_mm=length))
  if len(routes)==2:selected=pose,routes;break
 assert selected,'No complete source/output reconnection within the bounded placements and route-length targets'
 pose,routes=selected;first(old,'at')[1:3]=[pose['x'],pose['y']]
 for route in routes:
  net=route['net']
  for face,path in route['runs']:
   for p,q in zip(path,path[1:]):
    if math.dist(p,q)<1e-7:continue
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:latch-series-repack:{sha(cp)}:{net}:{face}:{p}:{q}'))
    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),uid]])
  for p in route['new_vias_mm']:
   uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:latch-series-via:{sha(cp)}:{net}:{p}'))
   board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
 out=ROOT/'staging/digital-latch-series-repack-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 inputs=[cp,pcb,Path(__file__)]+[ROOT/p for p in ['digital_core_layout.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','digital_multilayer_escape_routes_v3.py','digital_control_pulldowns_repack_v5.py','digital_native_spacing_search_v2.py','digital_native_spacing_search_v3.py','nf_pin_escape_routes.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','route_nf_surface.py']]
 recipe=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),component_move=dict(ref=REF,before_mm=origin,after_mm=[pose['x'],pose['y']],side='B',rotation_unchanged=True),routes=routes,placement_counts=counts,attempts=attempts,removed_objects=removed,removed_uuids=sorted(REMOVED),geometry_delta=geometry_delta(original,board),native_checks_pending=True,electrical_qualified=False,fabrication_released=False)
 (out/'construction.json').write_text(json.dumps(recipe,indent=2)+'\n');print('Repacked latch series resistor',recipe['component_move'],flush=True)
if __name__=='__main__':run()
