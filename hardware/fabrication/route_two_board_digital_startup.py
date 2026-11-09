"""Construct a digital startup fanout candidate; native checks remain mandatory."""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,nearest_points
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_buck_cell import mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
BASE=STAGING/'two-board-power-digital-reference-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2320-digital-reference-02/capture.json'
PLAN=STAGING/'two-board-digital-startup-plan-01'
OUT=STAGING/'two-board-power-digital-startup-01'


def run():
 assert not OUT.exists()
 cap=json.loads(CAP.read_text())
 for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
 f,p,r=[json.loads((PLAN/n).read_text()) for n in ['fanout.json','placement.json','resistor-routes.json']]
 assert not f['deferred'] and not r['deferred'] and set(f['retired_objects'])==set(p['retired_objects'])
 previous=json.loads((BASE/'digital-reference-routing.json').read_text())
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(x,'Reference')[2]:x for x in children(board,'footprint')}
 moving=set(p['moves']);retire=set(f['retired_objects']);old={o['uuid']:o for o in cap['objects']}
 assert retire<=old.keys() and all(old[u]['kind'] in ['PCB_TRACK','PCB_VIA'] for u in retire)
 for ref,(xy,rotation,flip) in p['moves'].items():
  assert not flip
  for o in cap['objects']:
   if o.get('ref')==ref:assert len(cap['all_groups'][o['group']])==1
  fps[ref]=rotate_footprint(fps[ref],xy,rotation)
 placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
 for rec in p['reconciled_existing_passive_sides']:
  row=next(x for x in placement['parts'] if x['id']==rec['ref']);assert row['side']==rec['old_side'];row['side']=rec['current_side']
 mechanical_check(fps,moving,placement)
 for i,x in enumerate(board):
  if isinstance(x,list) and x and x[0]=='footprint' and prop(x,'Reference')[2] in moving:board[i]=fps[prop(x,'Reference')[2]]
 board[:]=[x for x in board if not(isinstance(x,list) and x and x[0] in ['segment','via'] and str(first(x,'uuid')[1]) in retire)]
 codes={str(n[2]):int(n[1]) for n in children(board,'net')}
 uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPDIGSTART01:'+sha(CAP)+':'+s))
 routes=f['routes']+f['fixed_routes']+r['routes']
 for i,route in enumerate(routes):
  route['segment_uuids']=[]
  for j,(start,end) in enumerate(zip(route['path_mm'],route['path_mm'][1:])):
   assert start!=end
   u=uid(f'track-{i}-{j}');route['segment_uuids'].append(u)
   board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),route['width_mm']],[a('layer'),route['layer']],[a('net'),codes[route['net']]],[a('uuid'),u]])
 vias=[dict(v,owner=route['ref'],pin=route['pin']) for v,route in zip(f['vias'],f['routes'])]+f['extra_quiet_vias']+r.get('extra_quiet_vias',[])+[dict(net='PWR_AGND',owner='E_U17',pin='8',position_mm=f['relocated_star']['position_mm'])]
 for i,v in enumerate(vias):
  v['uuid']=uid('via-'+str(i));v['size_mm']=.6;v['drill_mm']=.3
  board.append([a('via'),[a('at'),*v['position_mm']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
 zcap={z['uuid']:z for z in cap['zones']};regions={u:shape(z['authored_outline']) for u,z in zcap.items()}
 quiet=copy.deepcopy(previous['quiet_ground_islands']);ownerzones={}
 for q in quiet:
  ref=q['ref'];q['control_vias']=[v for v in vias if v['owner']==ref and v.get('pin') in ['2','4'] and 'ref' not in v]
  if ref=='E_U17':q['star_via']=next(v for v in vias if v.get('pin')=='8')
  q['extra_quiet_vias']=[v for v in vias if 'ref' in v and v['owner']==ref]
  back=next(z['uuid'] for z in previous['new_zones'] if z['ref']==ref and z['layer']=='In6.Cu')
  q['zone_uuids']=[q['zone_uuid'],back];ownerzones[ref]=set(q['zone_uuids'])
  newfront=[LineString(route['path_mm']).buffer(.4) for route in f['routes']+f['fixed_routes'] if route.get('chip',route.get('ref'))==ref and route['net']=='PWR_AGND' and route['layer']=='F.Cu']
  regions[q['zone_uuid']]=unary_union([regions[q['zone_uuid']],*newfront,*[Point(v['position_mm']).buffer(.33) for v in q['control_vias']+[q['star_via']]]])
  if ref=='E_U15':
   regions[q['zone_uuid']]=unary_union([regions[q['zone_uuid']],LineString([q['control_vias'][0]['position_mm'],q['star_via']['position_mm']]).buffer(.4)])
  if q['extra_quiet_vias']:
   for v in q['extra_quiet_vias']:
    anchor=nearest_points(Point(v['position_mm']),regions[back])[1]
    if anchor.distance(Point(v['position_mm']))>1e-8:regions[back]=unary_union([regions[back],LineString([v['position_mm'],list(anchor.coords[0])]).buffer(.5),Point(v['position_mm']).buffer(.33)])
   regions[back]=unary_union([regions[back],*[LineString(route['path_mm']).buffer(.4) for route in f['fixed_routes'] if route.get('label')=='E_C47 local quiet return'],*[Point(v['position_mm']).buffer(.33) for v in q['extra_quiet_vias']]])
 # Exclude every non-owned ground contact from each local quiet field. The
 # GND8 star alone is allowed to contact bulk return copper on other layers.
 for q in quiet:
  own={v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]}
  for u in q['zone_uuids']:
   layer=zcap[u]['layer'];g=regions[u]
   for o in cap['objects']:
    if o['uuid'] not in retire|own and o['net']=='PWR_AGND' and o['layers'].get(layer):g=g.difference(shape(o['layers'][layer]).buffer(.21,quad_segs=64))
   for v in vias:
    if v['net']=='PWR_AGND' and v['uuid'] not in own:g=g.difference(Point(v['position_mm']).buffer(.51,quad_segs=64))
   regions[u]=g
 # Retain existing neighboring fields when extending an island; native capture
 # and reference audits must still prove every old critical route survives.
 for q in quiet:
  for u in q['zone_uuids']:
   for other in quiet:
    if other['ref']==q['ref']:continue
    for v in other['zone_uuids']:
     if zcap[u]['layer']==zcap[v]['layer']:regions[u]=regions[u].difference(shape(zcap[v]['authored_outline']).buffer(.215))
 for i,q in enumerate(quiet):
  for other in quiet[i+1:]:
   for u in q['zone_uuids']:
    for v in other['zone_uuids']:
     if zcap[u]['layer']==zcap[v]['layer']:regions[v]=regions[v].difference(regions[u].buffer(.215))
 allquiet={u for us in ownerzones.values() for u in us}
 for u,z in zcap.items():
  if z['net']!='PWR_AGND':continue
  for q in quiet:
   if u in q['zone_uuids']:continue
   for v in q['control_vias']+q['extra_quiet_vias']:regions[u]=regions[u].difference(Point(v['position_mm']).buffer(.51,quad_segs=64))
   if u not in allquiet:
    for v in q['zone_uuids']:
     if zcap[v]['layer']==z['layer']:regions[u]=regions[u].difference(regions[v].buffer(.215))
 edited=[];refill=[]
 Path('/private/tmp/digital-startup-zone-plan.json').write_text(json.dumps({u:[dict(outer=list(p.exterior.coords),holes=[list(h.coords) for h in p.interiors]) for p in (g.geoms if hasattr(g,'geoms') else [g])] for u,g in regions.items()},indent=2))
 changes=[Point(v['position_mm']).buffer(.9) for v in vias]+[shape(ps).buffer(.6) for u in retire for ps in old[u]['layers'].values() if ps]
 affected=unary_union(changes)
 for z in children(board,'zone'):
  u=str(first(z,'uuid')[1]);g=regions[u].simplify(.00001,preserve_topology=True)
  changed=regions[u].symmetric_difference(shape(zcap[u]['authored_outline'])).area>1e-7
  if changed:
   assert g.geom_type=='Polygon' and g.is_valid,(u,g.geom_type)
   z[:]=[x for x in z if not(isinstance(x,list) and x and x[0]=='polygon')]
   z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
   edited.append(dict(uuid=u,layer=zcap[u]['layer'],outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors]))
  if changed or g.intersects(affected):
   z[:]=[x for x in z if not(isinstance(x,list) and x and x[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for path in BASE.rglob('*'):
  if not path.is_file():continue
  rel=path.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (path.suffix=='.kicad_sch' or path.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);sources.append(path)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 path=OUT/'power_protection.kicad_sch';s=read_sexpr(path.read_text());first(first(s,'title_block'),'rev')[1]='TBP40-CANDIDATE';path.write_text(sexpr(s)+'\n')
 sources=[Path(__file__),CAP,BASE/'digital-reference-routing.json',*[p for p in PLAN.iterdir() if p.is_file()],STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_buck_cell.py','repack_two_board_buck_input.py']],*sources]
 report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},moves=p['moves'],retired_objects=sorted(retire),routes=routes,vias=vias,quiet_ground_islands=quiet,edited_zone_outlines=edited,refilled_existing_zones=refill,added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),reconciled_existing_passive_sides=p['reconciled_existing_passive_sides'],mechanical_screen_findings=0,circuit_changes=[],expected_closed_connections=10,native_validation_pending=True,complete_startup_routing=False,complete_current_thermal_parasitic_qualification=False,fabrication_released=False)
 (OUT/'digital-startup-routing.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(added_tracks=report['added_tracks'],added_vias=len(vias),edited_zones=len(edited),refilled_zones=len(refill))))
if __name__=='__main__':run()
