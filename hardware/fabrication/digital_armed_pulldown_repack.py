"""Move the isolated ARMED pull-down to accessible copper, preserving its ground junction."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import translate
from shapely.ops import nearest_points
from shapely.strtree import STRtree
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v2 as search
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_core_layout import pad_box
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent
NET='/PROCESSOR/ARMED';REF='R1005'
def polys(g):return [dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]
def run():
 cp=ROOT/'staging/digital-data-series-inputs-49/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
 fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(board,'footprint')};old=fps[REF];assert first(old,'layer')[1]=='B.Cu';origin=list(map(float,first(old,'at')[1:3]))
 oldpads=[o for o in cap['objects'] if o.get('ref')==REF];assert {p['net'] for p in oldpads}=={NET,'AGND'}
 c=copy.deepcopy(cap);c['objects']=[o for o in c['objects'] if o.get('ref')!=REF]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');search.LAYERS=('In5.Cu',)
 sides={r:first(f,'layer')[1][0] for r,f in fps.items()};courts={r:box(*courtyard(f,sides[r]+'.CrtYd')) for r,f in fps.items() if r!=REF};oldcourt=box(*courtyard(old,'B.CrtYd'))
 profile=Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
 mounts=[box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
 tht=[box(*pad_box(f,p,.5)) for r,f in fps.items() if r!=REF and sides[r]!='B' for p in children(f,'pad') if p[2]=='thru_hole']
 geometries=[(o['net'],surface.shape(o['layers']['B.Cu'])) for o in c['objects'] if o['layers'].get('B.Cu')];tree=STRtree([g for n,g in geometries])
 base_screen=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS)
 drilled=[(Point(p),r) for _,p,r,_ in base_screen.drilled]
 target_lines=[LineString([o['position_mm'],o['end_mm']]) for o in c['objects'] if o['net']==NET and o['kind']=='PCB_TRACK' and o['layers'].get('In5.Cu')]
 poses=[];counts=dict(screened=0,mechanical=0,pad_clear=0)
 for x,y in itertools.product([19+i*.5 for i in range(85)],[10+i*.5 for i in range(51)]):
  counts['screened']+=1;dx,dy=x-origin[0],y-origin[1];cc=translate(oldcourt,dx,dy)
  if not profile.covers(cc) or cc.distance(profile.boundary)<.5-1e-8 or any(cc.distance(m)<.15-1e-8 for m in mounts):continue
  if any(cc.distance(g)<.3-1e-8 for r,g in courts.items() if sides[r]=='B') or any(cc.intersection(g).area>1e-10 for g in tht):continue
  counts['mechanical']+=1;pads=[]
  for p in oldpads:
   g=translate(surface.shape(p['layers']['B.Cu']),dx,dy)
   if any(other!=p['net'] and g.distance(obstacle)<.21-1e-8 for i in tree.query(g.buffer(.22)) for other,obstacle in [geometries[int(i)]]):break
   if any(point.distance(g)-radius<.16-1e-8 for point,radius in drilled):break
   new=copy.deepcopy(p);new['position_mm']=[p['position_mm'][0]+dx,p['position_mm'][1]+dy];new['layers']={'B.Cu':polys(g)};pads.append(new)
  if len(pads)!=2:continue
  counts['pad_clear']+=1;pin=next(p for p in pads if p['net']==NET);score=min(Point(pin['position_mm']).distance(g) for g in target_lines)
  poses.append(dict(x=x,y=y,pads=pads,score=score))
 poses.sort(key=lambda p:p['score']);print('Placement screen',counts,flush=True);assert poses
 deadline=time.monotonic()+240;selected=None;attempts=[]
 for pose in poses[:32]:
  if time.monotonic()>deadline:break
  work=copy.deepcopy(c);work['objects']+=pose['pads'];screen=DigitalViaScreen(work,signal_layers=surface.SIGNAL_LAYERS)
  signal=next(p for p in pose['pads'] if p['net']==NET);ground=next(p for p in pose['pads'] if p['net']=='AGND')
  portals=escape_options(screen,NET,{('B.Cu',tuple(signal['position_mm']))},'moved-signal',min(deadline,time.monotonic()+8))
  endpoints=[]
  for line in target_lines:
   points=list(line.coords)
   points += [list(nearest_points(Point(p['point']),line)[1].coords)[0] for p in portals]
   endpoints += [dict(point=p,layers=['In5.Cu'],runs=[],vias=[],cost=0.,group='retained-ARMED') for p in points]
  result=search.route_multi(screen,NET,portals,{'In5.Cu':endpoints},min(deadline,time.monotonic()+10),max_visits=500000) if portals else None
  attempt=dict(position_mm=[pose['x'],pose['y']],signal_portals=len(portals),signal_connected=bool(result));attempts.append(attempt)
  if result is None:print(attempt,flush=True);continue
  screen.added += [(NET,l,LineString(p)) for l,p in result['runs']];screen.new_vias += [(NET,tuple(p)) for p in result['vias']]
  # A conventional AGND via joins the retained In1/In4/In6 plane after refill.
  ground_options=escape_options(screen,'AGND',{('B.Cu',tuple(ground['position_mm']))},'moved-ground',min(deadline,time.monotonic()+8))
  attempt['ground_options']=len(ground_options);print(attempt,flush=True)
  if not ground_options:continue
  ground_route=min(ground_options,key=lambda p:p['cost']);assert ground_route['vias']
  total=sum(LineString(p).length for _,p in result['runs']+ground_route['runs']);attempt['added_mm']=total
  if total>30:continue
  selected=pose,result,ground_route;break
 assert selected,'No complete signal/ground reconnection at screened poses'
 pose,result,ground=selected;first(old,'at')[1:3]=[pose['x'],pose['y']];routes=[]
 for net,r in [(NET,result),('AGND',ground)]:
  for face,path in r['runs']:
   for p,q in zip(path,path[1:]):
    if math.dist(p,q)<1e-7:continue
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:armed-repack:{sha(cp)}:{net}:{face}:{p}:{q}'))
    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),uid]])
  for p in r['vias']:
   uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:armed-repack-via:{sha(cp)}:{net}:{p}'))
   board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
  routes.append(dict(net=net,runs=r['runs'],new_vias_mm=r['vias'],planar_length_mm=sum(LineString(p).length for _,p in r['runs'])))
 out=ROOT/'staging/digital-armed-repack-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 inputs=[cp,pcb,Path(__file__)]+[ROOT/p for p in ['digital_core_layout.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','digital_native_spacing_search_v2.py','nf_pin_escape_routes.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','route_nf_surface.py']]
 recipe=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),component_move=dict(ref=REF,before_mm=origin,after_mm=[pose['x'],pose['y']],side='B',rotation_unchanged=True),geometry_delta=geometry_delta(original,board),all_existing_copper_exact=True,routes=routes,placement_counts=counts,attempts=attempts,native_checks_pending=True,electrical_qualified=False,fabrication_released=False)
 (out/'construction.json').write_text(json.dumps(recipe,indent=2)+'\n');print('Repacked',recipe['component_move'],flush=True)
if __name__=='__main__':run()
