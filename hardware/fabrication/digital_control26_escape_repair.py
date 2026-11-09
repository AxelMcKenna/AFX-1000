"""Free CONTROL_26 by rebuilding CONTROL_22 and CONTROL_25, if all three connect."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add,route
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
LED='/CONTROLS/CONTROL_26';CONTROLS=['/CONTROLS/CONTROL_22','/CONTROLS/CONTROL_25']
def run():
 cp=ROOT/'staging/digital-led-control-inputs-39/capture.json';dp=ROOT/'staging/digital-control-obstruction-diagnosis-01/diagnosis.json'
 cap=json.loads(cp.read_text());diagnosis=json.loads(dp.read_text())
 for r in (cap,diagnosis):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text())
 removed=[n for tag in ('segment','via') for n in children(original,tag) if first(n,'net')[1] in CONTROLS]
 ids={first(n,'uuid')[1] for n in removed};assert len(ids)==46
 work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in ids]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=search.LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 options=next(r['options'] for r in diagnosis['results'] if r['net']==LED)
 attempts=[];selected=None;deadline=time.monotonic()+420
 for option in options[:2]:
  for order in itertools.permutations(CONTROLS):
   if time.monotonic()>deadline:break
   screen=DigitalViaScreen(work,signal_layers=search.LAYERS)
   if not all(screen.legal(LED,f,p) for f,p in option['runs']) or not all(screen.via_legal(LED,p) for p in option['via_points']):continue
   routes=[add(screen,LED,dict(runs=option['runs'],vias=option['via_points']))]
   attempt=dict(escape_vias=option['via_points'],order=order,routes=[]);attempts.append(attempt)
   for net in order:
    pads=[o for o in work['objects'] if o['kind']=='PAD' and o['net']==net];assert len(pads)==2
    start=next(o for o in pads if o['ref'].startswith('U'));end=next(o for o in pads if o['ref'].startswith('J'))
    contacts={(f,tuple(end['position_mm'])) for f in search.LAYERS if end['layers'].get(f)}
    result=route(screen,net,'B.Cu',start['position_mm'],contacts,min(deadline,time.monotonic()+40))
    length=sum(LineString(p).length for f,p in result['runs']) if result else None
    attempt['routes'].append(dict(net=net,found=bool(result),planar_length_mm=length));print(attempt,flush=True)
    if result is None or length>75:break
    routes.append(add(screen,net,result))
   if len(routes)!=3:continue
   end=next(o for o in work['objects'] if o['kind']=='PAD' and o['net']==LED and o['ref'].startswith('J'))
   starts=[dict(point=option['via_points'][0],layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='LED')]
   ends=[dict(point=end['position_mm'],layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='header')]
   result=search.route_multi(screen,LED,starts,{f:ends for f in search.LAYERS},min(deadline,time.monotonic()+50),max_visits=2500000)
   length=sum(LineString(p).length for f,p in result['runs']) if result else None
   attempt['routes'].append(dict(net=LED,found=bool(result),planar_length_mm=length));print(attempt,flush=True)
   if result and length<90:routes.append(add(screen,LED,result));selected=routes;break
  if selected:break
 out=ROOT/'staging/digital-control26-escape-repair-01';out.mkdir(exist_ok=False)
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
     uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:CONTROL26-repair:{sha(cp)}:{net}:{f}:{p}:{q}'))
     board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),f],[a('net'),net],[a('uuid'),uid]])
   for p in r['new_vias_mm']:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:CONTROL26-via:{sha(cp)}:{net}:{p}'))
    board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
  dest=out/pcb.name;dest.write_text(sexpr(board)+'\n');receipt.update(candidate_PCB_sha256=sha(dest),removed_objects=removed,removed_uuids=sorted(ids),routes=selected,geometry_delta=geometry_delta(original,board),native_checks_pending=True)
 (out/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Completed; candidate emitted',bool(selected),flush=True)
if __name__=='__main__':run()
