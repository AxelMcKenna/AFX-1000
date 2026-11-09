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

BASE=STAGING/'two-board-power-startup-completion-native-06'
CAP=STAGING/'two-board-power-routing-inputs-2267-startup-completion-06/capture.json'
PLAN=STAGING/'two-board-permission-plan-03'
OUT=STAGING/'two-board-power-permission-03'

def run():
 assert not OUT.exists()
 for path in [CAP,PLAN/'manifest.json']:
  for name,h in json.loads(path.read_text())['source_sha256'].items():
   p=Path(name);assert sha(p if p.is_absolute() else REPO/p)==h,name
 c=json.loads(CAP.read_text());p=json.loads((PLAN/'plan.json').read_text())
 assert len(p['joins'])==25 and len(p['moves'])==2 and len(p['deferred'])==0
 b=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
 fps={prop(f,'Reference')[2]:f for f in children(b,'footprint')}
 old={o['uuid']:o for o in c['objects']};retire=set(p['retired_objects'])
 assert not retire
 for ref,(xy,rot,flip) in p['moves'].items():
  assert not flip
  for o in c['objects']:
   if o.get('ref')==ref:assert len(c['all_groups'][o['group']])==1
  fps[ref]=rotate_footprint(fps[ref],xy,rot)
 placement=json.loads((STAGING/'two-board-placement-05/capture.json').read_text())
 for row in p['side_reconciliations']:
  rec=next(r for r in placement['parts'] if r['id']==row['ref']);assert rec['side']==row['old_side'];rec['side']=row['current_side']
 mechanical_check(fps,set(p['moves']),placement)
 for i,n in enumerate(b):
  if isinstance(n,list) and n and n[0]=='footprint' and prop(n,'Reference')[2] in p['moves']:b[i]=fps[prop(n,'Reference')[2]]
 b[:]=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retire)]
 codes={str(n[2]):int(n[1]) for n in children(b,'net')}
 uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPERMISSION03:'+sha(CAP)+':'+name))
 unused=lambda x:False
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
 # Extend only the four declared main reference fields. Orphan proposal
 # fragments are discarded, never emitted as floating ground copper.
 main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
 assert main==p['main_ground_group']
 zcap={z['uuid']:z for z in c['zones']};regions={};discarded=[]
 for layer,record in p['reference_regions'].items():
  u=record['existing_zone_uuid'];original=shape(zcap[u]['authored_outline']);kept=[]
  for poly in record['polygons']:
   g=shape([poly])
   if original.difference(g.buffer(.000002)).area<1e-6:kept.append(g)
   else:
    contacts=[o for o in c['objects'] if o['net']=='PWR_AGND' and o['layers'].get(layer) and g.intersection(shape(o['layers'][layer])).area>1e-9]
    assert not contacts and not any(g.covers(Point(v['position_mm'])) for v in vias if v['net']=='PWR_AGND')
    discarded.append(dict(layer=layer,area_mm2=g.area,reason='No source contact or intended new return'))
  assert len(kept)==1 and kept[0].is_valid
  regions[u]=kept[0]
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
  if u in regions:
   region=regions[u];g=region;z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='polygon')]
   z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
  if u in regions or region.intersects(affected[zcap[u]['layer']]):
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for src in BASE.rglob('*'):
  if not src.is_file():continue
  rel=src.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (src.suffix=='.kicad_sch' or src.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);sources.append(src)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(b)+'\n')
 path=OUT/'power_protection.kicad_sch';sch=read_sexpr(path.read_text());first(first(sch,'title_block'),'rev')[1]='TBP44-CANDIDATE';path.write_text(sexpr(sch)+'\n')
 sources=[Path(__file__),CAP,*PLAN.iterdir(),STAGING/'two-board-placement-05/capture.json',STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','repack_two_board_buck_input.py','route_two_board_buck_cell.py']],*sources]
 result=dict(source_sha256={str(src.relative_to(REPO)):sha(src) for src in sources},moves=p['moves'],retired_objects=sorted(retire),routes=routes,vias=vias,joins=p['joins'],edited_zone_outlines=[dict(uuid=u,layer=zcap[u]['layer'],outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors]) for u,g in regions.items()],discarded_unconnected_regions=discarded,refilled_existing_zones=refill,main_ground_group_before=main,new_ground_pads=[[ref,'4'] for ref in ['E_U31','E_U42']]+[[ref,'2'] for ref in ['E_C76','E_C85']],local_bypass_joins=[[ref,'8',cap,'1'] for ref,cap in [('E_U42','E_C85')]],added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),expected_closed_connections=30,unused_fanout_not_emitted=p['unused_fanout_not_emitted'],deferred=p['deferred'],mechanical_screen_findings=0,circuit_changes=[],native_validation_pending=True,reference_review_pending=True,complete_startup_routing=False,fabrication_released=False)
 (OUT/'permission-routing.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['added_tracks','added_vias','expected_closed_connections','refilled_existing_zones']}))

if __name__=='__main__':run()
