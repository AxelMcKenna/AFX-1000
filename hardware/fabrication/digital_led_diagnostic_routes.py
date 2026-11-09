"""Test diagnostic escape proposals against the full board before additive routing."""
import copy,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,children,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent

def run():
 cp=ROOT/'staging/digital-pot-filter-inputs-40/capture.json';dp=ROOT/'staging/digital-led-obstruction-diagnosis-01/diagnosis.json'
 cap=json.loads(cp.read_text());diagnosis=json.loads(dp.read_text())
 for r in (cap,diagnosis):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(pcb.read_text());original,count=sexpr(board),len(board)
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01
 surface.SIGNAL_LAYERS=search.LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(cap,signal_layers=surface.SIGNAL_LAYERS);routes=[];attempts=[];deadline=time.monotonic()+480
 rows=sorted(diagnosis['results'],key=lambda r:(min((len(o['blockers']) for o in r['options']),default=999),r['net']))
 for row in rows:
  if time.monotonic()>deadline:break
  net=row['net'];target=next(o for o in cap['objects'] if o['kind']=='PAD' and o['net']==net and o.get('ref','').startswith('J'))
  ends=[dict(point=target['position_mm'],layers=[f for f in search.LAYERS if target['layers'].get(f)],runs=[],vias=[],cost=0.,group='header')]
  legal=[o for o in row['options'] if all(screen.legal(net,f,p) for f,p in o['runs']) and all(screen.via_legal(net,p) for p in o['via_points'])]
  print(net,'actual legal escapes',len(legal),flush=True)
  for option in legal[:3]:
   assert len(option['via_points'])==1
   start=dict(point=option['via_points'][0],layers=list(search.LAYERS),runs=option['runs'],vias=option['via_points'],cost=option['planar_length_mm']+2.5,group='driver')
   result=search.route_multi(screen,net,[start],{f:ends for f in search.LAYERS},min(deadline,time.monotonic()+25),max_visits=2000000)
   length=sum(LineString(p).length for f,p in result['runs']) if result else None
   attempt=dict(net=net,escape_via_mm=option['via_points'][0],found=bool(result),planar_length_mm=length,emitted=bool(result and length<=90));attempts.append(attempt);print(attempt,flush=True)
   if not attempt['emitted']:continue
   assert all(screen.legal(net,f,p) for f,p in result['runs'])
   fresh=[tuple(p) for p in result['vias'] if not any(n==net and math.dist(p,q)<1e-7 for n,q in screen.vias+screen.new_vias)]
   assert all(screen.via_legal(net,p) for p in fresh)
   for f,path in result['runs']:
    screen.added.append((net,f,LineString(path)))
    for p,q in zip(path,path[1:]):
     if math.dist(p,q)<1e-7:continue
     uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:diagnostic-LED:{sha(cp)}:{net}:{f}:{p}:{q}'))
     board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),f],[a('net'),net],[a('uuid'),uid]])
   for p in fresh:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:diagnostic-LED-via:{sha(cp)}:{net}:{p}'))
    board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
    screen.new_vias.append((net,p))
   result.update(net=net,new_vias_mm=fresh,planar_length_mm=length);routes.append(result);break
 assert sexpr(board[:count])==original
 out=ROOT/'staging/digital-led-diagnostic-routes-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 paths=[cp,dp,pcb,Path(__file__)]+[ROOT/p for p in ('digital_via_spacing_v2.py','digital_native_spacing_search_v3.py','route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},candidate_PCB_sha256=sha(dest),routes=routes,attempts=attempts,added_segments=len(children(board,'segment'))-len(children(read_sexpr(original),'segment')),added_vias=len(screen.new_vias),source_geometry_exact=True,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
 print('Completed',len(routes),'additive LED joins',flush=True)
if __name__=='__main__':run()
