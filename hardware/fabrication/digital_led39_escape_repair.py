"""Free LED_39 by restoring one declared CONTROL_20 segment around its via."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import nearest_points
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add,route
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
CONTROL='/CONTROLS/CONTROL_20';PERMIT='/PROCESSOR/MCU_PERMIT'
REMOVED={'1a20dad4-1d32-5128-bd0a-5d3fbdf3aae9'}

def contacts(cap,net,start):
 result=set()
 for o in cap['objects']:
  if o['net']!=net or o.get('ref')=='R1003':continue
  points=[o['position_mm']]
  if o['kind']=='PCB_TRACK':
   points+=[o['end_mm'],list(nearest_points(Point(start),LineString([o['position_mm'],o['end_mm']]))[1].coords)[0]]
  result.update((f,tuple(p)) for f in search.LAYERS if o['layers'].get(f) for p in points)
 return result

def run():
 cp=ROOT/'staging/digital-led-control-inputs-39/capture.json';dp=ROOT/'staging/digital-remaining-hard-obstruction-diagnosis-01/diagnosis.json'
 cap=json.loads(cp.read_text());diagnosis=json.loads(dp.read_text())
 for r in (cap,diagnosis):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text())
 removed=[n for tag in ('segment','via') for n in children(original,tag) if first(n,'uuid')[1] in REMOVED]
 assert len(removed)==1 and {first(n,'net')[1] for n in removed}=={CONTROL}
 work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in REMOVED]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01
 surface.SIGNAL_LAYERS=search.LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 tasks=[(CONTROL,'In5.Cu',[43.4,18.3],{('In5.Cu',(44.8,20.0))})]
 attempts=[];selected=None;deadline=time.monotonic()+360
 for net in ('/LED/LED_39',):
  options=next(r['options'] for r in diagnosis['results'] if r['net']==net)
  for option in options:
   if set(option['blocker_nets'])!={CONTROL}:continue
   for order in itertools.permutations(tasks):
    if time.monotonic()>deadline:break
    screen=DigitalViaScreen(work,signal_layers=search.LAYERS)
    if not all(screen.legal(net,f,p) for f,p in option['runs']) or not all(screen.via_legal(net,p) for p in option['via_points']):continue
    routes=[add(screen,net,dict(runs=option['runs'],vias=option['via_points']))]
    attempt=dict(net=net,escape_vias=option['via_points'],order=[t[0] for t in order],repairs=[]);attempts.append(attempt)
    for n,f,p,targets in order:
     result=route(screen,n,f,p,targets,min(deadline,time.monotonic()+45))
     length=sum(LineString(path).length for face,path in result['runs']) if result else None
     attempt['repairs'].append(dict(net=n,found=bool(result),planar_length_mm=length));print(attempt,flush=True)
     if result is None or length>15:break
     routes.append(add(screen,n,result))
    if len(routes)!=2:continue
    end=next(o for o in work['objects'] if o['kind']=='PAD' and o['net']==net and o['ref'].startswith('J'))
    starts=[dict(point=option['via_points'][0],layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='LED')]
    ends=[dict(point=end['position_mm'],layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='header')]
    result=search.route_multi(screen,net,starts,{f:ends for f in search.LAYERS},min(deadline,time.monotonic()+60),max_visits=2500000)
    length=sum(LineString(p).length for f,p in result['runs']) if result else None
    attempt.update(global_found=bool(result),global_length_mm=length);print(attempt,flush=True)
    if result and length<75:routes.append(add(screen,net,result));selected=routes;break
   if selected:break
  if selected:break
 out=ROOT/'staging/digital-led39-escape-repair-01';out.mkdir(exist_ok=False)
 paths=[cp,dp,pcb,Path(__file__)]+[ROOT/n for n in ('digital_xlat_escape_repair.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v4.py','digital_visibility_escape.py','digital_multilayer_escape_routes_v4.py','digital_native_spacing_search_v3.py','digital_native_spacing_search_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 receipt=dict(source_sha256={str(p):sha(p) for p in paths},attempts=attempts,candidate_emitted=bool(selected),fabrication_released=False)
 if selected:
  board=copy.deepcopy(original)
  for n in removed:board.remove(n)
  for r in selected:
   net=r['net']
   for f,path in r['runs']:
    for p,q in zip(path,path[1:]):
     if math.dist(p,q)<1e-7:continue
     uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:LED39-repair:{sha(cp)}:{net}:{f}:{p}:{q}'))
     board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),f],[a('net'),net],[a('uuid'),uid]])
   for p in r['new_vias_mm']:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:LED39-via:{sha(cp)}:{net}:{p}'))
    board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
  dest=out/pcb.name;dest.write_text(sexpr(board)+'\n');receipt.update(candidate_PCB_sha256=sha(dest),removed_objects=removed,removed_uuids=sorted(REMOVED),routes=selected,geometry_delta=geometry_delta(original,board),native_checks_pending=True)
 (out/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Completed; candidate emitted',bool(selected),flush=True)
if __name__=='__main__':run()
