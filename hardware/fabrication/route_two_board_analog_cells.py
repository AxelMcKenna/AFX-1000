"""Construct analog local controls and explicitly owned quiet return regions."""
import copy,json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.output_stage.check_placement import courtyard
BASE=STAGING/'two-board-power-permission-native-04'
CAP=STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json'
PLAN=STAGING/'two-board-analog-cell-plan-04'
POSE=STAGING/'two-board-analog-cell-native-poses-04'
OUT=STAGING/'two-board-power-analog-cells-01'

def run():
 assert not OUT.exists()
 c=json.loads(CAP.read_text());p=json.loads((PLAN/'routes.json').read_text());qplan=json.loads((PLAN/'quiet-shapes.json').read_text());geom=json.loads((PLAN/'geometry-review.json').read_text())
 assert geom['passed'] and not p['deferred']
 for data in [c,geom,json.loads((POSE/'poses.json').read_text())]:
  for name,h in data['source_sha256'].items():assert sha(REPO/name)==h,name
 b=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());posed=read_sexpr((POSE/'native-poses.kicad_pcb').read_text());codes={str(n[2]):int(n[1]) for n in children(b,'net')}
 fps={prop(f,'Reference')[2]:f for f in children(posed,'footprint')};retire=set(p['retired_objects']);old={o['uuid']:o for o in c['objects']}
 assert len(retire)==92 and retire<=old.keys()
 # KiCad 10's saved pose fixture uses named pad nets; normalize imported pads
 # to the existing numeric-net board encoding without changing net identity.
 for ref in p['moves']:
  for pad in children(fps[ref],'pad'):
   net=first(pad,'net');name=str(net[-1]);assert name in codes
   net[:]=[a('net'),codes[name],name]
 for i,n in enumerate(b):
  if isinstance(n,list) and n and n[0]=='footprint' and prop(n,'Reference')[2] in p['moves']:b[i]=fps[prop(n,'Reference')[2]]
 b[:]=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retire)]
 uid=lambda name:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPANALOG01:'+sha(CAP)+':'+name))
 routes=copy.deepcopy(p['routes']+p['connections'])
 for i,r in enumerate(routes):
  r['segment_uuids']=[]
  for j,(pt,qt) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
   assert pt!=qt
   u=uid(f'track-{i}-{j}');r['segment_uuids'].append(u)
   b.append([a('segment'),[a('start'),*pt],[a('end'),*qt],[a('width'),r['width_mm']],[a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),u]])
 vias=[dict(copy.deepcopy(v),owner=r['owner'],ref=r['ref'],pin=r['pin']) for r,v in zip(p['routes'],p['vias'])]+copy.deepcopy(p['extra_quiet_vias'])
 for i,v in enumerate(vias):
  v.update(uuid=uid(f'via-{i}'),size_mm=.6,drill_mm=.3)
  b.append([a('via'),[a('at'),*v['position_mm']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
 quiet=[];newzones=[];newshapes={}
 def polygon_nodes(g):
  return [[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]]
 for owner in ['E_U13','E_U14','E_U32']:
  star=next(v for v in vias if v['ref']==owner and v['pin']=='8')
  control=[v for v in vias if v['ref']==owner and v['pin'] in ['2','4']]
  extras=[v for v in vias if v['owner']==owner and v['net']=='PWR_AGND' and v not in control+[star]]
  own=[star,*control,*extras];ownids={v['uuid'] for v in own};zoneids=[]
  for region in qplan['regions']:
   if region['owner']!=owner:continue
   assert region['required_uncovered_mm2']<1e-6
   for index,(poly,component) in enumerate(zip(region['polygons'],region['components'])):
    g=shape([poly]).simplify(.00001,preserve_topology=True);assert g.geom_type=='Polygon' and g.is_valid and component['anchors']
    layer=region['layer'];u=uid(f'{owner}-{layer}-{index}');zoneids.append(u);newshapes[u]=g
    for o in c['objects']:
     if o['uuid'] not in retire and o['net']=='PWR_AGND' and o['layers'].get(layer):assert g.distance(shape(o['layers'][layer]))>=.2149,(u,o['uuid'])
    contacts=[]
    for v in vias:
     if v['net']!='PWR_AGND':continue
     vg=Point(v['position_mm']).buffer(.3)
     if v['uuid'] not in ownids:assert g.distance(vg)>=.2149,(u,v['uuid'])
     elif g.intersects(vg):contacts.append(v['uuid'])
    assert contacts
    b.append([a('zone'),[a('net'),codes['PWR_AGND']],[a('net_name'),'PWR_AGND'],[a('layer'),layer],[a('uuid'),u],[a('priority'),1],[a('hatch'),a('edge'),.5],[a('connect_pads'),a('yes'),[a('clearance'),.2]],[a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],[a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],*polygon_nodes(g)])
    newzones.append(dict(uuid=u,owner=owner,layer=layer,net='PWR_AGND',expected_contact_vias=contacts,outer_mm=list(g.exterior.coords),holes_mm=[list(h.coords) for h in g.interiors]))
  # Connectivity of authored regions is proved using only owned regions and
  # their shared through-vias; no main-ground shortcut participates.
  reached={star['uuid']};pending=set(zoneids)
  while True:
   before=set(reached)
   for z in newzones:
    if z['uuid'] in pending and reached.intersection(z['expected_contact_vias']):
     reached.update(z['expected_contact_vias']);pending.remove(z['uuid'])
   if reached==before:break
  assert not pending and ownids<=reached,(owner,pending,ownids-reached)
  quiet.append(dict(ref=owner,star_via=star,control_vias=control,extra_quiet_vias=extras,zone_uuids=zoneids,authored_owned_graph_connected=True,allowed_main_star_zones=['2fff880c-5da4-5609-a6d1-dfc1d5b3e287']))
 assert len(newzones)==7
 for i,z in enumerate(newzones):
  for other in newzones[i+1:]:
   if z['layer']==other['layer']:assert newshapes[z['uuid']].distance(newshapes[other['uuid']])>=.2149
 # Only GND8 stars touch main In5 ground. Every other quiet via is excluded
 # from every pre-existing ground field, even when the net names match.
 zcap={z['uuid']:z for z in c['zones']};regions={u:shape(z['authored_outline']) for u,z in zcap.items()}
 for u,z in zcap.items():
  if z['net']!='PWR_AGND':continue
  g=regions[u]
  for q in quiet:
   for v in q['control_vias']+q['extra_quiet_vias']:
    g=g.difference(Point(v['position_mm']).buffer(.515,quad_segs=64))
   if u not in q['allowed_main_star_zones']:g=g.difference(Point(q['star_via']['position_mm']).buffer(.515,quad_segs=64))
  for znew in newzones:
   if z['layer']==znew['layer']:g=g.difference(newshapes[znew['uuid']].buffer(.215,quad_segs=64))
  regions[u]=g
 affected={l:[] for l in c['copper_layers']}
 for o in c['objects']:
  if o['uuid'] in retire or o.get('ref') in p['moves']:
   for l,ps in o['layers'].items():affected[l].append(shape(ps).buffer(.6))
 for r in routes:affected[r['layer']].append(LineString(r['path_mm']).buffer(r['width_mm']/2+.6))
 for v in vias:
  for l in affected:affected[l].append(Point(v['position_mm']).buffer(.9))
 for ref in p['moves']:
  layer=str(first(fps[ref],'layer')[1]);affected[layer].append(box(*courtyard(fps[ref],layer[0]+'.CrtYd')).buffer(.6))
 affected={l:unary_union(gs) for l,gs in affected.items()};edited=[];refill=[];discarded=[]
 for z in children(b,'zone'):
  u=str(first(z,'uuid')[1])
  if u not in zcap:continue
  g=regions[u].simplify(.00001,preserve_topology=True);changed=regions[u].symmetric_difference(shape(zcap[u]['authored_outline'])).area>1e-7
  if changed:
   if g.geom_type!='Polygon':
    assert g.geom_type=='MultiPolygon',(u,g.geom_type)
    kept=[]
    for gg in g.geoms:
     contacts=[o['uuid'] for o in c['objects'] if o['uuid'] not in retire and o['net']=='PWR_AGND' and o['layers'].get(zcap[u]['layer']) and gg.intersects(shape(o['layers'][zcap[u]['layer']]))]
     if contacts:kept.append(gg);continue
     blockers=[v['uuid'] for v in vias if v['net']!='PWR_AGND' and gg.difference(Point(v['position_mm']).buffer(.5,quad_segs=64)).area<1e-6]
     blockers.extend(o['uuid'] for o in c['objects'] if o['uuid'] not in retire and o['net']!='PWR_AGND' and o['layers'].get(zcap[u]['layer']) and gg.difference(shape(o['layers'][zcap[u]['layer']]).buffer(.2,quad_segs=64)).area<1e-6)
     assert blockers,(u,'unanchored fragment not entirely inside foreign-via clearance',gg.area)
     discarded.append(dict(zone_uuid=u,area_mm2=gg.area,covered_by_foreign_object_uuids=blockers,outer_mm=list(gg.exterior.coords),holes_mm=[list(h.coords) for h in gg.interiors],reason='Unanchored authored fragment entirely inside a foreign-copper clearance; cannot contain ground fill.'))
    assert len(kept)==1;g=kept[0]
   assert g.geom_type=='Polygon' and g.is_valid,(u,g.geom_type)
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='polygon')];z.extend(polygon_nodes(g))
   edited.append(dict(uuid=u,layer=zcap[u]['layer'],outer_mm=list(g.exterior.coords),holes_mm=[list(h.coords) for h in g.interiors]))
  if changed or g.intersects(affected[zcap[u]['layer']]):
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for path in BASE.rglob('*'):
  if not path.is_file():continue
  rel=path.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or (len(rel.parts)==1 and (path.suffix=='.kicad_sch' or path.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json'])):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);sources.append(path)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(b)+'\n')
 path=OUT/'power_protection.kicad_sch';sch=read_sexpr(path.read_text());first(first(sch,'title_block'),'rev')[1]='TBP45-CANDIDATE';path.write_text(sexpr(sch)+'\n')
 sources=[Path(__file__),CAP,*[path for path in PLAN.iterdir() if path.is_file()],POSE/'poses.json',POSE/'native-poses.kicad_pcb',*[REPO/'hardware/fabrication'/name for name in ['route_nf_surface.py','route_two_board_buck_cell.py']],*sources]
 report=dict(source_sha256={str(path.relative_to(REPO)):sha(path) for path in sources},moves=p['moves'],retired_objects=sorted(retire),routes=routes,vias=vias,quiet_ground_islands=quiet,new_zones=newzones,edited_zone_outlines=edited,discarded_clearance_fragments=discarded,refilled_existing_zones=refill,added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),native_validation_pending=True,reference_and_preservation_review_pending=True,mechanical_screen_findings=0,circuit_changes=[],fabrication_released=False)
 (OUT/'analog-cell-routing.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(tracks=report['added_tracks'],vias=len(vias),new_zones=len(newzones),edited_zones=len(edited),refilled_zones=len(refill))))
if __name__=='__main__':run()
