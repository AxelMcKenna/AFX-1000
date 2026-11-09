"""Relocate the remaining master-enable pulldown to its owned quiet return."""
import copy,json,shutil,uuid,math
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_buck_cell import mechanical_check,position,transform_object
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
BASE=STAGING/'two-board-power-analog-cells-native-03'
CAP=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json'
PLAN=STAGING/'two-board-digital-return-plan-01'
OUT=STAGING/'two-board-power-digital-return-01'

def run():
 assert not OUT.exists()
 c=json.loads(CAP.read_text());proposal=json.loads((PLAN/'placement-options.json').read_text());retire=set(proposal['retired_objects'])
 for name,h in c['source_sha256'].items():assert sha(REPO/name)==h,name
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')}
 ref='E_R104';trial=proposal['candidates'][0];assert trial['rotation']==0 and not trial['flip']
 oldfp=copy.deepcopy(fps[ref]);fps[ref]=rotate_footprint(fps[ref],trial['xy'],0)
 plpath=STAGING/'two-board-placement-05/capture.json';pl=json.loads(plpath.read_text());sides=[]
 allowed={'P_R103','P_R101','P_R104','P_C101','P_C204','P_C104','E_C47','E_C51','E_R98','E_R110','E_C45','E_R97','E_R114','E_R116'}
 for r in pl['parts']:
  if r['id'] in fps and r['id']!=ref and r['side']!=str(first(fps[r['id']],'layer')[1])[0]:
   assert r['id'] in allowed and not r['tails_relative_xy'];bb=r['body_relative_xy'];assert abs(bb[0]+bb[2])<1e-7 and abs(bb[1]+bb[3])<1e-7
   sides.append(dict(ref=r['id'],old_side=r['side'],current_side=str(first(fps[r['id']],'layer')[1])[0]));r['side']=sides[-1]['current_side']
 assert {r['ref'] for r in sides}==allowed
 mechanical_check(fps,{ref},pl)
 old={o['uuid']:o for o in c['objects']};assert retire<=old.keys() and all(old[u]['kind'] in ['PCB_TRACK','PCB_VIA'] for u in retire)
 # Only the remote leaf branch retires. No third retained object contacts its
 # via or intermediate track except the intended old R104 and R28 endpoints.
 for u in retire:
  o=old[u]
  for other in c['objects']:
   if other['uuid'] in retire or other.get('ref')==ref or other['net']!=o['net']:continue
   for layer,polys in o['layers'].items():
    if polys and other['layers'].get(layer) and shape(polys).intersects(shape(other['layers'][layer])):
     assert other.get('ref')=='E_R28' or other['uuid'] in ['6b155b94-8b63-59c3-ab99-a63d5544e188'],(u,other['uuid'])
 for i,f in enumerate(board):
  if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2]==ref:board[i]=fps[ref]
 board[:]=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retire)]
 objects=[]
 for o in c['objects']:
  if o['uuid'] in retire:continue
  if o.get('ref')==ref:o=transform_object(o,position(oldfp),trial['xy'],0)
  objects.append(o)
 signal=next(o['net'] for o in objects if o.get('ref')==ref and o['pin']=='1')
 routes=[dict(label='E_R104 enable',net=signal,layer='B.Cu',width_mm=.2,path_mm=trial['enable'],owner='E_U15'),dict(label='E_R104 owned quiet return',net='PWR_AGND',layer='B.Cu',width_mm=.2,path_mm=trial['ground'],owner='E_U15')]
 own=set(proposal['surface_owned_ground_objects'])|{o['uuid'] for o in objects if o.get('ref')==ref and o['net']=='PWR_AGND'}
 # Independently recheck all relocated-pad and route geometry against retained
 # copper, distinguishing same-net ground belonging to another quiet owner.
 for r in routes:
  g=LineString(r['path_mm']);assert len(r['path_mm'])==2
  for o in objects:
   if o['layers'].get(r['layer']) and (o['net']!=r['net'] or r['net']=='PWR_AGND' and o['uuid'] not in own):assert g.distance(shape(o['layers'][r['layer']]))>=.31-1e-7,(r['label'],o['uuid'])
 for o in objects:
  if o.get('ref')!=ref:continue
  g=shape(o['layers']['B.Cu'])
  for other in objects:
   if other['uuid']==o['uuid']:continue
   if other['layers'].get('B.Cu') and (other['net']!=o['net'] or o['net']=='PWR_AGND' and other['uuid'] not in own):assert g.distance(shape(other['layers']['B.Cu']))>=.21-1e-7,other['uuid']
   d=other.get('drill_mm',0);rad=(max(d) if isinstance(d,list) else d)/2
   if rad:assert g.distance(Point(other['position_mm']))-rad>=.15-1e-7
 codes={str(n[2]):int(n[1]) for n in children(board,'net')};uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPDIGRETURN01:'+sha(CAP)+':'+s))
 for i,r in enumerate(routes):
  r['segment_uuids']=[uid(str(i))]
  board.append([a('segment'),[a('start'),*r['path_mm'][0]],[a('end'),*r['path_mm'][1]],[a('width'),.2],[a('layer'),'B.Cu'],[a('net'),codes[r['net']]],[a('uuid'),r['segment_uuids'][0]]])
 priorpath=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json';prior=json.loads(priorpath.read_text());q=prior['quiet_ground_islands'][0];assert q['ref']=='E_U15'
 quietids={u for qq in prior['quiet_ground_islands'] for u in qq['zone_uuids']}
 zmap={z['uuid']:z for z in c['zones']};regions={u:shape(z['authored_outline']) for u,z in zmap.items()};back=next(u for u in q['zone_uuids'] if zmap[u]['layer']=='In6.Cu')
 # Connect the new enable projection to the existing quiet field by extending
 # the short span underneath the resistor and its owned ground connection.
 extension=unary_union([LineString(trial['enable']).buffer(.4),LineString([trial['enable'][0],trial['ground'][0],trial['ground'][-1]]).buffer(.4)])
 g=unary_union([regions[back],extension]);ownvias={v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]}
 for o in objects:
  if o['layers'].get('In6.Cu') and (o['net']!='PWR_AGND' or o['uuid'] not in ownvias):g=g.difference(shape(o['layers']['In6.Cu']).buffer(.215,quad_segs=64))
 for u in quietids-{back}:
  if zmap[u]['layer']=='In6.Cu':g=g.difference(regions[u].buffer(.215,quad_segs=64))
 assert g.geom_type=='Polygon' and g.is_valid
 required=LineString(trial['enable']).buffer(.1)
 for o in objects:
  if o['kind']=='PCB_VIA' and o['net']==signal:required=required.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
 assert required.difference(g.buffer(.0015)).area<1e-6,'Enable projection not covered by owned region'
 regions[back]=g
 for u,z in zmap.items():
  if u not in quietids and z['net']=='PWR_AGND' and z['layer']=='In6.Cu':regions[u]=regions[u].difference(g.buffer(.215,quad_segs=64))
 affected={l:[] for l in c['copper_layers']}
 for u in retire:
  for l,ps in old[u]['layers'].items():
   if ps:affected[l].append(shape(ps).buffer(.7))
 for r in routes:affected[r['layer']].append(LineString(r['path_mm']).buffer(.7))
 edited=[];refill=[]
 for z in children(board,'zone'):
  u=str(first(z,'uuid')[1]);g=regions[u].simplify(.00001,preserve_topology=True);changed=g.symmetric_difference(shape(zmap[u]['authored_outline'])).area>1e-7
  if changed:
   assert g.geom_type=='Polygon' and g.is_valid,(u,g.geom_type)
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='polygon')]
   z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
   edited.append(dict(uuid=u,layer=zmap[u]['layer'],outer_mm=list(g.exterior.coords),holes_mm=[list(h.coords) for h in g.interiors]))
  if changed or any(g.intersects(a) for a in affected[zmap[u]['layer']]):
   z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
 OUT.mkdir();sources=[]
 for path in BASE.rglob('*'):
  if not path.is_file():continue
  rel=path.relative_to(BASE)
  if rel.parts[0] in ['libraries','symbols'] or len(rel.parts)==1 and (path.suffix=='.kicad_sch' or path.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json']):
   dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);sources.append(path)
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 sch=OUT/'power_protection.kicad_sch';tree=read_sexpr(sch.read_text());first(first(tree,'title_block'),'rev')[1]='TBP46-CANDIDATE';sch.write_text(sexpr(tree)+'\n')
 sources=[Path(__file__),CAP,priorpath,plpath,STAGING/'assembly-layout-04/allocation.json',*[p for p in PLAN.iterdir() if p.is_file()],*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_buck_cell.py','repack_two_board_buck_input.py']],*sources]
 report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},moves={ref:[trial['xy'],0,False]},retired_objects=sorted(retire),routes=routes,vias=[],added_tracks=2,added_vias=0,expected_closed_connections=1,reconciled_existing_passive_sides=sides,existing_surface_quiet_objects=sorted(own),extended_quiet_owner='E_U15',extended_quiet_zone_uuid=back,edited_zone_outlines=edited,refilled_existing_zones=refill,native_validation_pending=True,fabrication_released=False)
 (OUT/'digital-return-routing.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(routes=2,retired=3,edited_zones=len(edited),refilled=len(refill))))
if __name__=='__main__':run()
