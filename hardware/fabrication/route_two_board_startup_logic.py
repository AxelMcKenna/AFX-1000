"""Construct relocated startup logic and explicitly owned main return copper.

This candidate requires native validation and independent reference review.
"""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import mechanical_check

BASE=STAGING/'two-board-power-digital-startup-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2310-digital-startup-02/capture.json'
PLAN=STAGING/'two-board-startup-logic-plan-01'
OUT=STAGING/'two-board-power-startup-logic-01'

def run():
 assert not OUT.exists()
 for path in [CAP,PLAN/'manifest.json']:
  for name,h in json.loads(path.read_text())['source_sha256'].items():
   p=Path(name);assert sha(p if p.is_absolute() else REPO/p)==h,name
 c=json.loads(CAP.read_text());p=json.loads((PLAN/'plan.json').read_text())
 assert not p['deferred'] and len(p['joins'])==12
 b=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
 fps={prop(f,'Reference')[2]:f for f in children(b,'footprint')}
 old={o['uuid']:o for o in c['objects']};retire=set(p['retired_objects'])
 assert len(retire)==2 and all(old[u]['kind']=='PCB_TRACK' for u in retire)
 for ref,(xy,rot,flip) in p['moves'].items():
  assert not flip
  for o in c['objects']:
   if o.get('ref')==ref and (ref,o['pin']) not in [('E_U29','5'),('E_U29','7')]:assert len(c['all_groups'][o['group']])==1
  fps[ref]=rotate_footprint(fps[ref],xy,rot)
 placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
 for row in p['side_reconciliations']:
  rec=next(r for r in placement['parts'] if r['id']==row['ref']);assert rec['side']==row['old_side'];rec['side']=row['current_side']
 mechanical_check(fps,set(p['moves']),placement)
 for i,n in enumerate(b):
  if isinstance(n,list) and n and n[0]=='footprint' and prop(n,'Reference')[2] in p['moves']:b[i]=fps[prop(n,'Reference')[2]]
 b[:]=[n for n in b if not(isinstance(n,list) and n and n[0]=='segment' and str(first(n,'uuid')[1]) in retire)]
 codes={str(n[2]):int(n[1]) for n in children(b,'net')}
 uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPSTARTLOGIC01:'+sha(CAP)+':'+name))
 unused=lambda x:(x.get('ref'),x.get('pin'))==('E_U29','1')
 routes=[copy.deepcopy(r) for cell in p['cells'] for r in cell['routes'] if not unused(r)]+p['routes']
 vias=[copy.deepcopy(v) for cell in p['cells'] for v in cell['vias'] if not unused(v)]+p['extra_vias']
 for i,r in enumerate(routes):
  r['segment_uuids']=[]
  for j,(pt,qt) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
   assert pt!=qt
   u=uid(f'track-{i}-{j}');r['segment_uuids'].append(u)
   b.append([a('segment'),[a('start'),*pt],[a('end'),*qt],[a('width'),r['width_mm']],[a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),u]])
 for i,v in enumerate(vias):
  v['uuid']=uid(f'via-{i}')
  b.append([a('via'),[a('at'),*v['position_mm']],[a('size'),v['size_mm']],[a('drill'),v['drill_mm']],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
 # Extend the existing In5 main return to the two logic cells. Existing
 # unconnected ground groups and all owned quiet returns remain excluded.
 main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
 target='2fff880c-5da4-5609-a6d1-dfc1d5b3e287'
 zcap={z['uuid']:z for z in c['zones']};original=shape(zcap[target]['authored_outline'])
 extension=box(125.0,136.0,146.5,165.0)
 for o in c['objects']:
  if o['net']=='PWR_AGND' and o.get('group')!=main and o['layers'].get('In5.Cu'):
   extension=extension.difference(shape(o['layers']['In5.Cu']).buffer(.21,quad_segs=64))
  if o.get('npth'):extension=extension.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51,quad_segs=64))
 for z in c['zones']:
  if z['uuid']!=target and z['layer']=='In5.Cu':extension=extension.difference(shape(z['authored_outline']).buffer(.215))
 g=unary_union([original,extension]).simplify(.00001,preserve_topology=True)
 assert g.geom_type=='Polygon' and g.is_valid and original.difference(g.buffer(.00002)).area<1e-7
 # Refill every zone whose layer may be affected by a moved pad, track or via.
 affected={l:[] for l in c['copper_layers']}
 for o in c['objects']:
  if o['uuid'] in retire or o.get('ref') in p['moves']:
   for l,ps in o['layers'].items():affected[l].append(shape(ps).buffer(.6))
 for r in routes:affected[r['layer']].append(LineString(r['path_mm']).buffer(r['width_mm']/2+.6))
 for v in vias:
  for l in affected:affected[l].append(Point(v['position_mm']).buffer(.9))
 # New footprint pads stay within these conservatively expanded courtyards.
 from hardware.electronics.output_stage.check_placement import courtyard
 for ref in p['moves']:
  layer=first(fps[ref],'layer')[1];affected[layer].append(box(*courtyard(fps[ref],layer[0]+'.CrtYd')).buffer(.6))
 affected={l:unary_union(xs) for l,xs in affected.items()}
 refill=[]
 for z in children(b,'zone'):
  u=str(first(z,'uuid')[1]);region=shape(zcap[u]['authored_outline'])
  if u==target:
   region=g;z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='polygon')]
   z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
  if u==target or region.intersects(affected[zcap[u]['layer']]):
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for src in BASE.rglob('*'):
  if not src.is_file():continue
  rel=src.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (src.suffix=='.kicad_sch' or src.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);sources.append(src)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(b)+'\n')
 path=OUT/'power_protection.kicad_sch';sch=read_sexpr(path.read_text());first(first(sch,'title_block'),'rev')[1]='TBP41-CANDIDATE';path.write_text(sexpr(sch)+'\n')
 sources=[Path(__file__),CAP,*PLAN.iterdir(),STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','repack_two_board_buck_input.py','route_two_board_buck_cell.py']],*sources]
 result=dict(source_sha256={str(src.relative_to(REPO)):sha(src) for src in sources},moves=p['moves'],retired_objects=sorted(retire),routes=routes,vias=vias,joins=p['joins'],edited_zone_outlines=[dict(uuid=target,layer='In5.Cu',outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors])],refilled_existing_zones=refill,main_ground_group_before=main,new_ground_pads=[['E_U29','4'],['E_U40','4'],['E_C74','2'],['E_C83','2']],local_bypass_joins=[['E_U29','8','E_C74','1'],['E_U40','8','E_C83','1']],added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),expected_closed_connections=16,unused_fanout_not_emitted=['E_U29.1'],mechanical_screen_findings=0,circuit_changes=[],native_validation_pending=True,reference_review_pending=True,complete_startup_routing=False,fabrication_released=False)
 (OUT/'startup-logic-routing.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['added_tracks','added_vias','expected_closed_connections','refilled_existing_zones']}))

if __name__=='__main__':run()
