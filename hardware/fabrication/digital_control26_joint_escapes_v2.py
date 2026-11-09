"""Reserve three compatible control escapes before completing their header routes."""
import argparse,copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.digital_visibility_escape import route as visibility
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v4 import escape_options
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent

def run():
 nets=[f'/CONTROLS/CONTROL_{n}' for n in (22,25,26)]
 cp=ROOT/'staging/digital-led-control-inputs-39/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text())
 objects={o['uuid']:o for o in cap['objects']};open_nets={objects[ids[0]]['net'] for ids in cap['groups'].values()}
 assert nets[0] not in open_nets and nets[1] not in open_nets and nets[2] in open_nets
 removed=[n for tag in ('segment','via') for n in children(original,tag) if first(n,'net')[1] in nets]
 ids={first(n,'uuid')[1] for n in removed};work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in ids]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=search.LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(work,signal_layers=search.LAYERS);domains=[];headers={}
 for net in nets:
  pads=[o for o in work['objects'] if o['kind']=='PAD' and o['net']==net];assert len(pads)==2
  pad=next(o for o in pads if o['ref'].startswith('U'));headers[net]=next(o for o in pads if o['ref'].startswith('J'))
  options=escape_options(screen,net,{('B.Cu',tuple(pad['position_mm']))},net,time.monotonic()+20)
  domains.append(options);print(net,len(options),'escape options',flush=True)
 combinations=[]
 for options in itertools.product(*domains):
  compatible=True
  for left,right in itertools.combinations(options,2):
   if any(math.dist(p,q)<.814 for p in left['vias'] for q in right['vias']):compatible=False;break
  if compatible:combinations.append((sum(o['cost'] for o in options),options))
 combinations.sort(key=lambda row:row[0]);attempts=[];selected=None;deadline=time.monotonic()+420
 print('Compatible escape triples',len(combinations),flush=True)
 for index,(_,options) in enumerate(combinations[:32]):
  for order in itertools.permutations(nets):
   if time.monotonic()>deadline:break
   screen=DigitalViaScreen(work,signal_layers=search.LAYERS);routes=[]
   for n,o in zip(nets,options):screen.new_vias += [(n,tuple(v)) for v in o['vias']]
   attempt=dict(combination_index=index,order=order,escape_routes=[],global_routes=[]);attempts.append(attempt)
   for net in order:
    option=options[nets.index(net)];via=option['point'];pad=next(o for o in work['objects'] if o['kind']=='PAD' and o['net']==net and o['ref'].startswith('U'));start=pad['position_mm']
    choices=[path for path in surface.candidate_paths(start,via) if screen.legal(net,'B.Cu',path)]
    path=min(choices,key=lambda p:LineString(p).length) if choices else None
    if path is None:
     obstacles=[g.buffer(d+.0005,quad_segs=32) for n,g,d in screen.geometry['B.Cu'] if n!=net]
     obstacles += [g.buffer(.4105,quad_segs=32) for n,f,g in screen.added if n!=net and f=='B.Cu']
     obstacles += [Point(p).buffer(.5105,quad_segs=32) for n,p in screen.new_vias if n!=net]
     free=screen.outline.difference(unary_union(obstacles))
     path=visibility(screen,net,'B.Cu',start,via,free,min(deadline,time.monotonic()+2))
    attempt['escape_routes'].append(dict(net=net,found=bool(path),via=via))
    if path is None:break
    r=add(screen,net,dict(runs=[('B.Cu',path)],vias=[]));r['new_vias_mm']=option['vias'];routes.append(r)
   if len(routes)!=3:continue
   print('Three local escapes reserved',attempt,flush=True)
   for net in order:
    option=options[nets.index(net)];header=headers[net]
    start=dict(point=option['point'],layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='mux')
    end=dict(point=header['position_mm'],layers=[f for f in search.LAYERS if header['layers'].get(f)],runs=[],vias=[],cost=0.,group='header')
    result=search.route_multi(screen,net,[start],{f:[end] for f in search.LAYERS},min(deadline,time.monotonic()+30),max_visits=2500000)
    length=sum(LineString(p).length for f,p in result['runs']) if result else None
    attempt['global_routes'].append(dict(net=net,found=bool(result),planar_length_mm=length));print(attempt,flush=True)
    if result is None or length>75:break
    routes.append(add(screen,net,result))
   if len(routes)==6:selected=routes;break
  if selected:break
 out=ROOT/'staging/digital-control26-joint-escapes-02';out.mkdir(exist_ok=False)
 paths=[cp,pcb,Path(__file__)]+[ROOT/n for n in ('digital_via_spacing_v2.py','digital_continuous_escape_options_v4.py','digital_visibility_escape.py','digital_xlat_escape_repair.py','digital_multilayer_escape_routes_v4.py','digital_native_spacing_search_v3.py','digital_native_spacing_search_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 receipt=dict(source_sha256={str(p):sha(p) for p in paths},nets=nets,domains=domains,compatible_triples=len(combinations),attempts=attempts,candidate_emitted=bool(selected),fabrication_released=False)
 if selected:
  board=copy.deepcopy(original)
  for n in removed:board.remove(n)
  for r in selected:
   net=r['net']
   for f,path in r['runs']:
    for p,q in zip(path,path[1:]):
     if math.dist(p,q)<1e-7:continue
     uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:control-triple:{sha(cp)}:{net}:{f}:{p}:{q}'))
     board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),f],[a('net'),net],[a('uuid'),uid]])
   for p in r['new_vias_mm']:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:control-triple-via:{sha(cp)}:{net}:{p}'))
    board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
  dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
  receipt.update(candidate_PCB_sha256=sha(dest),removed_objects=removed,removed_uuids=sorted(ids),routes=selected,geometry_delta=geometry_delta(original,board),native_checks_pending=True)
 (out/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('Completed control triple; candidate emitted',bool(selected),'compatible triples',len(combinations),flush=True)
if __name__=='__main__':run()
