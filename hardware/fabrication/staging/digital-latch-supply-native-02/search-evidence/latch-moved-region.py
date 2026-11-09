"""Rebuild clock and blank escapes to open a local latch-buffer via corridor."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import LineString
from shapely.affinity import translate
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
ROOT=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/fabrication')
LATCH='/LED/LATCH_5V_SRC';CLOCK='/LED/CLOCK_5V_SRC';BLANK='/LED/BLANK_5V_SRC';OUTPUT='/LED/LATCH_5V'
REMOVED={'b5be175a-6407-420d-bdca-a534a938e3ed','8b479717-3eae-5658-8f55-3d250d6cdcb7','82db6130-72a0-56c4-8ce4-9163892072a5','efe8fe26-b281-5106-aeb9-c57974236860','12ed5b75-e25c-41fe-a1a5-aa7d758ddfb2','6cb15ae6-b6ba-4c69-8efa-436901e92945'}
def portal(p,faces,key):return dict(point=p,layers=faces,runs=[],vias=[],cost=0.,group=key)
def run():
 cp=ROOT/'staging/digital-blank-pullup-inputs-43/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
 removed=[n for tag in ('segment','via') for n in children(board,tag) if first(n,'uuid')[1] in REMOVED];assert len(removed)==6 and {first(n,'net')[1] for n in removed}=={CLOCK,BLANK,OUTPUT}
 for n in removed:board.remove(n)
 cap['objects']=[o for o in cap['objects'] if o['uuid'] not in REMOVED]
 fp=next(f for f in children(board,'footprint') if any(p[1:3]==['Reference','R3017'] for p in children(f,'property')))
 assert list(map(float,first(fp,'at')[1:3]))==[75.,23.]
 first(fp,'at')[1:3]=[68.,25.]
 for o in cap['objects']:
  if o.get('ref')=='R3017':
   o['position_mm']=[o['position_mm'][0]-7,o['position_mm'][1]+2]
   g=translate(surface.shape(o['layers']['B.Cu']),-7,2);o['layers']={'B.Cu':[dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]}
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');search.LAYERS=surface.SIGNAL_LAYERS
 screen=DigitalViaScreen(cap,signal_layers=surface.SIGNAL_LAYERS);records=[]
 from shapely.geometry import Point
 from shapely.ops import unary_union
 p=next(o for o in cap['objects'] if o.get('ref')=='R3017' and o.get('pin')=='1');net=p['net'];start=Point(p['position_mm'])
 free=screen.outline.difference(unary_union([g.buffer(d+.0005,quad_segs=32) for n,g,d in screen.geometry['B.Cu'] if n!=net]));regions=[free] if free.geom_type=='Polygon' else list(free.geoms);region=next((g for g in regions if g.covers(start)),None)
 available=region.intersection(screen.via_outline.difference(screen.obstacles(net))) if region else None
 print('Source pad',p['position_mm'],'region',region.area if region else None,'bounds',region.bounds if region else None,'via area',available.area if available else None)
 print('Available bounds',available.bounds,'centroid',list(available.centroid.coords) if not available.is_empty else [])
 freeF=screen.outline.difference(unary_union([g.buffer(d+.0005,quad_segs=32) for n,g,d in screen.geometry['F.Cu'] if n!=net]));parts=[freeF] if freeF.geom_type=='Polygon' else list(freeF.geoms);regF=next(g for g in parts if g.covers(Point(68.8625,21.175)))
 shared=regF.intersection(available);print('Shared area',shared.area,'bounds',shared.bounds)
 return
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
 out=ROOT/'staging/digital-buffer-escape-repack-02';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
 inputs=[cp,pcb,Path(__file__)]+[ROOT/p for p in ['digital_latch_series_repack_v2.py','digital_core_layout.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','digital_multilayer_escape_routes_v3.py','digital_control_pulldowns_repack_v5.py','digital_native_spacing_search_v2.py','digital_native_spacing_search_v3.py','nf_pin_escape_routes.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','route_nf_surface.py']]
 recipe=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),routes=records,removed_objects=removed,removed_uuids=sorted(REMOVED),geometry_delta=geometry_delta(original,board),component_move=dict(ref='R3017',before_mm=[75.,23.],after_mm=[68.,25.],side='B',rotation_unchanged=True),all_other_component_poses_exact=True,native_checks_pending=True,electrical_qualified=False,fabrication_released=False)
 (out/'construction.json').write_text(json.dumps(recipe,indent=2)+'\n');print('Buffer escape candidate emitted',flush=True)
if __name__=='__main__':run()
