"""Rebuild clock and blank escapes to open a local latch-buffer via corridor."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options
from hardware.fabrication.digital_multilayer_escape_routes_v3 import multilayer_portals
from hardware.fabrication.digital_latch_series_repack_v2 import connect,add_to_screen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
LATCH='/LED/LATCH_5V_SRC';CLOCK='/LED/CLOCK_5V_SRC';BLANK='/LED/BLANK_5V_SRC';OUTPUT='/LED/LATCH_5V'
REMOVED={'b5be175a-6407-420d-bdca-a534a938e3ed','8b479717-3eae-5658-8f55-3d250d6cdcb7','82db6130-72a0-56c4-8ce4-9163892072a5','efe8fe26-b281-5106-aeb9-c57974236860','12ed5b75-e25c-41fe-a1a5-aa7d758ddfb2','6cb15ae6-b6ba-4c69-8efa-436901e92945'}
def portal(p,faces,key):return dict(point=p,layers=faces,runs=[],vias=[],cost=0.,group=key)
def run():
 cp=ROOT/'staging/digital-blank-pullup-inputs-43/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
 removed=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in REMOVED];assert len(removed)==6 and {first(n,'net')[1] for n in removed}=={CLOCK,BLANK,OUTPUT}
 for n in removed:board.remove(n)
 cap['objects']=[o for o in cap['objects'] if o['uuid'] not in REMOVED]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');search.LAYERS=surface.SIGNAL_LAYERS
 screen=DigitalViaScreen(cap,signal_layers=surface.SIGNAL_LAYERS);records=[]
 via=(70.1,20.95);lead=[(68.8625,21.175),via]
 assert screen.legal(LATCH,'F.Cu',lead) and screen.via_legal(LATCH,via),'Local latch escape remains blocked'
 screen.added.append((LATCH,'F.Cu',LineString(lead)));screen.new_vias.append((LATCH,via))
 start=next(o for o in cap['objects'] if o.get('ref')=='R3017' and o.get('pin')=='1');contacts={('B.Cu',tuple(start['position_mm']))}
 starts=multilayer_portals(contacts,escape_options(screen,LATCH,contacts,'R3017',time.monotonic()+12),'R3017')
 ends=[portal(via,list(search.LAYERS),'new-buffer-via')]
 result=search.route_multi(screen,LATCH,starts,{f:ends for f in search.LAYERS},time.monotonic()+40,max_visits=2000000)
 assert result,'Latch resistor connection unavailable'
 length=sum(LineString(p).length for _,p in result['runs'])+LineString(lead).length;print('Latch source length',length,flush=True);assert length<18
 add_to_screen(screen,LATCH,result);records.append(dict(net=LATCH,runs=[('F.Cu',lead)]+result['runs'],new_vias_mm=[via]+result['vias'],planar_length_mm=length))
 # Replace only the two retired inner blank-source segments; the existing
 # via and every other branch stay in place.
 p=(69.508,19.5534);q=(70.1364,21.825)
 choices=[path for path in surface.candidate_paths(p,q) if screen.legal(BLANK,'In3.Cu',path)]
 if choices:result=dict(runs=[('In3.Cu',min(choices,key=lambda path:LineString(path).length))],vias=[])
 else:
  old=search.LAYERS;search.LAYERS=('In3.Cu',)
  result=search.route_multi(screen,BLANK,[portal(p,['In3.Cu'],'retained-blank-trace')],{'In3.Cu':[portal(q,['In3.Cu'],'retained-blank-via')]},time.monotonic()+20,max_visits=1000000);search.LAYERS=old
 assert result,'Blank source replacement unavailable'
 length=sum(LineString(p).length for _,p in result['runs']);print('Blank replacement length',length,flush=True);assert length<12
 add_to_screen(screen,BLANK,result);records.append(dict(net=BLANK,runs=result['runs'],new_vias_mm=result['vias'],planar_length_mm=length))
 pad=next(o for o in cap['objects'] if o.get('ref')=='R3016' and o.get('pin')=='1');targets=[o for o in cap['objects'] if o['net']==CLOCK and o['uuid']!=pad['uuid']]
 result=connect(screen,CLOCK,pad,targets,time.monotonic()+60);assert result,'Clock source replacement unavailable'
 length=sum(LineString(p).length for _,p in result['runs']);print('Clock source length',length,flush=True);assert length<18
 add_to_screen(screen,CLOCK,result);records.append(dict(net=CLOCK,runs=result['runs'],new_vias_mm=result['vias'],planar_length_mm=length))
 pad=next(o for o in cap['objects'] if o.get('ref')=='R3017' and o.get('pin')=='2');targets=[o for o in cap['objects'] if o['net']==OUTPUT and o['uuid']!=pad['uuid']]
 result=connect(screen,OUTPUT,pad,targets,time.monotonic()+60);assert result,'Latch output replacement unavailable'
 length=sum(LineString(p).length for _,p in result['runs']);print('Latch output replacement length',length,flush=True);assert length<25
 add_to_screen(screen,OUTPUT,result);records.append(dict(net=OUTPUT,runs=result['runs'],new_vias_mm=result['vias'],planar_length_mm=length))
 for route in records:
  net=route['net']
  for face,path in route['runs']:
   for p,q in zip(path,path[1:]):
    if math.dist(p,q)<1e-7:continue
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:buffer-escape-repack:{sha(cp)}:{net}:{face}:{p}:{q}'))
    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),uid]])
  for p in route['new_vias_mm']:
   uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:buffer-escape-via:{sha(cp)}:{net}:{p}'))
   board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
 out=ROOT/'staging/digital-buffer-escape-repack-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 inputs=[cp,pcb,Path(__file__)]+[ROOT/p for p in ['digital_latch_series_repack_v2.py','digital_core_layout.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','digital_multilayer_escape_routes_v3.py','digital_control_pulldowns_repack_v5.py','digital_native_spacing_search_v2.py','digital_native_spacing_search_v3.py','nf_pin_escape_routes.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','route_nf_surface.py']]
 recipe=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),routes=records,removed_objects=removed,removed_uuids=sorted(REMOVED),geometry_delta=geometry_delta(original,board),all_component_poses_exact=True,native_checks_pending=True,electrical_qualified=False,fabrication_released=False)
 (out/'construction.json').write_text(json.dumps(recipe,indent=2)+'\n');print('Buffer escape candidate emitted',flush=True)
if __name__=='__main__':run()
