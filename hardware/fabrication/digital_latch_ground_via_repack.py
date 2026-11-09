"""Rebuild one ground return to free an existing via site for U3002's latch escape."""
import copy,json,math,time,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import nearest_points
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_control_pulldowns_repack_v5 import surface_connection
from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v2 as search
ROOT=Path(__file__).resolve().parent
NET='/LED/LATCH_5V'
REMOVED={'ddf5ce63-a3bc-56b5-bae4-7601e66d24e9','db13c3bf-494c-5004-abf8-d82cf637654f'}
def run():
 cp=ROOT/'staging/digital-control-pulldowns-inputs-45/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
 removed=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in REMOVED];assert len(removed)==2 and all(first(n,'net')[1]=='AGND' for n in removed)
 for n in removed:board.remove(n)
 cap['objects']=[o for o in cap['objects'] if o['uuid'] not in REMOVED]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(cap,signal_layers=surface.SIGNAL_LAYERS);via=[44.0125,13.4]
 pad=next(o for o in cap['objects'] if o.get('ref')=='U3002' and o.get('pin')=='30');lead=[pad['position_mm'],via]
 assert screen.legal(NET,'F.Cu',lead),'Latch surface escape blocked'
 assert screen.via_legal(NET,via),'Freed via location still blocked'
 screen.added.append((NET,'F.Cu',LineString(lead)));screen.new_vias.append((NET,tuple(via)))
 ground=next(o for o in cap['objects'] if o.get('ref')=='R1049' and o.get('pin')=='2')
 targets=[LineString([o['position_mm'],o['end_mm']]) if o['kind']=='PCB_TRACK' else Point(o['position_mm']) for o in cap['objects'] if o['net']=='AGND' and o['uuid']!=ground['uuid'] and o['layers'].get('B.Cu')]
 path=surface_connection(screen,'AGND',ground['position_mm'],targets,time.monotonic()+10)
 if path:ground_route=dict(runs=[('B.Cu',path)],vias=[])
 else:
  options=escape_options(screen,'AGND',{('B.Cu',tuple(ground['position_mm']))},'R1049-ground',time.monotonic()+15)
  assert options,'No replacement R1049 ground path';ground_route=min(options,key=lambda p:p['cost'])
 assert all(screen.legal('AGND',f,p) for f,p in ground_route['runs']) and all(screen.via_legal('AGND',p) for p in ground_route['vias'])
 screen.added += [('AGND',face,LineString(p)) for face,p in ground_route['runs']];screen.new_vias += [('AGND',tuple(p)) for p in ground_route['vias']]
 print('Replacement ground',ground_route,flush=True)
 routes=[]
 for face in ('In5.Cu','In3.Cu'):
  search.LAYERS=(face,);ends=[]
  for o in cap['objects']:
   if o['net']!=NET or o['group']==pad['group'] or not o['layers'].get(face):continue
   points=[o['position_mm']]
   if 'end_mm' in o:
    points.append(o['end_mm']);points.append(list(nearest_points(Point(via),LineString([o['position_mm'],o['end_mm']]))[1].coords)[0])
   ends += [dict(point=p,layers=[face],runs=[],vias=[],cost=0.,group='retained-latch') for p in points]
  result=search.route_multi(screen,NET,[dict(point=via,layers=[face],runs=[],vias=[],cost=0.,group='new-latch-escape')],{face:ends},time.monotonic()+30,max_visits=1500000) if ends else None
  print('Latch layer',face,'route',bool(result),flush=True)
  if result is not None:routes.append(result)
 if not routes:
  search.LAYERS=surface.SIGNAL_LAYERS;ends={face:[] for face in search.LAYERS}
  for o in cap['objects']:
   if o['net']!=NET or o['group']==pad['group']:continue
   for face in search.LAYERS:
    if not o['layers'].get(face):continue
    for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):ends[face].append(dict(point=p,layers=[face],runs=[],vias=[],cost=0.,group='retained-latch'))
  result=search.route_multi(screen,NET,[dict(point=via,layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='new-latch-escape')],ends,time.monotonic()+60,max_visits=2500000)
  print('Multilayer latch route',bool(result),flush=True)
  if result is not None:routes.append(result)
 assert routes,'No latch reconnection from freed via'
 result=min(routes,key=lambda r:sum(LineString(p).length for _,p in r['runs']))
 assert all(screen.legal(NET,face,p) for face,p in result['runs']) and all(screen.via_legal(NET,p) for p in result['vias'])
 result=dict(runs=[('F.Cu',lead)]+result['runs'],vias=[via]+result['vias'])
 records=[]
 for net,r in [('AGND',ground_route),(NET,result)]:
  for face,path in r['runs']:
   for p,q in zip(path,path[1:]):
    if math.dist(p,q)<1e-7:continue
    ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:latch-via-repack:{sha(cp)}:{net}:{face}:{p}:{q}'))
    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),ident]])
  for p in r['vias']:
   ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:latch-via-repack-via:{sha(cp)}:{net}:{p}'))
   board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),ident]])
  records.append(dict(net=net,runs=r['runs'],new_vias_mm=r['vias'],planar_length_mm=sum(LineString(p).length for _,p in r['runs'])))
 out=ROOT/'staging/digital-latch-via-repack-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 inputs=[cp,pcb,Path(__file__)]+[ROOT/p for p in ['digital_via_spacing_v2.py','digital_control_pulldowns_repack_v5.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','digital_core_layout.py','digital_native_spacing_search_v2.py','nf_minimum_logic.py','nf_pin_escape_routes.py','route_nf_surface.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py']]
 recipe=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),removed_objects=removed,removed_uuids=sorted(REMOVED),routes=records,geometry_delta=geometry_delta(original,board),all_component_poses_exact=True,native_checks_pending=True,electrical_qualified=False,fabrication_released=False)
 (out/'construction.json').write_text(json.dumps(recipe,indent=2)+'\n');print('Repacked latch via',records,flush=True)
if __name__=='__main__':run()
