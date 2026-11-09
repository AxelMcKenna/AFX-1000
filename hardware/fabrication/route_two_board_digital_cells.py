"""Regroup digital eFuse support passives and route reviewed local networks."""
import json,shutil,uuid
from pathlib import Path
from shapely.geometry import MultiPoint,Point,box
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_two_board_buck_cell import mechanical_check
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-digital-distribution-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2340-digital-distribution-02/capture.json'
PLAN=STAGING/'two-board-digital-cell-plan-01'
POSES=STAGING/'two-board-digital-cell-native-poses-01'
OUT=STAGING/'two-board-power-digital-cells-01'


def run():
 assert not OUT.exists()
 cap=json.loads(CAP.read_text());plan=json.loads((PLAN/'routes.json').read_text());prior=json.loads((BASE/'digital-distribution-routing.json').read_text())
 for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
 assert not plan['deferred']
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());posed=read_sexpr((POSES/'native-poses.kicad_pcb').read_text())
 fps={prop(f,'Reference')[2]:f for f in children(posed,'footprint')};moving=set(plan['moves']);retire=set(plan['retired_objects'])
 placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text());reconciled=[]
 for r in placement['parts']:
  if r['id'] in fps and r['id'] not in moving and r['side']!=str(first(fps[r['id']],'layer')[1])[0]:
   assert r['id'].startswith(('P_R','P_C')) and not r['tails_relative_xy']
   b=r['body_relative_xy'];assert abs(b[0]+b[2])<1e-7 and abs(b[1]+b[3])<1e-7
   reconciled.append(r['id']);r['side']=str(first(fps[r['id']],'layer')[1])[0]
 mechanical_check(fps,moving,placement)
 for i,f in enumerate(board):
  if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in moving:board[i]=fps[prop(f,'Reference')[2]]
 board[:]=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retire)]
 codes={str(n[2]):int(n[1]) for n in children(board,'net')}
 uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPDIGCELL01:'+sha(CAP)+':'+s))
 routes=plan['routes']+plan['connections']
 for i,r in enumerate(routes):
  r['segment_uuids']=[]
  for j,(p,q) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
   u=uid(f'track-{i}-{j}');r['segment_uuids'].append(u)
   board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),r['width_mm']],[a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),u]])
 for i,v in enumerate(plan['vias']):
  v['uuid']=uid('via-'+str(i));board.append([a('via'),[a('at'),*v['position_mm']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
 shapes={};quiet=[]
 for ref in ['E_U15','E_U16','E_U17','E_U33']:
  controls=[v for r,v in zip(prior['routes'],prior['vias']) if r['ref']==ref and r['pin'] in ['2','4']]
  star=next(v for r,v in zip(plan['routes'],plan['vias']) if r['ref']==ref and r['pin']=='8')
  u=next(z['uuid'] for z in prior['new_zones'] if z['label']==ref+'-quiet-ground')
  g=MultiPoint([v['position_mm'] for v in [*controls,star]]).convex_hull.buffer(.32,quad_segs=64)
  own={v['uuid'] for v in [*controls,star]}
  for o in cap['objects']:
   if o['uuid'] in retire:continue
   if o['net']=='PWR_AGND' and o['uuid'] not in own and o['layers'].get('In1.Cu'):g=g.difference(shape(o['layers']['In1.Cu']).buffer(.21))
  for v in plan['vias']:
   if v['net']=='PWR_AGND' and v['uuid'] not in own:g=g.difference(Point(v['position_mm']).buffer(.51))
  assert g.geom_type=='Polygon' and g.is_valid;shapes[u]=g
  quiet.append(dict(ref=ref,zone_uuid=u,control_vias=controls,star_via=star))
 # U17's relocated star enters the concave space between U16's controls.
 # Reserve U17's complete island plus the inter-island clearance in U16.
 q16=next(q for q in quiet if q['ref']=='E_U16');q17=next(q for q in quiet if q['ref']=='E_U17')
 shapes[q16['zone_uuid']]=shapes[q16['zone_uuid']].difference(shapes[q17['zone_uuid']].buffer(.215))
 for q in quiet:
  g=shapes[q['zone_uuid']];assert g.is_valid and g.geom_type=='Polygon'
  for v in [*q['control_vias'],q['star_via']]:assert g.buffer(1e-6).covers(Point(v['position_mm']).buffer(.301))
 for i,q in enumerate(quiet):
  assert all(shapes[q['zone_uuid']].distance(shapes[r['zone_uuid']])>=.21 for r in quiet[i+1:])
 for label,extension in [('source-distribution',box(146,132,152,137)),('source-adjacent-return',box(145,132,154,137.5))]:
  desc=next(z for z in prior['new_zones'] if z['label']==label);z=next(z for z in cap['zones'] if z['uuid']==desc['uuid']);g=unary_union([shape(z['authored_outline']),extension])
  main=next(o['group'] for o in cap['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
  for o in cap['objects']:
   if o.get('npth'):g=g.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
   if label=='source-adjacent-return' and o['net']=='PWR_AGND' and o.get('group')!=main and o['layers'].get('In5.Cu'):g=g.difference(shape(o['layers']['In5.Cu']).buffer(.21))
  if label=='source-adjacent-return':
   for q in quiet:
    for v in q['control_vias']:g=g.difference(Point(v['position_mm']).buffer(.51,quad_segs=64))
  shapes[z['uuid']]=g
 changed=set(shapes)|{'2d29f18e-f863-557a-bd84-b2d1a216144c','a94125f8-f63e-5d6b-a427-21dcfd31e312','787e0385-5c4c-5b8f-9a2a-017054f7da0e','1893ea20-0fe1-5364-8239-d1853c450ce0'}
 outlines=[]
 for z in children(board,'zone'):
  u=str(first(z,'uuid')[1])
  if u in changed:z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
  if u in shapes:
   g=shapes[u].simplify(.00001,preserve_topology=True);assert g.is_valid and g.geom_type=='Polygon'
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='polygon')]
   z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
   outlines.append(dict(uuid=u,outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(r.coords)[:-1] for r in g.interiors]))
 OUT.mkdir();sources=[]
 for p in BASE.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (p.suffix=='.kicad_sch' or p.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);sources.append(p)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 p=OUT/'power_protection.kicad_sch';s=read_sexpr(p.read_text());first(first(s,'title_block'),'rev')[1]='TBP38';p.write_text(sexpr(s)+'\n')
 sources=[Path(__file__),CAP,*[p for p in PLAN.iterdir() if p.is_file()],POSES/'poses.json',POSES/'native-poses.kicad_pcb',STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',REPO/'hardware/fabrication/route_two_board_buck_cell.py',REPO/'hardware/fabrication/route_nf_surface.py',*sources]
 report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},moves=plan['moves'],retired_objects=sorted(retire),routes=routes,escape_count=len(plan['routes']),vias=plan['vias'],quiet_ground_islands=quiet,edited_zone_outlines=outlines,refilled_existing_zones=sorted(changed),added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(plan['vias']),mechanical_screen_findings=0,reconciled_existing_passive_sides=reconciled,circuit_changes=[],native_validation_pending=True,complete_reference_and_current_thermal_qualification=False,fabrication_released=False)
 (OUT/'digital-cell-routing.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['added_tracks','added_vias','mechanical_screen_findings']}))
if __name__=='__main__':run()
