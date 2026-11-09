"""Add main-ground reference fields around the routed startup logic.

Do not merge quiet returns or isolated existing ground groups. Native fill,
partition preservation and route-reference coverage still require review.
"""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-startup-logic-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json'
PLAN=STAGING/'two-board-logic-reference-plan-02'
OUT=STAGING/'two-board-power-logic-references-03'

def run():
 assert not OUT.exists()
 for p in [CAP,PLAN/'manifest.json']:
  for name,h in json.loads(p.read_text())['source_sha256'].items():
   path=Path(name);assert sha(path if path.is_absolute() else REPO/path)==h,name
 c=json.loads(CAP.read_text());p=json.loads((PLAN/'regions.json').read_text())
 b=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());zones={str(first(z,'uuid')[1]):z for z in children(b,'zone')};zc={z['uuid']:z for z in c['zones']}
 main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2');assert main==p['main_group']
 quiet=set(p['quiet_vias_excluded']);template=zones['2fff880c-5da4-5609-a6d1-dfc1d5b3e287']
 uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPLOGICREF02:'+sha(CAP)+':'+name))
 source_zone=zones['de233285-cc07-5d51-9dbd-88a46856bbca']
 assert first(source_zone,'priority') is None or int(first(source_zone,'priority')[1])==0
 if first(source_zone,'priority') is None:source_zone.append([a('priority'),2])
 else:first(source_zone,'priority')[1]=2
 changed_routes=[copy.deepcopy(route) for item in p['reroutes'] for route in item['routes']]
 newvias=[copy.deepcopy(v) for item in p['reroutes'] for v in item['vias']]
 retired_routes=[route for item in p['reroutes'] for route in item.get('retired_routes',[item.get('retired_route')]) if route]
 retired={u for route in retired_routes for u in route['segment_uuids']}
 retired.update(item['retired_via']['uuid'] for item in p['reroutes'] if item.get('retired_via'))
 old={o['uuid']:o for o in c['objects']};assert len(retired)==9 and all(old[u]['kind'] in ['PCB_TRACK','PCB_VIA'] for u in retired)
 b[:]=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired)]
 codes={str(n[2]):int(n[1]) for n in children(b,'net')}
 for i,route in enumerate(changed_routes):
  route['segment_uuids']=[]
  for j,(pt,qt) in enumerate(zip(route['path_mm'],route['path_mm'][1:])):
   u=uid(f'track-{i}-{j}');route['segment_uuids'].append(u)
   b.append([a('segment'),[a('start'),*pt],[a('end'),*qt],[a('width'),route['width_mm']],[a('layer'),route['layer']],[a('net'),codes[route['net']]],[a('uuid'),u]])
 for i,v in enumerate(newvias):
  v['uuid']=uid(f'via-{i}');b.append([a('via'),[a('at'),*v['position_mm']],[a('size'),v['size_mm']],[a('drill'),v['drill_mm']],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
 effective_routes=copy.deepcopy(p['combined_routes']);replacement={r['label']:r for r in changed_routes}
 effective_routes=[replacement.get(r.get('label'),r) for r in effective_routes]
 assert len(effective_routes)==37 and all(r['segment_uuids'] for r in effective_routes)
 added=[];edited=[];discarded=[];refill=[]
 def setpoly(z,g):
  g=g.simplify(.00001,preserve_topology=True);assert g.geom_type=='Polygon' and g.is_valid
  z[:]=[n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
  z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
  return dict(outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(h.coords)[:-1] for h in g.interiors])
 for layer,record in p['regions'].items():
  parts=sorted([shape([poly]) for poly in record['polygons']],key=lambda g:-g.area);existing=record['existing_zone_uuid'];retained_original=False
  for i,g in enumerate(parts):
   contacts=[o for o in c['objects'] if o['net']=='PWR_AGND' and o['layers'].get(layer) and g.intersects(shape(o['layers'][layer]))]
   if not contacts:
    discarded.append(dict(layer=layer,area_mm2=g.area,reason='No existing ground contact'));continue
   assert {o['group'] for o in contacts}=={main} and not {o['uuid'] for o in contacts}&quiet
   contains_original=existing and shape(zc[existing]['authored_outline']).difference(g.buffer(.000002)).area<1e-6
   if contains_original:
    assert not retained_original;retained_original=True
    if shape(zc[existing]['authored_outline']).symmetric_difference(g).area<1e-6:continue
    z=zones[existing];region=setpoly(z,g);edited.append(dict(uuid=existing,layer=layer,**region));refill.append(existing)
   else:
    z=copy.deepcopy(template);u=uid(layer+'-'+str(i));first(z,'uuid')[1]=u;first(z,'layer')[1]=layer
    region=setpoly(z,g);b.append(z);added.append(dict(uuid=u,layer=layer,net='PWR_AGND',existing_main_contacts=sorted(o['uuid'] for o in contacts),**region))
  if existing:assert retained_original,(layer,'Original field removed')
 # Copper replacement affects native clearances even where zone outlines do
 # not change. Explicitly refill all touched original fields.
 affected={l:[] for l in c['copper_layers']}
 for u in retired:
  for l,ps in old[u]['layers'].items():affected[l].append(shape(ps).buffer(.6))
 for route in changed_routes:affected[route['layer']].append(LineString(route['path_mm']).buffer(.7))
 for v in newvias:
  for l in affected:affected[l].append(Point(v['position_mm']).buffer(.9))
 for u,z in zones.items():
  if u in refill:continue
  if any(shape(zc[u]['authored_outline']).intersects(g) for g in affected[zc[u]['layer']]):
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for src in BASE.rglob('*'):
  if not src.is_file():continue
  rel=src.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (src.suffix=='.kicad_sch' or src.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);sources.append(src)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(b)+'\n')
 path=OUT/'power_protection.kicad_sch';s=read_sexpr(path.read_text());first(first(s,'title_block'),'rev')[1]='TBP42-CANDIDATE';path.write_text(sexpr(s)+'\n')
 sources=[Path(__file__),CAP,*PLAN.iterdir(),REPO/'hardware/fabrication/route_nf_surface.py',BASE/'startup-logic-routing.json',*sources]
 r=dict(zone_priority_changes=[dict(uuid='de233285-cc07-5d51-9dbd-88a46856bbca',before=0,after=2,reason='Reserve the existing digital supply field ahead of added main-ground reference copper')],source_sha256={str(src.relative_to(REPO)):sha(src) for src in sources},added_zones=added,edited_zone_outlines=edited,refilled_existing_zones=refill,discarded_unconnected_regions=discarded,existing_main_group=main,excluded_quiet_vias=sorted(quiet),moved_footprints=[],circuit_changes=[],routes=changed_routes,vias=newvias,effective_logic_routes=effective_routes,retired_objects=sorted(retired),retired_routes=retired_routes,added_tracks=sum(len(r['segment_uuids']) for r in changed_routes),added_vias=len(newvias),expected_native_opens=2294,native_validation_pending=True,reference_review_pending=True,fabrication_released=False)
 (OUT/'logic-reference-routing.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(added_zones=len(added),edited_zones=len(edited),discarded_regions=len(discarded),total_zones=len(children(b,'zone')))))

if __name__=='__main__':run()
